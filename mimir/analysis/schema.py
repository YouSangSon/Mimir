from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel

from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.source import Dataset, Market
from mimir.storage.schema import Record

DISCLAIMER = "For information only. Not financial advice."
ANALYSIS_SOURCE = "mimir_analysis"


class Insight(BaseModel):
    symbol: str
    market: Market
    as_of: date
    direction: SignalDirection
    stars: int
    confidence: float
    attention: float = 0.0
    signals: list[SignalResult]
    reasons: list[str]
    disclaimer: str = DISCLAIMER


def to_record(insight: Insight, captured_at: datetime) -> Record:
    return Record(
        source=ANALYSIS_SOURCE,
        dataset=Dataset.INSIGHTS,
        market=insight.market,
        symbol=insight.symbol,
        ts=datetime(insight.as_of.year, insight.as_of.month, insight.as_of.day, tzinfo=UTC),
        captured_at=captured_at,
        idempotency_key=f"insight:{insight.symbol}:{insight.as_of.isoformat()}",
        payload=insight.model_dump(mode="json"),
    )
