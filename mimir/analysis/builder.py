from __future__ import annotations

import importlib.util
import logging
from typing import TYPE_CHECKING

from mimir.analysis.news_aliases import merge_news_aliases
from mimir.analysis.signals.base import Signal
from mimir.analysis.signals.filing_event import FilingEventSignal
from mimir.analysis.signals.macro_regime import MacroRegimeSignal
from mimir.analysis.signals.news_volume import NewsVolumeSignal
from mimir.analysis.signals.price_momentum import PriceMomentumSignal
from mimir.settings import Settings
from mimir.sources.config import SourcesConfig

if TYPE_CHECKING:
    # Annotation-only: the classifier type lives in llm_sentiment, which lazily
    # imports `anthropic`. A runtime import here would defeat the off-by-default
    # invariant (loading the builder must never pull anthropic).
    from mimir.analysis.signals.llm_sentiment import HeadlineClassifier

logger = logging.getLogger(__name__)


def build_signals(
    config: SourcesConfig | None = None,
    settings: Settings | None = None,
    *,
    classifier: HeadlineClassifier | None = None,
) -> list[Signal]:
    """Build the analysis signal set.

    Off-by-default (INC5): the paid LLM news-sentiment signal is appended ONLY
    when config enables it AND a key is present AND `anthropic` is installed (the
    package check is bypassed when a fake `classifier` is injected for tests).
    With no args, returns exactly today's four signals and never imports
    `anthropic`.
    """
    cfg = config or SourcesConfig()
    news_aliases = merge_news_aliases(
        cfg.news_aliases,
        include_defaults=cfg.use_default_news_aliases,
    )
    signals: list[Signal] = [
        FilingEventSignal(),
        NewsVolumeSignal(aliases=news_aliases),
        PriceMomentumSignal(),
        MacroRegimeSignal(rate_series=cfg.macro_regime_rate_series),
    ]
    settings = settings or Settings()
    if _llm_sentiment_enabled(cfg, settings, classifier):
        # Local import — the default path never enters this branch, so loading
        # this module never pulls `anthropic` (off-by-default invariant).
        from mimir.analysis.signals.llm_sentiment import (
            AnthropicHeadlineClassifier,
            LlmSentimentSignal,
        )

        signals.append(
            LlmSentimentSignal(
                classifier=classifier or AnthropicHeadlineClassifier(settings.anthropic_api_key),
                max_headlines=cfg.llm_sentiment_max_headlines,
                aliases=news_aliases,
            )
        )
    return signals


def _llm_sentiment_enabled(
    cfg: SourcesConfig, settings: Settings, classifier: HeadlineClassifier | None
) -> bool:
    if not cfg.llm_sentiment_enabled:
        return False
    if not settings.anthropic_api_key:
        logger.warning(
            "llm_sentiment_enabled=true but ANTHROPIC_API_KEY is not set; signal disabled"
        )
        return False
    # A fake classifier (tests) needs no SDK; only the real path requires the package.
    if classifier is None and importlib.util.find_spec("anthropic") is None:
        logger.warning(
            "llm_sentiment_enabled=true but 'anthropic' is not installed "
            "(pip install -e '.[llm]'); signal disabled"
        )
        return False
    return True
