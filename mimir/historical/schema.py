from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from mimir.core.source import Dataset, Market
from mimir.historical.analog import HorizonStat

if TYPE_CHECKING:
    from mimir.storage.schema import Record

DISCLAIMER = "Past performance does not guarantee future results. Not financial advice."
HISTORICAL_SOURCE = "mimir_historical"


class HistoricalInsight(BaseModel):
    # extra="forbid": typed payload (see core/payloads.py); drift fails at the boundary.
    model_config = ConfigDict(extra="forbid")

    symbol: str
    market: Market
    as_of: date
    event_type: str
    occurrences: int
    triggered_today: bool
    horizons: list[HorizonStat]
    examples: list[str]
    disclaimer: str = DISCLAIMER


def to_record(insight: HistoricalInsight, captured_at: datetime) -> Record:
    # Function-local import breaks the phase-4 cycle (see analysis/schema.py).
    from mimir.storage.schema import Record

    return Record(
        source=HISTORICAL_SOURCE,
        dataset=Dataset.HISTORICAL,
        market=insight.market,
        symbol=insight.symbol,
        ts=datetime(insight.as_of.year, insight.as_of.month, insight.as_of.day, tzinfo=UTC),
        captured_at=captured_at,
        idempotency_key=(
            f"historical:{insight.symbol}:{insight.event_type}:{insight.as_of.isoformat()}"
        ),
        payload=insight,  # already a typed payload; before-validator no-ops on a model
    )
