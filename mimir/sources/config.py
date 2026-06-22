from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mimir.report.i18n import DEFAULT_LANG, normalize_lang
from mimir.sources.ecos import EcosSeries
from mimir.sources.rss import RssFeed
from mimir.sources.rss_catalog import RssCatalogSelection, SecCompanyFilingFeed

PluginConfig = TypeVar("PluginConfig", bound=BaseModel)

DEFAULT_SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


class TickerCikMapRefresh(BaseModel):
    """Off-by-default opt-in for auto-refreshing the local SEC company_tickers.json.

    When ``enabled`` is false (default) the pipeline never touches the network for
    the mapping file — the operator keeps managing it manually (R1i behavior).
    """

    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    url: str = DEFAULT_SEC_TICKERS_URL
    max_age_hours: int = Field(default=168, ge=1)


class SourcesConfig(BaseModel):
    fred_series: list[str] | None = None
    ecos_series: list[EcosSeries] | None = None
    rss_feeds: list[RssFeed] | None = None
    rss_catalogs: list[RssCatalogSelection] | None = None
    rss_sec_company_filings: list[SecCompanyFilingFeed] | None = None
    rss_sec_ticker_cik_map_path: Path | None = None
    rss_sec_ticker_cik_map_refresh: TickerCikMapRefresh | None = None
    plugin_settings: dict[str, dict[str, Any]] = Field(default_factory=dict)
    macro_regime_rate_series: list[str] | None = None
    news_aliases: dict[str, list[str]] | None = None
    use_default_news_aliases: bool = True
    # INC5: off-by-default toggle for the paid LLM news-sentiment signal. Mirrors
    # the top-level `gray_enabled` key in sources.yaml (analysis-plane gate, not a
    # nested `sources:` block). `build_signals` requires this AND a key AND the
    # anthropic package before it registers the signal.
    llm_sentiment_enabled: bool = False
    llm_sentiment_max_headlines: int = Field(default=50, ge=1, le=50)

    def plugin_config(self, source_id: str) -> dict[str, Any]:
        """Return a copy of the plugin config block for ``source_id``."""
        return dict(self.plugin_settings.get(source_id, {}))

    def parse_plugin_config(
        self, source_id: str, model: type[PluginConfig]
    ) -> PluginConfig:
        """Validate a plugin config block with the plugin-owned pydantic model."""
        return model.model_validate(self.plugin_config(source_id))


class _FredBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    series: list[str] | None = None


class _EcosBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    series: list[EcosSeries] | None = None


class _RssSecBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_filings: list[SecCompanyFilingFeed] | None = None
    ticker_cik_map_path: Path | None = None
    ticker_cik_map_refresh: TickerCikMapRefresh | None = None

    @field_validator("ticker_cik_map_path", mode="before")
    @classmethod
    def _reject_blank_ticker_cik_map_path(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("SEC ticker CIK map path must not be blank")
        return value


class _RssBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feeds: list[RssFeed] | None = None
    catalogs: list[RssCatalogSelection] | None = None
    sec: _RssSecBlock | None = None


class _SourcesBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fred: _FredBlock | None = None
    ecos: _EcosBlock | None = None
    rss: _RssBlock | None = None
    plugins: dict[str, dict[str, Any]] | None = None


class _MacroRegimeBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rate_series: list[str] | None = None


class _NewsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aliases: dict[str, list[str]] | None = None
    use_default_aliases: bool = True


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
    llm_sentiment_max_headlines: int = Field(default=50, ge=1, le=50)
    analysis: _AnalysisBlock | None = None


class RuntimeSourcesConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_config: SourcesConfig = Field(default_factory=SourcesConfig)
    gray_enabled: bool = True
    disabled_ids: tuple[str, ...] = ()
    lang: str = DEFAULT_LANG


def _source_config_from_top_level(top_level: _TopLevelSourcesConfig) -> SourcesConfig:
    block = top_level.sources or _SourcesBlock()
    news_block = top_level.analysis.news if top_level.analysis and top_level.analysis.news else None
    return SourcesConfig(
        fred_series=block.fred.series if block.fred else None,
        ecos_series=block.ecos.series if block.ecos else None,
        rss_feeds=block.rss.feeds if block.rss else None,
        rss_catalogs=block.rss.catalogs if block.rss else None,
        rss_sec_company_filings=(
            block.rss.sec.company_filings if block.rss and block.rss.sec else None
        ),
        rss_sec_ticker_cik_map_path=(
            block.rss.sec.ticker_cik_map_path if block.rss and block.rss.sec else None
        ),
        rss_sec_ticker_cik_map_refresh=(
            block.rss.sec.ticker_cik_map_refresh if block.rss and block.rss.sec else None
        ),
        plugin_settings=block.plugins or {},
        macro_regime_rate_series=(
            top_level.analysis.macro_regime.rate_series
            if top_level.analysis and top_level.analysis.macro_regime
            else None
        ),
        news_aliases=news_block.aliases if news_block else None,
        use_default_news_aliases=news_block.use_default_aliases if news_block else True,
        # Top-level analysis-plane toggles (siblings of gray_enabled), not under `sources:`.
        llm_sentiment_enabled=top_level.llm_sentiment_enabled,
        llm_sentiment_max_headlines=top_level.llm_sentiment_max_headlines,
    )


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
    return _source_config_from_top_level(top_level)


def parse_runtime_sources_config(raw: dict[str, Any]) -> RuntimeSourcesConfig:
    top_level = _TopLevelSourcesConfig.model_validate(raw)
    return RuntimeSourcesConfig(
        source_config=_source_config_from_top_level(top_level),
        gray_enabled=top_level.gray_enabled,
        disabled_ids=tuple(top_level.disabled_ids or ()),
        lang=normalize_lang(top_level.lang),
    )
