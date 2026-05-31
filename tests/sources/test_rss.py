from datetime import UTC, datetime

import requests
import responses

from mimir.core.source import Cadence, Dataset, FetchContext, LegalStatus
from mimir.sources.rss import RssFeed, RssSource

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Example</title>
  <item>
    <title>Big news headline</title>
    <link>https://example.test/news/1</link>
    <pubDate>Fri, 29 May 2026 13:00:00 GMT</pubDate>
    <description>Short summary.</description>
  </item>
</channel></rss>
"""

FEEDS = [RssFeed(url="https://example.test/feed", publisher="Example", market="US")]


def _ctx():
    return FetchContext(watchlist={"us": [], "kr": []}, now=datetime(2026, 5, 31, tzinfo=UTC))


@responses.activate
def test_rss_parses_entries():
    responses.add(responses.GET, "https://example.test/feed", body=RSS, status=200)
    src = RssSource(feeds=FEEDS, session=requests.Session())
    recs = list(src.fetch(_ctx()))
    assert len(recs) == 1
    rec = recs[0]
    assert rec.symbol is None
    assert rec.idempotency_key == "rss:https://example.test/news/1"
    assert rec.payload["title"] == "Big news headline"
    assert rec.payload["publisher"] == "Example"
    assert rec.payload["market"] == "US"
    assert rec.ts == datetime(2026, 5, 29, 13, 0, 0, tzinfo=UTC)


def test_rss_meta():
    assert RssSource.meta.dataset is Dataset.NEWS
    assert RssSource.meta.cadence is Cadence.HOURLY
    assert RssSource.meta.legal_status is LegalStatus.OFFICIAL
