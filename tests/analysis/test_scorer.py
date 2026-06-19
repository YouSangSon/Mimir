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


def test_neutral_activity_is_low_stars_but_high_attention():
    # A flurry of direction-less activity must NOT masquerade as a high-conviction call.
    s = score([_r(SignalDirection.NEUTRAL, strength=1.0, confidence=1.0, weight=1.0)])
    assert s.direction is SignalDirection.NEUTRAL
    assert s.stars <= 2  # no directional conviction -> low stars
    assert s.attention >= 0.9  # but the activity is surfaced separately


def test_neutral_signals_do_not_dilute_directional_conviction():
    # Stars reflect directional conviction, not signal count: adding always-neutral
    # activity signals (e.g. news_volume) must not lower the stars of a real
    # directional call — but the activity must still raise attention.
    bullish_only = score([_r(SignalDirection.BULLISH, 1.0, 0.9, weight=1.0)])
    with_neutral = score(
        [
            _r(SignalDirection.BULLISH, 1.0, 0.9, weight=1.0),
            _r(SignalDirection.NEUTRAL, 1.0, 1.0, weight=0.5),
            _r(SignalDirection.NEUTRAL, 1.0, 1.0, weight=0.8),
        ]
    )
    assert with_neutral.direction is SignalDirection.BULLISH
    assert with_neutral.stars == bullish_only.stars
    assert with_neutral.attention >= bullish_only.attention


def test_reasons_are_prefixed_with_signal():
    s = score([_r(SignalDirection.BULLISH, 0.5, 0.5, signal="price_momentum")])
    assert s.reasons == ["[price_momentum] r"]
