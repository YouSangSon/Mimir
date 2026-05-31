from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Iterable

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
        params = {
            "crtfc_key": self._api_key,
            "bgn_de": since.strftime("%Y%m%d"),
            "end_de": ctx.now.strftime("%Y%m%d"),
            "page_no": "1",
            "page_count": str(PAGE_COUNT),
        }
        data = self.get(LIST_URL, params=params).json()
        status = data.get("status")
        if status not in ("000", "013"):  # 013 = no data for the query
            raise FetchError(f"DART error status={status}: {data.get('message')}")
        for item in data.get("list", []):
            code = item.get("stock_code")
            if code not in wanted:
                continue
            rcept_no = item["rcept_no"]
            ts = datetime.strptime(item["rcept_dt"], "%Y%m%d").replace(tzinfo=UTC)
            yield RawRecord(
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
