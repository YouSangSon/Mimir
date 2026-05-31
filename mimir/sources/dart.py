from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from mimir.core.errors import FetchError
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

LIST_URL = "https://opendart.fss.or.kr/api/list.json"
PAGE_COUNT = 100
MAX_PAGES = 100  # safety cap on pagination


class DartSource(BaseSource):
    meta = SourceMeta(
        id="dart",
        market=Market.KR,
        dataset=Dataset.FILINGS,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=2.0),
        requires_secret="DART_API_KEY",
    )

    def __init__(
        self,
        *,
        api_key: str,
        session: requests.Session | None = None,
        throttle: Throttle | None = None,
    ) -> None:
        super().__init__(session=session, throttle=throttle)
        self._api_key = api_key

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        wanted = set(ctx.watchlist.get("kr", []))
        if not wanted:
            return
        since = ctx.backfill_since or (ctx.now.date() - timedelta(days=1))
        # list.json returns market-wide filings 100 at a time; page through all of
        # them (total_page) so a watchlist company past the first page isn't lost.
        page_no = 1
        while page_no <= MAX_PAGES:
            params = {
                "crtfc_key": self._api_key,
                "bgn_de": since.strftime("%Y%m%d"),
                "end_de": ctx.now.strftime("%Y%m%d"),
                "page_no": str(page_no),
                "page_count": str(PAGE_COUNT),
            }
            data = self.get(LIST_URL, params=params).json()
            status = data.get("status")
            if status == "013":  # no data for the query
                return
            if status != "000":
                raise FetchError(f"DART error status={status}: {data.get('message')}")
            for item in data.get("list", []):
                rec = self._to_record(item, wanted)
                if rec is not None:
                    yield rec
            if page_no >= int(data.get("total_page", 1) or 1):
                return
            page_no += 1

    @staticmethod
    def _to_record(item: dict[str, Any], wanted: set[str]) -> RawRecord | None:
        code = item.get("stock_code")
        if code not in wanted:
            return None
        rcept_no = item.get("rcept_no")
        rcept_dt = item.get("rcept_dt")
        if not rcept_no or not rcept_dt:
            return None  # missing keys: skip this item, don't abort the batch
        ts = datetime.strptime(rcept_dt, "%Y%m%d").replace(tzinfo=UTC)
        return RawRecord(
            symbol=code,
            ts=ts,
            idempotency_key=f"dart:{rcept_no}",
            payload={
                "form_type": item.get("report_nm"),
                "title": item.get("report_nm"),
                "corp_name": item.get("corp_name"),
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                "filed_at": item.get("rcept_dt"),
                "flr_nm": item.get("flr_nm"),
            },
        )
