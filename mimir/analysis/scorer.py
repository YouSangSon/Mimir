from __future__ import annotations

from pydantic import BaseModel

from mimir.analysis.signals.base import DIRECTION_SIGN, SignalDirection, SignalResult

DIRECTION_EPS = 0.02


class InsightScore(BaseModel):
    direction: SignalDirection
    stars: int  # 1..5 — directional CONVICTION (not mere activity)
    confidence: float
    attention: float  # 0..1 — how much is happening, regardless of direction
    reasons: list[str]


def score(results: list[SignalResult]) -> InsightScore:
    if not results:
        return InsightScore(
            direction=SignalDirection.NEUTRAL, stars=1, confidence=0.0, attention=0.0, reasons=[]
        )

    total_weight = sum(r.weight for r in results) or 1.0
    # net is the signed, weighted directional pull in [-1, 1].
    net = (
        sum(DIRECTION_SIGN[r.direction] * r.strength * r.confidence * r.weight for r in results)
        / total_weight
    )
    # attention is the unsigned weighted activity (neutral signals contribute here only).
    attention = sum(r.strength * r.confidence * r.weight for r in results) / total_weight
    confidence = sum(r.confidence * r.weight for r in results) / total_weight

    if net > DIRECTION_EPS:
        direction = SignalDirection.BULLISH
    elif net < -DIRECTION_EPS:
        direction = SignalDirection.BEARISH
    else:
        direction = SignalDirection.NEUTRAL

    # Stars reflect directional conviction |net|, so a flurry of direction-less
    # activity (filings/news) cannot masquerade as a high-conviction call.
    stars = max(1, min(5, round(1 + 4 * abs(net))))
    reasons = [f"[{r.signal}] {r.reason}" for r in results]
    return InsightScore(
        direction=direction,
        stars=stars,
        confidence=round(confidence, 3),
        attention=round(attention, 3),
        reasons=reasons,
    )
