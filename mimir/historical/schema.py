from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel

from mimir.core.source import Dataset, Market
from mimir.historical.analog import HorizonStat
from mimir.storage.schema import Record

DISCLAIMER = "Past performance does not guarantee future results. Not financial advice."
HISTORICAL_SOURCE = "mimir_historical"


class HistoricalInsight(BaseModel):
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
        payload=insight.model_dump(mode="json"),
    )
