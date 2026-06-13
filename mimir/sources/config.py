from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from mimir.sources.ecos import EcosSeries
from mimir.sources.rss import RssFeed


class SourcesConfig(BaseModel):
    fred_series: list[str] | None = None
    ecos_series: list[EcosSeries] | None = None
    rss_feeds: list[RssFeed] | None = None


def parse_sources_config(raw: dict[str, Any]) -> SourcesConfig:
    """Read the optional ``raw['sources']`` block into a validated model.

    Absent keys map to ``None`` ("keep the code default"); an explicit empty list
    means "zero series" and is preserved. Malformed input raises
    ``pydantic.ValidationError`` — never a silent fallback to defaults.
    """
    sources = raw.get("sources") or {}
    fred = sources.get("fred") or {}
    ecos = sources.get("ecos") or {}
    rss = sources.get("rss") or {}
    return SourcesConfig(
        fred_series=fred.get("series"),
        ecos_series=ecos.get("series"),
        rss_feeds=rss.get("feeds"),
    )
