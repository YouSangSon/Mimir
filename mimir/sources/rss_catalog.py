from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Literal
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


SEC_BROWSE_EDGAR_URL = "https://www.sec.gov/cgi-bin/browse-edgar"


class SecCompanyFilingFeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cik: str
    symbol: str | None = None
    forms: list[str] | None = None
    count: int = Field(default=40, ge=10, le=100)
    owner: Literal["exclude", "include", "only"] = "exclude"

    @field_validator("cik", mode="before")
    @classmethod
    def _normalize_cik(cls, value: object) -> str:
        cik = str(value).strip()
        if not cik or not cik.isdigit() or len(cik) > 10:
            raise ValueError("SEC CIK must be a 1-10 digit string")
        return cik.zfill(10)

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, value: str | None) -> str | None:
        if value is None:
            return None
        symbol = value.strip()
        if not symbol:
            raise ValueError("SEC filing feed symbol must not be blank")
        return symbol

    @field_validator("forms")
    @classmethod
    def _normalize_forms(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        forms: list[str] = []
        for form in value:
            normalized = form.strip()
            if not normalized:
                raise ValueError("SEC form type must not be blank")
            forms.append(normalized)
        return forms


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
    ),
    "sec_structured_usgaap": RssCatalogEntry(
        id="sec_structured_usgaap",
        feed=RssFeed(
            url="https://www.sec.gov/Archives/edgar/usgaap.rss.xml",
            publisher="SEC",
            market="US",
        ),
        description=(
            "SEC structured disclosure RSS feed for filings containing "
            "financial statements tagged with US GAAP or IFRS taxonomies."
        ),
        source_url="https://www.sec.gov/data-research/structured-data/structured-disclosure-rss-feeds",
        verified_on=date(2026, 6, 18),
    ),
    "sec_structured_risk_return": RssCatalogEntry(
        id="sec_structured_risk_return",
        feed=RssFeed(
            url="https://www.sec.gov/Archives/edgar/xbrl-rr.rss.xml",
            publisher="SEC",
            market="US",
        ),
        description=(
            "SEC structured disclosure RSS feed for mutual fund filings "
            "tagged with the US Mutual Fund Risk/Return taxonomy."
        ),
        source_url="https://www.sec.gov/data-research/structured-data/structured-disclosure-rss-feeds",
        verified_on=date(2026, 6, 18),
    ),
    "sec_structured_inline_xbrl": RssCatalogEntry(
        id="sec_structured_inline_xbrl",
        feed=RssFeed(
            url="https://www.sec.gov/Archives/edgar/xbrl-inline.rss.xml",
            publisher="SEC",
            market="US",
        ),
        description=(
            "SEC structured disclosure RSS feed for Inline XBRL filings "
            "containing financial statements tagged with US GAAP or IFRS taxonomies."
        ),
        source_url="https://www.sec.gov/data-research/structured-data/structured-disclosure-rss-feeds",
        verified_on=date(2026, 6, 18),
    ),
    "sec_structured_all_xbrl": RssCatalogEntry(
        id="sec_structured_all_xbrl",
        feed=RssFeed(
            url="https://www.sec.gov/Archives/edgar/xbrlrss.all.xml",
            publisher="SEC",
            market="US",
        ),
        description="SEC structured disclosure RSS feed for all XBRL filings submitted to the SEC.",
        source_url="https://www.sec.gov/data-research/structured-data/structured-disclosure-rss-feeds",
        verified_on=date(2026, 6, 18),
    ),
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
    sec_company_filings: Sequence[SecCompanyFilingFeed] | None = None,
) -> list[RssFeed] | None:
    feeds = [
        *resolve_rss_catalogs(selections),
        *resolve_sec_company_filing_feeds(sec_company_filings),
        *list(manual_feeds or ()),
    ]
    _validate_unique_feeds(feeds)
    return feeds or None


def resolve_sec_company_filing_feeds(
    selections: Sequence[SecCompanyFilingFeed] | None,
) -> list[RssFeed]:
    feeds: list[RssFeed] = []
    for selection in selections or ():
        forms: Sequence[str | None] = selection.forms or (None,)
        for form in forms:
            feeds.append(
                RssFeed(
                    url=_sec_company_filing_url(selection, form),
                    publisher="SEC",
                    market="US",
                    symbol=selection.symbol,
                )
            )
    _validate_unique_feeds(feeds)
    return feeds


def _sec_company_filing_url(selection: SecCompanyFilingFeed, form: str | None) -> str:
    params: list[tuple[str, str]] = [
        ("action", "getcompany"),
        ("CIK", selection.cik),
    ]
    if form is not None:
        params.append(("type", form))
    params.extend(
        [
            ("owner", selection.owner),
            ("count", str(selection.count)),
            ("output", "atom"),
        ]
    )
    return f"{SEC_BROWSE_EDGAR_URL}?{urlencode(params)}"


def _validate_unique_feeds(feeds: Sequence[RssFeed]) -> None:
    seen: set[tuple[str, str | None]] = set()
    for feed in feeds:
        key = (feed.url, feed.symbol)
        if key in seen:
            suffix = f" for symbol {feed.symbol}" if feed.symbol else ""
            raise ValueError(f"duplicate RSS feed: {feed.url}{suffix}")
        seen.add(key)
