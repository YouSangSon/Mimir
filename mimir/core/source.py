from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class Cadence(StrEnum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class LegalStatus(StrEnum):
    OFFICIAL = "official"
    GRAY = "gray"


class Market(StrEnum):
    US = "US"
    KR = "KR"
    GLOBAL = "GLOBAL"


class Dataset(StrEnum):
    PRICES = "prices"
    FILINGS = "filings"
    MACRO = "macro"
    NEWS = "news"
    INSIGHTS = "insights"
    HISTORICAL = "historical"


class RateLimit(BaseModel):
    # None means unknown / unpublished -> caller throttles conservatively.
    max_per_second: float | None = None


class SourceMeta(BaseModel):
    id: str
    market: Market
    dataset: Dataset
    cadence: Cadence
    legal_status: LegalStatus
    rate_limit: RateLimit
    requires_secret: str | None = None


class FetchContext(BaseModel):
    watchlist: dict[str, list[str]]
    now: datetime
    backfill_since: date | None = None


class RawRecord(BaseModel):
    symbol: str | None
    ts: datetime
    idempotency_key: str
    payload: dict[str, Any]


@runtime_checkable
class Source(Protocol):
    meta: SourceMeta

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]: ...
