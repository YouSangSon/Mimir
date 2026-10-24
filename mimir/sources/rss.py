from __future__ import annotations

import calendar
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any

import feedparser
import requests
from pydantic import BaseModel, ConfigDict, PrivateAttr, field_validator

from mimir.core.provenance import SourceProvenance, UsageRights, public_url, require_rights
from mimir.core.source import (
    Cadence,
    Dataset,
    FetchContext,
    LegalStatus,
    Market,
    RateLimit,
    RawRecord,
    SourceMeta,
)
from mimir.core.throttle import Throttle
from mimir.sources.base import BaseSource

SUMMARY_MAX = 500  # store only a short summary; never full article text (copyright)


class RssFeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    publisher: str
    market: str  # US | KR | GLOBAL — recorded in payload (envelope market stays GLOBAL)
    symbol: str | None = None
    provenance: UsageRights | None = None
    _builtin_route: str | None = PrivateAttr(default=None)
    _builtin_url: str | None = PrivateAttr(default=None)

    _url = field_validator("url")(public_url)

    def snapshot(self) -> SourceProvenance:
        builtin = (
            self._builtin_route is not None and self.url == self._builtin_url
            and self.provenance is None
        )
        rights = None if builtin else require_rights(self.url, self.provenance)
        return SourceProvenance(
            target=self.url, publisher=self.publisher, source_url=self.url,
            origin="rss_builtin" if builtin else "rss_manual",
            route=(self._builtin_route or "") if builtin else "sources.rss.feeds", rights=rights,
        )

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, value: str | None) -> str | None:
        if value is None:
            return None
        symbol = value.strip()
        if not symbol:
            raise ValueError("RSS feed symbol must not be blank")
        return symbol


def mark_builtin_feed(feed: RssFeed, route: str) -> RssFeed:
    """Code-only discovery marker; operator YAML cannot set private attributes."""
    feed._builtin_route = route
    feed._builtin_url = feed.url
    return feed


# Discovery evidence only; no blanket commercial-rights approval.
DEFAULT_FEEDS = [
    mark_builtin_feed(
        RssFeed(url="https://www.sec.gov/news/pressreleases.rss", publisher="SEC", market="US"),
        "default:sec_press_releases",
    ),
]


class RssSource(BaseSource):
    meta = SourceMeta(
        id="rss",
        market=Market.GLOBAL,
        dataset=Dataset.NEWS,
        cadence=Cadence.HOURLY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1.0),
    )

    def __init__(
        self,
        *,
        feeds: list[RssFeed] | None = None,
        parse_fn: Callable[[Any], Any] = feedparser.parse,
        session: requests.Session | None = None,
        throttle: Throttle | None = None,
        user_agent: str | None = None,
    ) -> None:
        super().__init__(session=session, throttle=throttle)
        self._feeds = [feed.model_copy(deep=True) for feed in (feeds or DEFAULT_FEEDS)]
        for feed in self._feeds:
            feed.snapshot()
        self._parse_fn = parse_fn
        self._headers = {"User-Agent": user_agent} if user_agent else None

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        for feed in self._feeds:
            resp = self.get(feed.url, headers=self._headers)
            parsed = self._parse_fn(resp.text)
            for entry in parsed.entries:
                link = entry.get("link")
                ts = _entry_ts(entry)
                if not link or ts is None:
                    # No stable publish date -> skip. Stamping ctx.now would land
                    # the same article in a different partition each run, defeating
                    # dedup and inflating news-volume counts.
                    continue
                key = f"rss:{feed.symbol}:{link}" if feed.symbol else f"rss:{link}"
                yield RawRecord(
                    symbol=feed.symbol,
                    ts=ts,
                    idempotency_key=key,
                    payload={
                        "title": entry.get("title"),
                        "url": link,
                        "publisher": feed.publisher,
                        "market": feed.market,
                        "published_at": entry.get("published"),
                        "summary": (entry.get("summary") or "")[:SUMMARY_MAX],
                        "feed_url": feed.url,
                        "provenance": feed.snapshot().model_dump(mode="json"),
                    },
                )


def _entry_ts(entry: Any) -> datetime | None:
    parsed = entry.get("published_parsed")
    if parsed is not None:
        # feedparser normalizes published_parsed to UTC; timegm treats it as UTC.
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=UTC)
    return None
