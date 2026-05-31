from mimir.analysis.scorer import score
from mimir.analysis.signals.base import SignalDirection, SignalResult


def _r(direction, strength, confidence, weight=1.0, signal="s"):
    return SignalResult(
        signal=signal,
        direction=direction,
        strength=strength,
        confidence=confidence,
        reason="r",
        weight=weight,
    )


def test_empty_results_score_is_neutral_one_star():
    s = score([])
    assert s.direction is SignalDirection.NEUTRAL
    assert s.stars == 1


def test_strong_bullish_signal_scores_bullish_high_stars():
    s = score([_r(SignalDirection.BULLISH, strength=1.0, confidence=0.9, weight=1.0)])
    assert s.direction is SignalDirection.BULLISH
    assert s.stars >= 4


def test_opposing_signals_net_toward_neutral():
    s = score(
        [
            _r(SignalDirection.BULLISH, 1.0, 0.9, 1.0),
            _r(SignalDirection.BEARISH, 1.0, 0.9, 1.0),
        ]
    )
    assert s.direction is SignalDirection.NEUTRAL


def test_neutral_attention_signal_raises_stars_without_direction():
    s = score([_r(SignalDirection.NEUTRAL, strength=1.0, confidence=1.0, weight=1.0)])
    assert s.direction is SignalDirection.NEUTRAL
    assert s.stars >= 4  # high attention even though direction is neutral


def test_reasons_are_prefixed_with_signal():
    s = score([_r(SignalDirection.BULLISH, 0.5, 0.5, signal="price_momentum")])
    assert s.reasons == ["[price_momentum] r"]
