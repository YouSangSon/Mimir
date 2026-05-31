from __future__ import annotations

import calendar
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any

import feedparser
import requests
from pydantic import BaseModel

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
    url: str
    publisher: str
    market: str  # US | KR | GLOBAL — recorded in payload (envelope market stays GLOBAL)


# Official, headline/metadata-only feeds. Override via constructor / config.
DEFAULT_FEEDS = [
    RssFeed(url="https://www.sec.gov/news/pressreleases.rss", publisher="SEC", market="US"),
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
    ) -> None:
        super().__init__(session=session, throttle=throttle)
        self._feeds = feeds or list(DEFAULT_FEEDS)
        self._parse_fn = parse_fn

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        for feed in self._feeds:
            resp = self.get(feed.url)
            parsed = self._parse_fn(resp.text)
            for entry in parsed.entries:
                link = entry.get("link")
                ts = _entry_ts(entry)
                if not link or ts is None:
                    # No stable publish date -> skip. Stamping ctx.now would land
                    # the same article in a different partition each run, defeating
                    # dedup and inflating news-volume counts.
                    continue
                yield RawRecord(
                    symbol=None,
                    ts=ts,
                    idempotency_key=f"rss:{link}",
                    payload={
                        "title": entry.get("title"),
                        "url": link,
                        "publisher": feed.publisher,
                        "market": feed.market,
                        "published_at": entry.get("published"),
                        "summary": (entry.get("summary") or "")[:SUMMARY_MAX],
                    },
                )


def _entry_ts(entry: Any) -> datetime | None:
    parsed = entry.get("published_parsed")
    if parsed is not None:
        # feedparser normalizes published_parsed to UTC; timegm treats it as UTC.
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=UTC)
    return None
