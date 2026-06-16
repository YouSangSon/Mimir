import pytest

from mimir.sources.rss import RssFeed
from mimir.sources.rss_catalog import (
    RssCatalogSelection,
    resolve_rss_catalogs,
    resolve_rss_feeds,
)


def test_resolve_known_rss_catalog_id():
    feeds = resolve_rss_catalogs([RssCatalogSelection(id="sec_press_releases")])

    assert feeds == [
        RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        )
    ]


def test_resolve_known_rss_catalog_returns_copy():
    feeds = resolve_rss_catalogs([RssCatalogSelection(id="sec_press_releases")])
    feeds[0].publisher = "Mutated"

    resolved_again = resolve_rss_catalogs([RssCatalogSelection(id="sec_press_releases")])

    assert resolved_again == [
        RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        )
    ]


def test_resolve_unknown_rss_catalog_id_raises_value_error():
    with pytest.raises(ValueError, match="unknown RSS catalog id: nope"):
        resolve_rss_catalogs([RssCatalogSelection(id="nope")])


def test_resolve_duplicate_catalog_selection_raises_value_error():
    with pytest.raises(ValueError, match="duplicate RSS feed"):
        resolve_rss_catalogs(
            [
                RssCatalogSelection(id="sec_press_releases"),
                RssCatalogSelection(id="sec_press_releases"),
            ]
        )


def test_resolve_rss_feeds_combines_catalogs_before_manual_feeds():
    manual = RssFeed(
        url="https://example.com/aapl.rss",
        publisher="Example",
        market="US",
        symbol="AAPL",
    )

    feeds = resolve_rss_feeds([RssCatalogSelection(id="sec_press_releases")], [manual])

    assert feeds == [
        RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        ),
        manual,
    ]


def test_resolve_rss_feeds_returns_none_when_no_catalog_or_manual_feeds():
    assert resolve_rss_feeds(None, None) is None


def test_resolve_rss_feeds_rejects_duplicate_manual_and_catalog_feed():
    manual = RssFeed(
        url="https://www.sec.gov/news/pressreleases.rss",
        publisher="SEC",
        market="US",
    )

    with pytest.raises(ValueError, match="duplicate RSS feed"):
        resolve_rss_feeds([RssCatalogSelection(id="sec_press_releases")], [manual])


def test_resolve_rss_feeds_allows_same_url_for_different_symbols():
    aapl = RssFeed(
        url="https://example.com/company.rss",
        publisher="Example",
        market="US",
        symbol="AAPL",
    )
    msft = RssFeed(
        url="https://example.com/company.rss",
        publisher="Example",
        market="US",
        symbol="MSFT",
    )

    assert resolve_rss_feeds(None, [aapl, msft]) == [aapl, msft]
