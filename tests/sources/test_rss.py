from datetime import UTC, datetime

import requests
import responses

from mimir.core.source import Cadence, Dataset, FetchContext, LegalStatus
from mimir.sources.rss import RssFeed, RssSource
from mimir.sources.rss_catalog import RssCatalogSelection, resolve_rss_feeds

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
SYMBOL_FEEDS = [
    RssFeed(url="https://example.test/feed", publisher="Example", market="US", symbol="AAPL")
]
MULTI_SYMBOL_FEEDS = [
    RssFeed(url="https://example.test/aapl", publisher="Example", market="US", symbol="AAPL"),
    RssFeed(url="https://example.test/msft", publisher="Example", market="US", symbol="MSFT"),
]


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


@responses.activate
def test_rss_fetches_catalog_resolved_feed_with_existing_key_format():
    responses.add(
        responses.GET,
        "https://www.sec.gov/news/pressreleases.rss",
        body=RSS,
        status=200,
    )
    feeds = resolve_rss_feeds([RssCatalogSelection(id="sec_press_releases")], None)
    src = RssSource(feeds=feeds, session=requests.Session())

    recs = list(src.fetch(_ctx()))

    assert len(recs) == 1
    assert recs[0].symbol is None
    assert recs[0].idempotency_key == "rss:https://example.test/news/1"


@responses.activate
def test_rss_parses_entries_with_feed_symbol():
    responses.add(responses.GET, "https://example.test/feed", body=RSS, status=200)
    src = RssSource(feeds=SYMBOL_FEEDS, session=requests.Session())

    recs = list(src.fetch(_ctx()))

    assert len(recs) == 1
    rec = recs[0]
    assert rec.symbol == "AAPL"
    assert rec.idempotency_key == "rss:AAPL:https://example.test/news/1"
    assert rec.payload == {
        "title": "Big news headline",
        "url": "https://example.test/news/1",
        "publisher": "Example",
        "market": "US",
        "published_at": "Fri, 29 May 2026 13:00:00 GMT",
        "summary": "Short summary.",
    }


@responses.activate
def test_rss_symbol_feed_key_keeps_same_url_for_multiple_symbols():
    responses.add(responses.GET, "https://example.test/aapl", body=RSS, status=200)
    responses.add(responses.GET, "https://example.test/msft", body=RSS, status=200)
    src = RssSource(feeds=MULTI_SYMBOL_FEEDS, session=requests.Session())

    recs = list(src.fetch(_ctx()))

    assert [(rec.symbol, rec.idempotency_key) for rec in recs] == [
        ("AAPL", "rss:AAPL:https://example.test/news/1"),
        ("MSFT", "rss:MSFT:https://example.test/news/1"),
    ]


def test_rss_meta():
    assert RssSource.meta.dataset is Dataset.NEWS
    assert RssSource.meta.cadence is Cadence.HOURLY
    assert RssSource.meta.legal_status is LegalStatus.OFFICIAL
