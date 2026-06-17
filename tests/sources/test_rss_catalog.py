import pytest
from pydantic import ValidationError

from mimir.sources.rss import RssFeed
from mimir.sources.rss_catalog import (
    RssCatalogSelection,
    SecCompanyFilingFeed,
    load_sec_ticker_cik_map,
    resolve_rss_catalogs,
    resolve_rss_feeds,
)

STRUCTURED_FEEDS = [
    (
        "sec_structured_usgaap",
        "https://www.sec.gov/Archives/edgar/usgaap.rss.xml",
    ),
    (
        "sec_structured_risk_return",
        "https://www.sec.gov/Archives/edgar/xbrl-rr.rss.xml",
    ),
    (
        "sec_structured_inline_xbrl",
        "https://www.sec.gov/Archives/edgar/xbrl-inline.rss.xml",
    ),
    (
        "sec_structured_all_xbrl",
        "https://www.sec.gov/Archives/edgar/xbrlrss.all.xml",
    ),
]


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


@pytest.mark.parametrize(("catalog_id", "url"), STRUCTURED_FEEDS)
def test_resolve_sec_structured_rss_catalog_ids(catalog_id: str, url: str):
    feeds = resolve_rss_catalogs([RssCatalogSelection(id=catalog_id)])

    assert feeds == [
        RssFeed(
            url=url,
            publisher="SEC",
            market="US",
        )
    ]


@pytest.mark.parametrize(("catalog_id", "url"), STRUCTURED_FEEDS)
def test_resolve_sec_structured_rss_catalog_returns_copy(catalog_id: str, url: str):
    feeds = resolve_rss_catalogs([RssCatalogSelection(id=catalog_id)])
    feeds[0].publisher = "Mutated"

    resolved_again = resolve_rss_catalogs([RssCatalogSelection(id=catalog_id)])

    assert resolved_again == [
        RssFeed(
            url=url,
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


def test_resolve_rss_feeds_rejects_duplicate_manual_and_structured_catalog_feed():
    manual = RssFeed(
        url="https://www.sec.gov/Archives/edgar/xbrlrss.all.xml",
        publisher="SEC",
        market="US",
    )

    with pytest.raises(ValueError, match="duplicate RSS feed"):
        resolve_rss_feeds([RssCatalogSelection(id="sec_structured_all_xbrl")], [manual])


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


def test_resolve_sec_company_filing_feed_with_ticker():
    feeds = resolve_rss_feeds(
        None,
        None,
        [SecCompanyFilingFeed(ticker=" aapl ", symbol="AAPL")],
    )

    assert feeds == [
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=AAPL&owner=exclude&count=40&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        )
    ]


def test_resolve_sec_company_filing_feed_maps_ticker_to_cik():
    feeds = resolve_rss_feeds(
        None,
        None,
        [SecCompanyFilingFeed(ticker=" aapl ", symbol="AAPL")],
        {"AAPL": "0000320193"},
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


def test_resolve_sec_company_filing_feed_missing_ticker_mapping_raises():
    with pytest.raises(ValueError, match="SEC ticker CIK map has no entry for ticker MSFT"):
        resolve_rss_feeds(
            None,
            None,
            [SecCompanyFilingFeed(ticker="MSFT", symbol="MSFT")],
            {"AAPL": "0000320193"},
        )


def test_resolve_sec_company_filing_feed_missing_loaded_ticker_mapping_includes_path(
    tmp_path,
):
    path = tmp_path / "company_tickers.json"
    path.write_text(
        """
        {
          "0": {"cik_str": 320193, "ticker": "aapl", "title": "Apple Inc."}
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"SEC ticker CIK map has no entry for ticker MSFT in .*company_tickers\.json",
    ):
        resolve_rss_feeds(
            None,
            None,
            [SecCompanyFilingFeed(ticker="MSFT", symbol="MSFT")],
            load_sec_ticker_cik_map(path),
        )


def test_load_sec_ticker_cik_map_reads_official_json_shape(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text(
        """
        {
          "0": {"cik_str": 320193, "ticker": "aapl", "title": "Apple Inc."},
          "1": {"cik_str": "789019", "ticker": "MSFT", "title": "Microsoft Corp."}
        }
        """,
        encoding="utf-8",
    )

    assert load_sec_ticker_cik_map(path) == {
        "AAPL": "0000320193",
        "MSFT": "0000789019",
    }


def test_load_sec_ticker_cik_map_missing_file_raises_clear_error(tmp_path):
    path = tmp_path / "missing_company_tickers.json"

    with pytest.raises(
        ValueError,
        match=r"SEC ticker CIK map file not found: .*missing_company_tickers\.json",
    ):
        load_sec_ticker_cik_map(path)


def test_load_sec_ticker_cik_map_unreadable_file_raises_clear_error(tmp_path):
    path = tmp_path / "company_tickers_directory.json"
    path.mkdir()

    with pytest.raises(
        ValueError,
        match=r"SEC ticker CIK map file could not be read: .*company_tickers_directory\.json",
    ):
        load_sec_ticker_cik_map(path)


def test_load_sec_ticker_cik_map_invalid_json_raises_clear_error(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"SEC ticker CIK map file is not valid JSON: .*company_tickers\.json",
    ):
        load_sec_ticker_cik_map(path)


def test_load_sec_ticker_cik_map_rejects_non_object_json(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"SEC ticker CIK map must be a JSON object: .*company_tickers\.json",
    ):
        load_sec_ticker_cik_map(path)


def test_load_sec_ticker_cik_map_rejects_non_object_entry_with_context(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text('{"0": []}', encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"SEC ticker CIK map entry '0' must be a JSON object: .*company_tickers\.json",
    ):
        load_sec_ticker_cik_map(path)


def test_load_sec_ticker_cik_map_rejects_invalid_entry_ticker_with_context(
    tmp_path,
):
    path = tmp_path / "company_tickers.json"
    path.write_text(
        '{"0": {"cik_str": 320193, "ticker": "bad ticker"}}',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"invalid SEC ticker CIK map entry '0' in .*company_tickers\.json",
    ):
        load_sec_ticker_cik_map(path)


def test_load_sec_ticker_cik_map_rejects_missing_entry_cik_with_context(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text('{"0": {"ticker": "AAPL"}}', encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"invalid SEC ticker CIK map entry '0' in .*company_tickers\.json",
    ):
        load_sec_ticker_cik_map(path)


def test_load_sec_ticker_cik_map_rejects_invalid_entry_cik_with_context(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text(
        '{"0": {"cik_str": "not-a-cik", "ticker": "AAPL"}}',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"invalid SEC ticker CIK map entry '0' in .*company_tickers\.json",
    ):
        load_sec_ticker_cik_map(path)


def test_load_sec_ticker_cik_map_rejects_ambiguous_duplicate_ticker(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text(
        """
        {
          "0": {"cik_str": 1, "ticker": "DUP", "title": "One"},
          "1": {"cik_str": 2, "ticker": "dup", "title": "Two"}
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"ambiguous SEC ticker mapping for DUP in .*company_tickers\.json at entry '1'",
    ):
        load_sec_ticker_cik_map(path)


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


def test_resolve_sec_company_filing_feeds_with_ticker_and_form_filters():
    feeds = resolve_rss_feeds(
        None,
        None,
        [
            SecCompanyFilingFeed(
                ticker="brk-b",
                symbol="BRK.B",
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
                "action=getcompany&CIK=BRK-B&type=10-K&owner=include&count=20&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="BRK.B",
        ),
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=BRK-B&type=10-K%2FA&owner=include&count=20&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="BRK.B",
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


def test_resolve_rss_feeds_rejects_duplicate_ticker_sec_and_manual_feed():
    manual = RssFeed(
        url=(
            "https://www.sec.gov/cgi-bin/browse-edgar?"
            "action=getcompany&CIK=AAPL&owner=exclude&count=40&output=atom"
        ),
        publisher="SEC",
        market="US",
        symbol="AAPL",
    )

    with pytest.raises(ValueError, match="duplicate RSS feed"):
        resolve_rss_feeds(None, [manual], [SecCompanyFilingFeed(ticker="AAPL", symbol="AAPL")])


@pytest.mark.parametrize("bad_cik", ["", "ABC", "12345678901"])
def test_sec_company_filing_feed_rejects_bad_cik(bad_cik: str):
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed(cik=bad_cik)


def test_sec_company_filing_feed_rejects_missing_identifier():
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed()


def test_sec_company_filing_feed_rejects_both_cik_and_ticker():
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed(cik="320193", ticker="AAPL")


@pytest.mark.parametrize("bad_ticker", ["", "  ", "A APL", "AAPL/US"])
def test_sec_company_filing_feed_rejects_bad_ticker(bad_ticker: str):
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed(ticker=bad_ticker)


def test_sec_company_filing_feed_rejects_blank_form():
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed(cik="320193", forms=["10-K", "  "])


@pytest.mark.parametrize("bad_count", [9, 101])
def test_sec_company_filing_feed_rejects_count_out_of_bounds(bad_count: int):
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed(cik="320193", count=bad_count)
