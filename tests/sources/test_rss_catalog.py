import pytest
from pydantic import ValidationError

from mimir.sources.rss import RssFeed
from mimir.sources.rss_catalog import (
    RssCatalogSelection,
    SecCompanyFilingFeed,
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


def test_resolve_sec_company_filing_feed_without_form_filter():
    feeds = resolve_rss_feeds(
        None,
        None,
        [SecCompanyFilingFeed(cik="320193", symbol="AAPL")],
    )

    assert feeds == [
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=0000320193&owner=exclude&count=40&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        )
    ]


def test_resolve_sec_company_filing_feeds_with_encoded_form_filters():
    feeds = resolve_rss_feeds(
        None,
        None,
        [
            SecCompanyFilingFeed(
                cik="0000320193",
                symbol="AAPL",
                forms=["10-K", "10-K/A"],
                count=20,
                owner="include",
            )
        ],
    )

    assert feeds == [
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=0000320193&type=10-K&owner=include&count=20&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        ),
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=0000320193&type=10-K%2FA&owner=include&count=20&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        ),
    ]


def test_resolve_rss_feeds_rejects_duplicate_sec_and_manual_feed():
    manual = RssFeed(
        url=(
            "https://www.sec.gov/cgi-bin/browse-edgar?"
            "action=getcompany&CIK=0000320193&owner=exclude&count=40&output=atom"
        ),
        publisher="SEC",
        market="US",
        symbol="AAPL",
    )

    with pytest.raises(ValueError, match="duplicate RSS feed"):
        resolve_rss_feeds(None, [manual], [SecCompanyFilingFeed(cik="320193", symbol="AAPL")])


@pytest.mark.parametrize("bad_cik", ["", "ABC", "12345678901"])
def test_sec_company_filing_feed_rejects_bad_cik(bad_cik: str):
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed(cik=bad_cik)


def test_sec_company_filing_feed_rejects_blank_form():
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed(cik="320193", forms=["10-K", "  "])


@pytest.mark.parametrize("bad_count", [9, 101])
def test_sec_company_filing_feed_rejects_count_out_of_bounds(bad_count: int):
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed(cik="320193", count=bad_count)
