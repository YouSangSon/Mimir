from __future__ import annotations

from pydantic import BaseModel

from mimir.analysis.signals.base import DIRECTION_SIGN, SignalDirection, SignalResult

DIRECTION_EPS = 0.02


class InsightScore(BaseModel):
    direction: SignalDirection
    stars: int  # 1..5
    confidence: float
    reasons: list[str]


def score(results: list[SignalResult]) -> InsightScore:
    if not results:
        return InsightScore(direction=SignalDirection.NEUTRAL, stars=1, confidence=0.0, reasons=[])

    total_weight = sum(r.weight for r in results) or 1.0
    net = (
        sum(DIRECTION_SIGN[r.direction] * r.strength * r.confidence * r.weight for r in results)
        / total_weight
    )
    attention = sum(r.strength * r.confidence * r.weight for r in results) / total_weight
    confidence = sum(r.confidence * r.weight for r in results) / total_weight

    if net > DIRECTION_EPS:
        direction = SignalDirection.BULLISH
    elif net < -DIRECTION_EPS:
        direction = SignalDirection.BEARISH
    else:
        direction = SignalDirection.NEUTRAL

    magnitude = max(abs(net), attention)
    stars = max(1, min(5, round(1 + 4 * magnitude)))
    reasons = [f"[{r.signal}] {r.reason}" for r in results]
    return InsightScore(
        direction=direction, stars=stars, confidence=round(confidence, 3), reasons=reasons
    )
