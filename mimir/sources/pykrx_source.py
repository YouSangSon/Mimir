from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

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

# pykrx returns a pandas DataFrame; we only depend on .iterrows() and these columns.
OhlcvFn = Callable[[str, str, str], Any]
DEFAULT_BACKFILL_DAYS = 7
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF = 0.5


def _default_ohlcv_fn(fromdate: str, todate: str, ticker: str) -> Any:
    # Lazy import so the (heavy, optional) pykrx/pandas stack is only needed when used.
    from pykrx import stock

    return stock.get_market_ohlcv(fromdate, todate, ticker)


class PykrxSource:
    # GRAY: pykrx scrapes KRX/Naver (no official API). Throttled, internal-analysis
    # only; disable via sources.yaml `gray_enabled: false`.
    meta = SourceMeta(
        id="pykrx",
        market=Market.KR,
        dataset=Dataset.PRICES,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.GRAY,
        rate_limit=RateLimit(max_per_second=1.0),
    )

    def __init__(
        self,
        *,
        ohlcv_fn: OhlcvFn | None = None,
        throttle: Throttle | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff: float = DEFAULT_BACKOFF,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if backoff < 0:
            raise ValueError("backoff must be >= 0")
        self._ohlcv_fn = ohlcv_fn or _default_ohlcv_fn
        self._throttle = throttle or Throttle(self.meta.rate_limit.max_per_second)
        self._max_retries = max_retries
        self._backoff = backoff
        self._sleep = sleep

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        since = ctx.backfill_since or (ctx.now.date() - timedelta(days=DEFAULT_BACKFILL_DAYS))
        fromdate = since.strftime("%Y%m%d")
        todate = ctx.now.strftime("%Y%m%d")
        for code in ctx.watchlist.get("kr", []):
            df = self._fetch_ohlcv(fromdate, todate, code)
            yield from self._parse(code, df)

    def _fetch_ohlcv(self, fromdate: str, todate: str, code: str) -> Any:
        last_exc: Exception | None = None
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            self._throttle.wait()
            try:
                return self._ohlcv_fn(fromdate, todate, code)
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    self._sleep(self._backoff * (2**attempt))
        raise FetchError(
            f"pykrx OHLCV failed after {attempts} attempts for {code}: {last_exc}"
        ) from last_exc

    @staticmethod
    def _parse(code: str, df: Any) -> Iterable[RawRecord]:
        for idx, row in df.iterrows():
            day = idx.strftime("%Y-%m-%d")
            ts = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
            yield RawRecord(
                symbol=code,
                ts=ts,
                idempotency_key=f"pykrx:{code}:{day}",
                payload={
                    "open": float(row["시가"]),
                    "high": float(row["고가"]),
                    "low": float(row["저가"]),
                    "close": float(row["종가"]),
                    "volume": float(row["거래량"]),
                    "currency": "KRW",
                    "interval": "1d",
                },
            )
