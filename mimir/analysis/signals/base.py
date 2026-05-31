from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel

from mimir.analysis.reader import DataReader
from mimir.core.source import Market


class SignalDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


DIRECTION_SIGN: dict[SignalDirection, float] = {
    SignalDirection.BULLISH: 1.0,
    SignalDirection.BEARISH: -1.0,
    SignalDirection.NEUTRAL: 0.0,
}


class SignalResult(BaseModel):
    signal: str
    direction: SignalDirection
    strength: float  # 0..1 magnitude of the signal
    confidence: float  # 0..1 trust in the signal
    reason: str
    weight: float = 1.0


class Signal(Protocol):
    id: str

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None: ...
