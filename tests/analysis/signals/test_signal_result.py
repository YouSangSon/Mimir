import pytest
from pydantic import ValidationError

from mimir.analysis.signals.base import SignalDirection, SignalResult


def _kwargs(**over: object) -> dict[str, object]:
    base: dict[str, object] = dict(
        signal="s",
        direction=SignalDirection.BULLISH,
        strength=0.5,
        confidence=0.8,
        reason="r",
    )
    base.update(over)
    return base


def test_signal_result_rejects_unknown_field():
    # SignalResult is nested in the stored Insight payload and re-validated on every
    # read; an upstream drift key must fail loud, matching the A4 typed-payload
    # contract (all stored payloads use extra="forbid").
    with pytest.raises(ValidationError):
        SignalResult(**_kwargs(bogus="x"))


def test_signal_result_rejects_negative_weight():
    # A negative weight would flip the signed directional pull in scorer.score()
    # (net += DIRECTION_SIGN * strength * confidence * weight), corrupting direction.
    with pytest.raises(ValidationError):
        SignalResult(**_kwargs(weight=-0.1))


def test_signal_result_accepts_valid_weight_bounds():
    # weight is a multiplier, not a [0,1] score: 0 and >1 are valid; only negative is not.
    assert SignalResult(**_kwargs(weight=0.0)).weight == 0.0
    assert SignalResult(**_kwargs(weight=2.0)).weight == 2.0
