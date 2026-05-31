from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

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
    payload: dict[str, Any]
