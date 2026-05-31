from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any

import requests
from pydantic import BaseModel

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

BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"
NO_DATA_CODE = "INFO-200"
PAGE_SIZE = 100
MAX_PAGES = 100  # safety cap on pagination


class EcosSeries(BaseModel):
    stat_code: str
    cycle: str  # D | M | Q | A
    item_code: str


# A small default macro set (Bank of Korea base rate); override via constructor.
DEFAULT_SERIES = [EcosSeries(stat_code="722Y001", cycle="M", item_code="0101000")]


def _fmt(d: date, cycle: str) -> str:
    if cycle == "D":
        return d.strftime("%Y%m%d")
    if cycle == "M":
        return d.strftime("%Y%m")
    if cycle == "Q":
        return f"{d.year}Q{(d.month - 1) // 3 + 1}"
    return d.strftime("%Y")  # A / Y


def _parse_time(t: str) -> datetime:
    if "Q" in t:
        year, q = t.split("Q")
        return datetime(int(year), (int(q) - 1) * 3 + 1, 1, tzinfo=UTC)
    if len(t) == 8:
        return datetime.strptime(t, "%Y%m%d").replace(tzinfo=UTC)
    if len(t) == 6:
        return datetime.strptime(t, "%Y%m").replace(tzinfo=UTC)
    return datetime(int(t), 1, 1, tzinfo=UTC)


class EcosSource(BaseSource):
    meta = SourceMeta(
        id="ecos",
        market=Market.KR,
        dataset=Dataset.MACRO,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=2.0),
        requires_secret="ECOS_API_KEY",
    )

    def __init__(
        self,
        *,
        api_key: str,
        series: list[EcosSeries] | None = None,
        session: requests.Session | None = None,
        throttle: Throttle | None = None,
    ) -> None:
        super().__init__(session=session, throttle=throttle)
        self._api_key = api_key
        self._series = series or list(DEFAULT_SERIES)

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        start = ctx.backfill_since or date(ctx.now.year - 1, 1, 1)
        end = ctx.now.date()
        for s in self._series:
            yield from self._fetch_series(s, start, end)

    def _fetch_series(self, s: EcosSeries, start: date, end: date) -> Iterable[RawRecord]:
        page_start = 1
        for _ in range(MAX_PAGES):
            page_end = page_start + PAGE_SIZE - 1
            url = "/".join(
                [
                    BASE_URL,
                    self._api_key,
                    "json",
                    "kr",
                    str(page_start),
                    str(page_end),
                    s.stat_code,
                    s.cycle,
                    _fmt(start, s.cycle),
                    _fmt(end, s.cycle),
                    s.item_code,
                ]
            )
            try:
                resp = self.get(url)
            except FetchError as exc:
                # ECOS embeds the key in the URL path, which http_get includes in
                # its error message; redact it so the secret never reaches logs/
                # the manifest/status.html/the committed repo.
                raise FetchError(str(exc).replace(self._api_key, "***")) from None
            data = resp.json()
            if "RESULT" in data:
                code = data["RESULT"].get("CODE", "")
                if code.startswith(NO_DATA_CODE):
                    return
                raise FetchError(f"ECOS error {code}: {data['RESULT'].get('MESSAGE')}")
            search = data.get("StatisticSearch", {})
            rows = search.get("row", [])
            for row in rows:
                rec = self._row_to_record(s, row)
                if rec is not None:
                    yield rec
            total = int(search.get("list_total_count", 0) or 0)
            if not rows or page_end >= total:
                return
            page_start = page_end + 1

    @staticmethod
    def _row_to_record(s: EcosSeries, row: dict[str, Any]) -> RawRecord | None:
        value = row.get("DATA_VALUE")
        t = row.get("TIME")
        if not t or value is None or value == "":
            return None
        return RawRecord(
            symbol=f"{s.stat_code}.{s.item_code}",
            ts=_parse_time(t),
            idempotency_key=f"ecos:{s.stat_code}:{s.item_code}:{t}",
            payload={
                "stat_code": s.stat_code,
                "item_code": s.item_code,
                "item_name": row.get("ITEM_NAME1"),
                "value": float(value),
                "unit": row.get("UNIT_NAME"),
                "time": t,
            },
        )
