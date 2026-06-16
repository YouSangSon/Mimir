"""build_signals() gate — off-by-default LLM sentiment signal (INC5).

The gate is a three-condition AND: config flag + ANTHROPIC_API_KEY + anthropic
installed (the package check is bypassed when a fake classifier is injected).
With no config/settings, build_signals() must return exactly today's 4 signals
and must NOT import `anthropic`.
"""

import sys
from datetime import UTC, date, datetime
from pathlib import Path

from mimir.analysis.builder import build_signals
from mimir.analysis.signals.base import SignalDirection
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


def _reader(tmp_path: Path, records: list[Record]) -> DataReader:
    store = JsonlStore(root=tmp_path)
    store.append(records)
    return DataReader(store)


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
