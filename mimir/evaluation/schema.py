from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, SerializerFunctionWrapHandler, model_serializer

from mimir.analysis.signals.base import SOURCE_AWARE_SIGNALS
from mimir.core.provenance import SourceProvenance
from mimir.core.source import Dataset, Market

if TYPE_CHECKING:
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
    # extra="forbid": typed payload (see core/payloads.py); drift fails at the boundary.
    model_config = ConfigDict(extra="forbid")

    dimension: str  # "per_signal" | "per_direction" | "per_star"
    key: str  # e.g. "momentum" | "bullish" | "4"
    market: Market
    horizons: list[HorizonEval]
    attributions: list[SourceProvenance] = Field(default_factory=list)

    @property
    def source_evidence_ready(self) -> bool:
        # Legacy aggregates cannot identify inputs; unrelated per-signal rows can.
        return "attributions" in self.model_fields_set or (
            self.dimension == "per_signal" and self.key not in SOURCE_AWARE_SIGNALS
        )

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if "attributions" not in self.model_fields_set:
            data.pop("attributions", None)
        return data


class EvaluationReport(BaseModel):
    as_of: date
    insights_evaluated: int  # total insights read (<= as_of)
    buckets: list[BucketStat]  # gated; may be [] on cold-start
    sufficient: bool  # False when every bucket was gated out
    disclaimer: str = DISCLAIMER


def to_record(stat: BucketStat, as_of: date, captured_at: datetime) -> Record:
    # Function-local import breaks the phase-4 cycle (see analysis/schema.py).
    from mimir.storage.schema import Record

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
        payload=stat,  # already a typed payload; before-validator no-ops on a model
    )
