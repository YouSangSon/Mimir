from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel

from mimir.core.source import Dataset, Market
from mimir.storage.schema import Record

DISCLAIMER = "Backtest hit-rate is descriptive, not predictive. Not financial advice."
EVALUATION_SOURCE = "mimir_evaluation"


class HorizonEval(BaseModel):
    horizon: int  # trading bars (e.g. 1/5/20)
    n: int  # directional observations with a forward bar at this horizon
    hit_rate: float  # |{ e > 0 }| / n
    mean_fwd_return: float  # mean of signed return e (directional edge)
    neutral_n: int  # observations excluded from hit-rate (sign == 0)


class BucketStat(BaseModel):
    dimension: str  # "per_signal" | "per_direction" | "per_star"
    key: str  # e.g. "momentum" | "bullish" | "4"
    market: Market
    horizons: list[HorizonEval]


class EvaluationReport(BaseModel):
    as_of: date
    insights_evaluated: int  # total insights read (<= as_of)
    buckets: list[BucketStat]  # gated; may be [] on cold-start
    sufficient: bool  # False when every bucket was gated out
    disclaimer: str = DISCLAIMER


def to_record(stat: BucketStat, as_of: date, captured_at: datetime) -> Record:
    return Record(
        source=EVALUATION_SOURCE,
        dataset=Dataset.EVALUATION,
        market=stat.market,
        symbol=None,
        ts=datetime(as_of.year, as_of.month, as_of.day, tzinfo=UTC),
        captured_at=captured_at,
        idempotency_key=(
            f"evaluation:{stat.dimension}:{stat.key}:{stat.market.value}:{as_of.isoformat()}"
        ),
        payload=stat.model_dump(mode="json"),
    )
