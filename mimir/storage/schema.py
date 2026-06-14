from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_validator

from mimir.core.payloads import Payload, parse_payload
from mimir.core.source import Dataset, Market


class Record(BaseModel):
    schema_version: int = 1
    source: str
    dataset: Dataset
    market: Market
    symbol: str | None
    ts: datetime
    captured_at: datetime
    idempotency_key: str
    payload: Payload

    @model_validator(mode="before")
    @classmethod
    def _typed_payload(cls, data: Any) -> Any:
        """Parse a dict payload into its dataset-specific model before field
        validation. The discriminator is the envelope `dataset` (external
        dispatch — no tag key in the payload), so deserialization is
        deterministic rather than relying on union heuristics. Drift raises
        PayloadSchemaError. A payload that is already a model (re-validation) is
        left untouched."""
        if isinstance(data, dict) and isinstance(data.get("payload"), dict):
            dataset = Dataset(data["dataset"])
            return {**data, "payload": parse_payload(dataset, data["payload"])}
        return data
