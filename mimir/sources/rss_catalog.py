from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any, Literal, Self
from urllib.parse import urlencode

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

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


class _SecTickerCikMap(dict[str, str]):
    def __init__(self, *args: object, path: Path | None = None, **kwargs: str) -> None:
        super().__init__(*args, **kwargs)
        self.path = path


class SecCompanyFilingFeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cik: str | None = None
    ticker: str | None = None
    symbol: str | None = None
    forms: list[str] | None = None
    count: int = Field(default=40, ge=10, le=100)
    owner: Literal["exclude", "include", "only"] = "exclude"

    @field_validator("cik", mode="before")
    @classmethod
    def _normalize_cik(cls, value: object) -> str | None:
        if value is None:
            return None
        cik = str(value).strip()
        if not cik or not cik.isdigit() or len(cik) > 10:
            raise ValueError("SEC CIK must be a 1-10 digit string")
        return cik.zfill(10)

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker(cls, value: object) -> str | None:
        if value is None:
            return None
        ticker = str(value).strip().upper()
        if not ticker:
            raise ValueError("SEC filing feed ticker must not be blank")
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
        if any(ch.isspace() or ch not in allowed for ch in ticker):
            raise ValueError(
                "SEC filing feed ticker must contain only letters, digits, dots, or hyphens"
            )
        return ticker

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

    @model_validator(mode="after")
    def _validate_identifier(self) -> Self:
        if (self.cik is None) == (self.ticker is None):
            raise ValueError("SEC filing feed must set exactly one of cik or ticker")
        return self


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
    sec_ticker_cik_map: Mapping[str, str] | None = None,
) -> list[RssFeed] | None:
    feeds = [
        *resolve_rss_catalogs(selections),
        *resolve_sec_company_filing_feeds(sec_company_filings, sec_ticker_cik_map),
        *list(manual_feeds or ()),
    ]
    _validate_unique_feeds(feeds)
    return feeds or None


def resolve_sec_company_filing_feeds(
    selections: Sequence[SecCompanyFilingFeed] | None,
    sec_ticker_cik_map: Mapping[str, str] | None = None,
) -> list[RssFeed]:
    feeds: list[RssFeed] = []
    for selection in selections or ():
        forms: Sequence[str | None] = selection.forms or (None,)
        for form in forms:
            feeds.append(
                RssFeed(
                    url=_sec_company_filing_url(selection, form, sec_ticker_cik_map),
                    publisher="SEC",
                    market="US",
                    symbol=selection.symbol,
                )
            )
    _validate_unique_feeds(feeds)
    return feeds


def load_sec_ticker_cik_map(path: Path) -> dict[str, str]:
    """Read SEC's company_tickers.json shape into normalized ticker -> CIK data."""
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"SEC ticker CIK map file not found: {path}") from exc
    except OSError as exc:
        raise ValueError(f"SEC ticker CIK map file could not be read: {path}") from exc

    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"SEC ticker CIK map file is not valid JSON: {path}"
        ) from exc

    if not isinstance(raw, dict):
        raise ValueError(f"SEC ticker CIK map must be a JSON object: {path}")

    mapping = _SecTickerCikMap(path=path)
    for entry_key, entry in raw.items():
        ticker, cik = _parse_sec_ticker_cik_entry(
            entry,
            path=path,
            entry_key=entry_key,
        )
        existing = mapping.get(ticker)
        if existing is not None and existing != cik:
            raise ValueError(
                f"ambiguous SEC ticker mapping for {ticker} in {path} "
                f"at entry {entry_key!r}"
            )
        mapping[ticker] = cik
    return mapping


def _parse_sec_ticker_cik_entry(
    entry: object,
    *,
    path: Path,
    entry_key: object,
) -> tuple[str, str]:
    if not isinstance(entry, dict):
        raise ValueError(
            f"SEC ticker CIK map entry {entry_key!r} must be a JSON object: {path}"
        )
    try:
        ticker = _normalize_ticker_value(entry.get("ticker"))
        cik = _normalize_cik_value(entry.get("cik_str"))
    except ValidationError as exc:
        raise ValueError(
            f"invalid SEC ticker CIK map entry {entry_key!r} in {path}: {exc}"
        ) from exc
    return ticker, cik


def _normalize_ticker_value(value: Any) -> str:
    return SecCompanyFilingFeed(ticker=value).ticker or ""


def _normalize_cik_value(value: Any) -> str:
    return SecCompanyFilingFeed(cik=value).cik or ""


def _sec_company_filing_url(
    selection: SecCompanyFilingFeed,
    form: str | None,
    sec_ticker_cik_map: Mapping[str, str] | None = None,
) -> str:
    identifier = _sec_company_filing_identifier(selection, sec_ticker_cik_map)
    params: list[tuple[str, str]] = [
        ("action", "getcompany"),
        ("CIK", identifier),
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


def _sec_company_filing_identifier(
    selection: SecCompanyFilingFeed,
    sec_ticker_cik_map: Mapping[str, str] | None = None,
) -> str:
    if selection.cik is not None:
        return selection.cik
    if selection.ticker is None:  # defensive; model validation guarantees this
        raise ValueError("SEC filing feed must set exactly one of cik or ticker")
    if sec_ticker_cik_map is None:
        return selection.ticker
    cik = sec_ticker_cik_map.get(selection.ticker)
    if cik is None:
        mapping_path = getattr(sec_ticker_cik_map, "path", None)
        if isinstance(mapping_path, Path):
            raise ValueError(
                f"SEC ticker CIK map has no entry for ticker {selection.ticker} in {mapping_path}"
            )
        raise ValueError(
            f"SEC ticker CIK map has no entry for ticker {selection.ticker}"
        )
    return cik


def _validate_unique_feeds(feeds: Sequence[RssFeed]) -> None:
    seen: set[tuple[str, str | None]] = set()
    for feed in feeds:
        key = (feed.url, feed.symbol)
        if key in seen:
            suffix = f" for symbol {feed.symbol}" if feed.symbol else ""
            raise ValueError(f"duplicate RSS feed: {feed.url}{suffix}")
        seen.add(key)
