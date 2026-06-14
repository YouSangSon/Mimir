from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.source import Dataset, Market

if TYPE_CHECKING:
    from mimir.storage.schema import Record

DISCLAIMER = "For information only. Not financial advice."
ANALYSIS_SOURCE = "mimir_analysis"


class Insight(BaseModel):
    # extra="forbid": this is a typed payload (see core/payloads.py). Upstream drift
    # in an insights payload must fail loudly at the boundary, not be silently dropped.
    model_config = ConfigDict(extra="forbid")

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
    # Function-local import breaks the phase-4 cycle: storage.schema imports
    # core.payloads (the Payload union), which imports this module for Insight.
    from mimir.storage.schema import Record

    return Record(
        source=ANALYSIS_SOURCE,
        dataset=Dataset.INSIGHTS,
        market=insight.market,
        symbol=insight.symbol,
        ts=datetime(insight.as_of.year, insight.as_of.month, insight.as_of.day, tzinfo=UTC),
        captured_at=captured_at,
        idempotency_key=f"insight:{insight.symbol}:{insight.as_of.isoformat()}",
        payload=insight,  # already a typed payload; before-validator no-ops on a model
    )
