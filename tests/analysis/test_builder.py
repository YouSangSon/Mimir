"""build_signals() gate — off-by-default LLM sentiment signal (INC5).

The gate is a three-condition AND: config flag + ANTHROPIC_API_KEY + anthropic
installed (the package check is bypassed when a fake classifier is injected).
With no config/settings, build_signals() must return exactly today's 4 signals
and must NOT import `anthropic`.
"""

import sys

from mimir.analysis.builder import build_signals
from mimir.analysis.signals.base import SignalDirection
from mimir.analysis.signals.llm_sentiment import HeadlineVerdict
from mimir.settings import Settings
from mimir.sources.config import SourcesConfig

BASE_SIGNAL_IDS = {"filing_event", "news_volume", "price_momentum", "macro_regime"}


class _FakeClassifier:
    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]:
        return [
            HeadlineVerdict(direction=SignalDirection.NEUTRAL, confidence=0.0, rationale="")
            for _ in headlines
        ]


def _ids(signals) -> set[str]:
    return {s.id for s in signals}


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
