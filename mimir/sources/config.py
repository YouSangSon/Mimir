from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from mimir.sources.ecos import EcosSeries
from mimir.sources.rss import RssFeed


class SourcesConfig(BaseModel):
    fred_series: list[str] | None = None
    ecos_series: list[EcosSeries] | None = None
    rss_feeds: list[RssFeed] | None = None


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


def parse_sources_config(raw: dict[str, Any]) -> SourcesConfig:
    """Read the optional ``raw['sources']`` block into a validated model.

    Absent keys map to ``None`` ("keep the code default"). Malformed input — a
    non-mapping block, a wrong-typed field, or a typo'd key/block name — raises
    ``pydantic.ValidationError`` (``extra="forbid"`` rejects unknown keys), never
    a silent fallback to defaults. To turn a source off entirely use
    ``disabled_ids`` in sources.yaml, not an empty series list.
    """
    # Collapse only an absent/None block to defaults; any other non-mapping
    # (0, false, [], "x") is malformed and must raise — not silently fall back.
    raw_sources = raw.get("sources")
    block = _SourcesBlock.model_validate({} if raw_sources is None else raw_sources)
    return SourcesConfig(
        fred_series=block.fred.series if block.fred else None,
        ecos_series=block.ecos.series if block.ecos else None,
        rss_feeds=block.rss.feeds if block.rss else None,
    )
