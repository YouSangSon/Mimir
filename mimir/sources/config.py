from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from mimir.sources.ecos import EcosSeries
from mimir.sources.rss import RssFeed


class SourcesConfig(BaseModel):
    fred_series: list[str] | None = None
    ecos_series: list[EcosSeries] | None = None
    rss_feeds: list[RssFeed] | None = None
    macro_regime_rate_series: list[str] | None = None
    news_aliases: dict[str, list[str]] | None = None
    # INC5: off-by-default toggle for the paid LLM news-sentiment signal. Mirrors
    # the top-level `gray_enabled` key in sources.yaml (analysis-plane gate, not a
    # nested `sources:` block). `build_signals` requires this AND a key AND the
    # anthropic package before it registers the signal.
    llm_sentiment_enabled: bool = False
    llm_sentiment_max_headlines: int = 50


class _FredBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    series: list[str] | None = None


class _EcosBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    series: list[EcosSeries] | None = None


class _RssBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feeds: list[RssFeed] | None = None


class _SourcesBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fred: _FredBlock | None = None
    ecos: _EcosBlock | None = None
    rss: _RssBlock | None = None


class _MacroRegimeBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rate_series: list[str] | None = None


class _NewsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aliases: dict[str, list[str]] | None = None


class _AnalysisBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    macro_regime: _MacroRegimeBlock | None = None
    news: _NewsBlock | None = None


class _TopLevelSourcesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: _SourcesBlock | None = None
    gray_enabled: bool = True
    disabled_ids: list[str] | None = None
    lang: str = "en"
    llm_sentiment_enabled: bool = False
    llm_sentiment_max_headlines: int = 50
    analysis: _AnalysisBlock | None = None


def parse_sources_config(raw: dict[str, Any]) -> SourcesConfig:
    """Read source and analysis-plane settings into a validated model.

    Absent source keys map to ``None`` ("keep the code default"). Malformed
    input — a non-mapping block, a wrong-typed field, or a typo'd key/block name
    — raises ``pydantic.ValidationError`` (``extra="forbid"`` rejects unknown
    keys), never a silent fallback to defaults. To turn a source off entirely
    use ``disabled_ids`` in sources.yaml, not an empty series list.
    """
    # Collapse only an absent/None block to defaults; any other non-mapping
    # (0, false, [], "x") is malformed and must raise — not silently fall back.
    top_level = _TopLevelSourcesConfig.model_validate(raw)
    block = top_level.sources or _SourcesBlock()
    return SourcesConfig(
        fred_series=block.fred.series if block.fred else None,
        ecos_series=block.ecos.series if block.ecos else None,
        rss_feeds=block.rss.feeds if block.rss else None,
        macro_regime_rate_series=(
            top_level.analysis.macro_regime.rate_series
            if top_level.analysis and top_level.analysis.macro_regime
            else None
        ),
        news_aliases=(
            top_level.analysis.news.aliases
            if top_level.analysis and top_level.analysis.news
            else None
        ),
        # Top-level analysis-plane toggles (siblings of gray_enabled), not under `sources:`.
        llm_sentiment_enabled=top_level.llm_sentiment_enabled,
        llm_sentiment_max_headlines=top_level.llm_sentiment_max_headlines,
    )
