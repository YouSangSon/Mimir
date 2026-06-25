"""build_signals() gate - off-by-default LLM sentiment signal (INC5).

The gate is a three-condition AND: config flag + ANTHROPIC_API_KEY + anthropic
installed (the package check is bypassed when a fake classifier is injected).
With no config/settings, build_signals() must return exactly today's 4 signals
and must NOT import `anthropic`.
"""

import logging
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from mimir.analysis.builder import (
    BUILTIN_SIGNAL_SPECS,
    SignalSpec,
    _build_signals_from_specs,
    _load_entry_point_signal_specs,
    build_signals,
    load_signal_specs,
)
from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.analysis.signals.llm_sentiment import HeadlineVerdict
from mimir.analysis.signals.macro_regime import MacroRegimeSignal
from mimir.core.source import Dataset, Market
from mimir.settings import Settings
from mimir.sources.config import SourcesConfig
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

BASE_SIGNAL_IDS = {"filing_event", "news_volume", "price_momentum", "macro_regime"}
AS_OF = date(2026, 5, 31)


class _FakeClassifier:
    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]:
        return [
            HeadlineVerdict(direction=SignalDirection.NEUTRAL, confidence=0.0, rationale="")
            for _ in headlines
        ]


class _FakeSignal:
    id = "plugin_quality"

    def evaluate(self, symbol, market, as_of, reader):
        return SignalResult(
            signal=self.id,
            direction=SignalDirection.NEUTRAL,
            strength=0.5,
            confidence=0.5,
            reason="plugin quality signal",
        )


class _OtherFakeSignal:
    id = "plugin_macro_quality"

    def evaluate(self, symbol, market, as_of, reader):
        return None


class _MismatchedSignal:
    id = "plugin_quality"

    def evaluate(self, symbol, market, as_of, reader):
        return None


class _FakeEntryPoint:
    def __init__(self, name, value=None, error: Exception | None = None):
        self.name = name
        self._value = value
        self._error = error

    def load(self):
        if self._error:
            raise self._error
        return self._value


def _patch_signal_entry_points(monkeypatch, entry_points):
    monkeypatch.setattr(
        "mimir.analysis.builder.importlib.metadata.entry_points",
        lambda group=None: entry_points if group == "mimir.analysis_signals" else [],
    )


def _ids(signals) -> set[str]:
    return {s.id for s in signals}


def _macro_payload(value: float, series_id: str) -> dict:
    return {"series_id": series_id, "value": value, "period": "2026-01-15"}


def _macro_record(series_id: str, day: int, value: float) -> Record:
    return Record(
        source="seed",
        dataset=Dataset.MACRO,
        market=Market.US,
        symbol=series_id,
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key=f"macro:{series_id}:{day}",
        payload=_macro_payload(value, series_id),
    )


def _news_payload(title: str | None, summary: str) -> dict:
    return {
        "title": title,
        "url": "https://example.com/a",
        "publisher": "SEC",
        "market": "US",
        "published_at": None,
        "summary": summary,
    }


def _news_record(day: int, title: str | None, summary: str) -> Record:
    return Record(
        source="seed",
        dataset=Dataset.NEWS,
        market=Market.US,
        symbol=None,
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key=f"news:{day}:{title}",
        payload=_news_payload(title, summary),
    )


def _reader(tmp_path: Path, records: list[Record]) -> DataReader:
    store = JsonlStore(root=tmp_path)
    store.append(records)
    return DataReader(store)


def test_builtin_signal_specs_keep_existing_order():
    assert [spec.id for spec in BUILTIN_SIGNAL_SPECS] == [
        "filing_event",
        "news_volume",
        "price_momentum",
        "macro_regime",
    ]


def test_load_entry_point_signal_specs_accepts_single_spec(monkeypatch):
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("plugin_quality", spec)])

    assert _load_entry_point_signal_specs() == (spec,)


def test_load_entry_point_signal_specs_accepts_sequence(monkeypatch):
    quality = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    macro_quality = SignalSpec(
        "plugin_macro_quality", lambda settings, cfg: _OtherFakeSignal()
    )
    _patch_signal_entry_points(
        monkeypatch, [_FakeEntryPoint("plugin_bundle", (quality, macro_quality))]
    )

    assert _load_entry_point_signal_specs() == (quality, macro_quality)


def test_load_entry_point_signal_specs_rejects_duplicate_plugin_ids(monkeypatch):
    quality = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(
        monkeypatch,
        [
            _FakeEntryPoint("plugin_quality", quality),
            _FakeEntryPoint("plugin_quality", quality),
        ],
    )

    with pytest.raises(ValueError, match="duplicate signal id"):
        _load_entry_point_signal_specs()


def test_entry_point_signal_specs_are_loaded_in_name_order(monkeypatch):
    alpha = SignalSpec("alpha_signal", lambda settings, cfg: _FakeSignal())
    zulu = SignalSpec("zulu_signal", lambda settings, cfg: _OtherFakeSignal())
    _patch_signal_entry_points(
        monkeypatch,
        [_FakeEntryPoint("zulu_signal", zulu), _FakeEntryPoint("alpha_signal", alpha)],
    )

    assert [spec.id for spec in _load_entry_point_signal_specs()] == [
        "alpha_signal",
        "zulu_signal",
    ]


def test_load_signal_specs_appends_entry_point_signals(monkeypatch):
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("plugin_quality", spec)])

    signal_ids = [loaded.id for loaded in load_signal_specs()]

    assert signal_ids == [
        "filing_event",
        "news_volume",
        "price_momentum",
        "macro_regime",
        "plugin_quality",
    ]


def test_entry_point_signal_spec_id_must_match_entry_point_name(monkeypatch):
    spec = SignalSpec("plugin_b", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("plugin_a", spec)])

    with pytest.raises(
        ValueError, match="entry point 'plugin_a' loaded signal spec 'plugin_b'"
    ):
        _load_entry_point_signal_specs()


def test_broken_entry_point_signal_spec_is_skipped_and_logged(monkeypatch, caplog):
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("broken", error=RuntimeError("boom"))])

    with caplog.at_level(logging.WARNING):
        assert _load_entry_point_signal_specs() == ()

    assert "skipping analysis signal plugin 'broken'" in " ".join(
        r.message for r in caplog.records
    )


def test_entry_point_signal_wrong_object_type_raises_value_error(monkeypatch):
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("bad", object())])

    with pytest.raises(ValueError, match="entry point 'bad' must load SignalSpec"):
        _load_entry_point_signal_specs()


def test_unconfigured_plugin_signal_is_not_built(monkeypatch):
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("plugin_quality", spec)])

    signals = build_signals()

    assert "plugin_quality" not in _ids(signals)


def test_default_path_does_not_read_signal_entry_points(monkeypatch):
    def fail_entry_points(*args, **kwargs):
        raise AssertionError("entry points should not be read without analysis.plugins config")

    monkeypatch.setattr(
        "mimir.analysis.builder.importlib.metadata.entry_points",
        fail_entry_points,
    )

    signals = build_signals()

    assert _ids(signals) == BASE_SIGNAL_IDS


def test_build_signals_includes_configured_plugin_signals_after_builtins(monkeypatch):
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("plugin_quality", spec)])
    cfg = SourcesConfig(analysis_plugin_settings={"plugin_quality": {"enabled": True}})

    signals = build_signals(cfg)

    assert [signal.id for signal in signals] == [
        "filing_event",
        "news_volume",
        "price_momentum",
        "macro_regime",
        "plugin_quality",
    ]


def test_entry_point_duplicate_builtin_signal_id_raises_value_error(monkeypatch):
    spec = SignalSpec("news_volume", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("news_volume", spec)])

    with pytest.raises(ValueError, match="duplicate signal id"):
        build_signals(SourcesConfig(analysis_plugin_settings={"news_volume": {}}))


def test_plugin_signal_id_mismatch_raises_value_error():
    spec = SignalSpec("plugin_bad", lambda settings, cfg: _MismatchedSignal())
    cfg = SourcesConfig(analysis_plugin_settings={"plugin_bad": {}})

    with pytest.raises(
        ValueError,
        match="signal spec id 'plugin_bad' built signal id 'plugin_quality'",
    ):
        _build_signals_from_specs(Settings.from_env({}), cfg, (spec,))


def test_required_module_dotted_missing_parent_is_skipped_and_logged(
    monkeypatch, caplog
):
    required_module = "missing_parent_package.missing_child_module"
    spec = SignalSpec(
        "plugin_quality",
        lambda settings, cfg: _FakeSignal(),
        required_module=required_module,
        missing_module_hint="install missing-parent-package",
    )
    cfg = SourcesConfig(analysis_plugin_settings={"plugin_quality": {}})

    def fake_find_spec(name):
        if name == required_module:
            raise ModuleNotFoundError("No module named 'missing_parent_package'")
        return object()

    monkeypatch.setattr("mimir.analysis.builder.importlib.util.find_spec", fake_find_spec)

    with caplog.at_level(logging.WARNING):
        signals = _build_signals_from_specs(Settings.from_env({}), cfg, (spec,))

    assert signals == []
    assert "plugin_quality" in " ".join(record.message for record in caplog.records)
    assert "install missing-parent-package" in " ".join(
        record.message for record in caplog.records
    )


def test_build_signals_passes_analysis_plugin_namespace_to_factory():
    class PluginConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")
        threshold: float

    class ConfiguredSignal:
        id = "plugin_quality"

        def __init__(self, threshold: float):
            self.threshold = threshold

        def evaluate(self, symbol, market, as_of, reader):
            return None

    def build_plugin(settings, cfg):
        plugin_cfg = cfg.parse_analysis_plugin_config("plugin_quality", PluginConfig)
        return ConfiguredSignal(threshold=plugin_cfg.threshold)

    cfg = SourcesConfig(analysis_plugin_settings={"plugin_quality": {"threshold": 0.7}})
    signals = _build_signals_from_specs(
        Settings.from_env({}), cfg, (SignalSpec("plugin_quality", build_plugin),)
    )

    assert len(signals) == 1
    assert signals[0].threshold == 0.7


def test_builder_warns_for_unmatched_analysis_plugin_config(caplog):
    cfg = SourcesConfig(analysis_plugin_settings={"missing_signal": {"enabled": True}})

    with caplog.at_level(logging.WARNING):
        signals = _build_signals_from_specs(Settings.from_env({}), cfg, ())

    assert signals == []
    assert "analysis plugin config 'missing_signal' has no matching signal spec" in " ".join(
        r.message for r in caplog.records
    )


def test_builder_warns_when_analysis_plugin_namespace_targets_configurable_builtin_signal(
    caplog,
):
    cfg = SourcesConfig(analysis_plugin_settings={"news_volume": {"enabled": True}})

    with caplog.at_level(logging.WARNING):
        signals = _build_signals_from_specs(Settings.from_env({}), cfg, ())

    assert signals == []
    messages = " ".join(r.message for r in caplog.records)
    assert "analysis plugin config 'news_volume' targets built-in signal 'news_volume'" in messages
    assert "use analysis.news instead" in messages
    assert "has no matching signal spec" not in messages


def test_builder_warns_when_analysis_plugin_namespace_targets_llm_sentiment(caplog):
    cfg = SourcesConfig(analysis_plugin_settings={"llm_sentiment": {"enabled": True}})

    with caplog.at_level(logging.WARNING):
        signals = _build_signals_from_specs(Settings.from_env({}), cfg, ())

    assert signals == []
    messages = " ".join(r.message for r in caplog.records)
    assert (
        "analysis plugin config 'llm_sentiment' targets built-in signal 'llm_sentiment'"
        in messages
    )
    assert "use llm_sentiment_enabled instead" in messages
    assert "has no matching signal spec" not in messages


def test_gate_off_by_default():
    # No config, no settings -> today's 4 signals, byte-identical pipeline.
    signals = build_signals()
    assert _ids(signals) == BASE_SIGNAL_IDS
    assert len(signals) == 4


def test_default_path_does_not_import_anthropic():
    sys.modules.pop("anthropic", None)
    build_signals()
    assert "anthropic" not in sys.modules


def test_gate_requires_flag_even_with_key():
    cfg = SourcesConfig(llm_sentiment_enabled=False)
    settings = Settings(anthropic_api_key="sk-test")
    signals = build_signals(cfg, settings, classifier=_FakeClassifier())
    assert _ids(signals) == BASE_SIGNAL_IDS


def test_gate_requires_key_even_with_flag():
    cfg = SourcesConfig(llm_sentiment_enabled=True)
    settings = Settings(anthropic_api_key=None)
    signals = build_signals(cfg, settings, classifier=_FakeClassifier())
    assert _ids(signals) == BASE_SIGNAL_IDS


def test_gate_enabled_with_fake_classifier_appends_signal():
    cfg = SourcesConfig(llm_sentiment_enabled=True)
    settings = Settings(anthropic_api_key="sk-test")
    signals = build_signals(cfg, settings, classifier=_FakeClassifier())
    assert _ids(signals) == BASE_SIGNAL_IDS | {"llm_sentiment"}
    assert len(signals) == 5


def test_enabled_with_fake_classifier_does_not_import_anthropic():
    # Fake injection means the package gate is bypassed -> anthropic stays unimported.
    sys.modules.pop("anthropic", None)
    cfg = SourcesConfig(llm_sentiment_enabled=True)
    settings = Settings(anthropic_api_key="sk-test")
    build_signals(cfg, settings, classifier=_FakeClassifier())
    assert "anthropic" not in sys.modules


def test_build_signals_passes_macro_rate_series_config(tmp_path: Path):
    cfg = SourcesConfig(macro_regime_rate_series=["T10Y2Y"])
    macro = next(s for s in build_signals(cfg) if s.id == "macro_regime")
    assert isinstance(macro, MacroRegimeSignal)
    recs = [
        _macro_record("T10Y2Y", 1, 0.5),
        _macro_record("T10Y2Y", 20, 0.8),
    ]
    result = macro.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert result is not None


def test_build_signals_passes_news_aliases_to_news_volume(tmp_path: Path):
    cfg = SourcesConfig(news_aliases={"AAPL": ["Apple"]})
    news_volume = next(s for s in build_signals(cfg) if s.id == "news_volume")

    result = news_volume.evaluate(
        "AAPL",
        Market.US,
        AS_OF,
        _reader(tmp_path, [_news_record(31, "Apple supplier update", "")]),
    )

    assert result is not None
    assert result.signal == "news_volume"


def test_build_signals_uses_default_news_aliases_for_news_volume(tmp_path: Path):
    news_volume = next(s for s in build_signals() if s.id == "news_volume")

    result = news_volume.evaluate(
        "AAPL",
        Market.US,
        AS_OF,
        _reader(tmp_path, [_news_record(31, "Apple supplier update", "")]),
    )

    assert result is not None
    assert result.signal == "news_volume"


def test_build_signals_can_disable_default_news_aliases(tmp_path: Path):
    cfg = SourcesConfig(use_default_news_aliases=False)
    news_volume = next(s for s in build_signals(cfg) if s.id == "news_volume")

    result = news_volume.evaluate(
        "AAPL",
        Market.US,
        AS_OF,
        _reader(tmp_path, [_news_record(31, "Apple supplier update", "")]),
    )

    assert result is None


def test_build_signals_passes_news_aliases_to_llm_sentiment(tmp_path: Path):
    cfg = SourcesConfig(llm_sentiment_enabled=True, news_aliases={"AAPL": ["Apple"]})
    settings = Settings(anthropic_api_key="sk-test")
    llm_sentiment = next(
        s
        for s in build_signals(cfg, settings, classifier=_FakeClassifier())
        if s.id == "llm_sentiment"
    )

    result = llm_sentiment.evaluate(
        "AAPL",
        Market.US,
        AS_OF,
        _reader(tmp_path, [_news_record(31, "Apple supplier update", "")]),
    )

    assert result is not None
    assert result.signal == "llm_sentiment"


def test_build_signals_uses_default_news_aliases_for_llm_sentiment(tmp_path: Path):
    cfg = SourcesConfig(llm_sentiment_enabled=True)
    settings = Settings(anthropic_api_key="sk-test")
    llm_sentiment = next(
        s
        for s in build_signals(cfg, settings, classifier=_FakeClassifier())
        if s.id == "llm_sentiment"
    )

    result = llm_sentiment.evaluate(
        "AAPL",
        Market.US,
        AS_OF,
        _reader(tmp_path, [_news_record(31, "Apple supplier update", "")]),
    )

    assert result is not None
    assert result.signal == "llm_sentiment"
