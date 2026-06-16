from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from pydantic import BaseModel, ConfigDict

from mimir.sources.rss import RssFeed


class RssCatalogSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str


class RssCatalogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    feed: RssFeed
    description: str
    source_url: str
    verified_on: date


RSS_CATALOG: dict[str, RssCatalogEntry] = {
    "sec_press_releases": RssCatalogEntry(
        id="sec_press_releases",
        feed=RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        ),
        description="SEC press releases RSS feed.",
        source_url="https://www.sec.gov/about/rss-feeds",
        verified_on=date(2026, 6, 16),
    )
}


def resolve_rss_catalogs(
    selections: Sequence[RssCatalogSelection] | None,
) -> list[RssFeed]:
    feeds: list[RssFeed] = []
    for selection in selections or ():
        entry = RSS_CATALOG.get(selection.id)
        if entry is None:
            raise ValueError(f"unknown RSS catalog id: {selection.id}")
        feeds.append(entry.feed.model_copy(deep=True))
    _validate_unique_feeds(feeds)
    return feeds


def resolve_rss_feeds(
    selections: Sequence[RssCatalogSelection] | None,
    manual_feeds: Sequence[RssFeed] | None,
) -> list[RssFeed] | None:
    feeds = [*resolve_rss_catalogs(selections), *list(manual_feeds or ())]
    _validate_unique_feeds(feeds)
    return feeds or None


def _validate_unique_feeds(feeds: Sequence[RssFeed]) -> None:
    seen: set[tuple[str, str | None]] = set()
    for feed in feeds:
        key = (feed.url, feed.symbol)
        if key in seen:
            suffix = f" for symbol {feed.symbol}" if feed.symbol else ""
            raise ValueError(f"duplicate RSS feed: {feed.url}{suffix}")
        seen.add(key)
