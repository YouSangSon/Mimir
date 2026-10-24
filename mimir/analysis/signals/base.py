from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, SerializerFunctionWrapHandler, model_serializer

from mimir.core.provenance import SourceProvenance
from mimir.core.source import Market

if TYPE_CHECKING:
    # Annotation-only (the Signal Protocol's reader param). A module-top import
    # would create a cycle: core.payloads -> analysis.schema -> signals.base ->
    # storage.reader -> jsonl_store -> storage.schema -> core.payloads.
    from mimir.storage.reader import DataReader


class SignalDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


DIRECTION_SIGN: dict[SignalDirection, float] = {
    SignalDirection.BULLISH: 1.0,
    SignalDirection.BEARISH: -1.0,
    SignalDirection.NEUTRAL: 0.0,
}
SOURCE_AWARE_SIGNALS = {"macro_regime", "news_volume", "llm_sentiment"}


class SignalResult(BaseModel):
    # Stored nested in the INSIGHTS payload (Insight.signals[]) and re-validated on
    # every read, so it carries the same boundary contract as the A4 typed payloads:
    # reject drift keys, and keep weight a non-negative multiplier (a negative weight
    # would flip the signed directional pull in scorer.score()).
    model_config = ConfigDict(extra="forbid")

    signal: str
    direction: SignalDirection
    strength: float = Field(ge=0.0, le=1.0)  # magnitude of the signal
    confidence: float = Field(ge=0.0, le=1.0)  # trust in the signal
    reason: str
    weight: float = Field(default=1.0, ge=0.0)
    attributions: list[SourceProvenance] = Field(default_factory=list)

    @property
    def source_evidence_ready(self) -> bool:
        return self.signal not in SOURCE_AWARE_SIGNALS or (
            "attributions" in self.model_fields_set
        )

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        # Missing legacy metadata differs from a new, explicit empty source list.
        if "attributions" not in self.model_fields_set:
            data.pop("attributions", None)
        return data


class Signal(Protocol):
    id: str

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None: ...
