from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Iterable

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
from mimir.sources.base import BaseSource

BASE_URL = "https://stooq.com/q/d/l/"


class StooqSource(BaseSource):
    meta = SourceMeta(
        id="stooq",
        market=Market.US,
        dataset=Dataset.PRICES,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1.0),
    )

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        for symbol in ctx.watchlist.get("us", []):
            params: dict[str, str] = {"s": f"{symbol.lower()}.us", "i": "d"}
            if ctx.backfill_since is not None:
                params["d1"] = ctx.backfill_since.strftime("%Y%m%d")
                params["d2"] = ctx.now.strftime("%Y%m%d")
            resp = self.get(BASE_URL, params=params)
            yield from self._parse(symbol, resp.text)

    @staticmethod
    def _parse(symbol: str, body: str) -> Iterable[RawRecord]:
        reader = csv.DictReader(io.StringIO(body))
        for row in reader:
            day = row.get("Date", "")
            close = row.get("Close", "")
            if not day or close in ("", "N/D"):
                continue
            ts = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
            yield RawRecord(
                symbol=symbol,
                ts=ts,
                idempotency_key=f"stooq:{symbol}:{day}",
                payload={
                    "open": _f(row.get("Open")),
                    "high": _f(row.get("High")),
                    "low": _f(row.get("Low")),
                    "close": _f(close),
                    "volume": _f(row.get("Volume")),
                    "currency": "USD",
                    "interval": "1d",
                },
            )


def _f(value: str | None) -> float | None:
    if value in (None, "", "N/D"):
        return None
    return float(value)  # type: ignore[arg-type]
