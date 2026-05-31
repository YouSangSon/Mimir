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

OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
# A small default macro set; override via constructor.
DEFAULT_SERIES = ["DGS10", "FEDFUNDS", "CPIAUCSL"]


class FredSource(BaseSource):
    meta = SourceMeta(
        id="fred",
        market=Market.US,
        dataset=Dataset.MACRO,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=2.0),
        requires_secret="FRED_API_KEY",
    )

    def __init__(
        self,
        *,
        api_key: str,
        series: list[str] | None = None,
        session: requests.Session | None = None,
        throttle: Throttle | None = None,
    ) -> None:
        super().__init__(session=session, throttle=throttle)
        self._api_key = api_key
        self._series = series or list(DEFAULT_SERIES)

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        for series_id in self._series:
            params = {
                "series_id": series_id,
                "api_key": self._api_key,
                "file_type": "json",
            }
            if ctx.backfill_since is not None:
                params["observation_start"] = ctx.backfill_since.isoformat()
            data = self.get(OBSERVATIONS_URL, params=params).json()
            for obs in data.get("observations", []):
                value = obs.get("value")
                day = obs.get("date")
                if not day or value in (None, "", "."):  # FRED missing marker is "."
                    continue
                ts = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
                yield RawRecord(
                    symbol=series_id,
                    ts=ts,
                    idempotency_key=f"fred:{series_id}:{day}",
                    payload={"series_id": series_id, "value": float(value), "period": day},
                )
