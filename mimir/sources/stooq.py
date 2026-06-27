from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from datetime import UTC, datetime

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

BASE_URL = "https://stooq.com/q/d/l/"
CSV_HEADER = "Date,"


class StooqSource(BaseSource):
    # Stooq's per-symbol CSV download now requires a free apikey (obtained via a
    # one-time captcha at https://stooq.com/q/d/?s=<sym>&get_apikey). Without a
    # key the source is skipped by the builder, like other key-gated sources.
    meta = SourceMeta(
        id="stooq",
        market=Market.US,
        dataset=Dataset.PRICES,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1.0),
        requires_secret="STOOQ_API_KEY",
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        session: requests.Session | None = None,
        throttle: Throttle | None = None,
    ) -> None:
        super().__init__(session=session, throttle=throttle)
        self._api_key = api_key

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        for symbol in ctx.watchlist.get("us", []):
            params: dict[str, str] = {"s": f"{symbol.lower()}.us", "i": "d"}
            if self._api_key:
                params["apikey"] = self._api_key
            if ctx.backfill_since is not None:
                params["d1"] = ctx.backfill_since.strftime("%Y%m%d")
                params["d2"] = ctx.now.strftime("%Y%m%d")
            resp = self.get(BASE_URL, params=params)
            body = resp.text
            if not body.lstrip().startswith(CSV_HEADER):
                # Not CSV -> apikey missing/invalid or upstream message. Surface it
                # as a failure instead of silently yielding zero rows.
                raise FetchError(f"stooq: unexpected non-CSV response: {body[:80]!r}")
            yield from self._parse(symbol, body)

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
    if value is None or value in ("", "N/D"):
        return None
    return float(value)
