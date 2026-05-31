from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

import requests

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

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
RECENT_LIMIT = 50
DEFAULT_UA = "Mimir/0.1 (set MIMIR_SEC_USER_AGENT to your contact)"


class SecEdgarSource(BaseSource):
    meta = SourceMeta(
        id="sec_edgar",
        market=Market.US,
        dataset=Dataset.FILINGS,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=10.0),
    )

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        throttle: Throttle | None = None,
        user_agent: str = DEFAULT_UA,
    ) -> None:
        super().__init__(session=session, throttle=throttle)
        self._headers = {"User-Agent": user_agent}

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        cik_by_ticker = self._load_ticker_map()
        for symbol in ctx.watchlist.get("us", []):
            cik = cik_by_ticker.get(symbol.upper())
            if cik is None:
                continue
            yield from self._fetch_filings(symbol, cik)

    def _load_ticker_map(self) -> dict[str, str]:
        data = self.get(TICKERS_URL, headers=self._headers).json()
        return {row["ticker"].upper(): f"{int(row['cik_str']):010d}" for row in data.values()}

    def _fetch_filings(self, symbol: str, cik10: str) -> Iterable[RawRecord]:
        data = self.get(SUBMISSIONS_URL.format(cik10=cik10), headers=self._headers).json()
        recent = data.get("filings", {}).get("recent", {})
        accessions = recent.get("accessionNumber", [])[:RECENT_LIMIT]
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        docs = recent.get("primaryDocument", [])
        for i, accession in enumerate(accessions):
            if i >= len(dates) or not dates[i]:
                continue  # malformed parallel arrays: skip rather than abort the batch
            day = dates[i]
            ts = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
            no_dashes = accession.replace("-", "")
            doc = docs[i] if i < len(docs) else ""
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik10)}/{no_dashes}/{doc}"
            yield RawRecord(
                symbol=symbol,
                ts=ts,
                idempotency_key=f"sec_edgar:{cik10}:{accession}",
                payload={
                    "form_type": forms[i] if i < len(forms) else None,
                    "title": forms[i] if i < len(forms) else None,
                    "accession": accession,
                    "url": url,
                    "filed_at": day,
                },
            )
