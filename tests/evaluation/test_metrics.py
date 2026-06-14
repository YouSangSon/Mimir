from datetime import date

from mimir.analysis.signals.base import SignalDirection
from mimir.core.source import Market
from mimir.evaluation.metrics import MIN_EVAL_N, Obs, anchor_index, evaluate_bucket
from mimir.historical.analog import forward_returns
from mimir.historical.series import Bar


def _series(closes: list[float], start_day: int = 1) -> list[Bar]:
    return [Bar(date(2026, 5, start_day + i), c, None) for i, c in enumerate(closes)]


# --- anchor_index (lookahead barrier) ------------------------------------


def test_anchor_index_returns_first_bar_strictly_after_as_of():
    # bars on 5/1..5/5; as_of = 5/3 -> first bar STRICTLY after is 5/4 = idx 3
    series = _series([10, 11, 12, 13, 14])
    assert anchor_index(series, date(2026, 5, 3)) == 3


def test_anchor_index_excludes_same_day_close():
    # as_of equals a bar's day -> that same-day close is NOT a valid entry
    series = _series([10, 11, 12])  # 5/1, 5/2, 5/3
    assert anchor_index(series, date(2026, 5, 2)) == 2  # 5/3, not 5/2


def test_anchor_index_none_when_no_future_bar():
    series = _series([10, 11, 12])  # last bar 5/3
    assert anchor_index(series, date(2026, 5, 3)) is None
    assert anchor_index(series, date(2026, 5, 10)) is None


def test_anchor_index_none_on_empty_series():
    assert anchor_index([], date(2026, 5, 3)) is None


# --- direction-aware hit-rate --------------------------------------------


def _bucket(obs: list[Obs]):
    return evaluate_bucket(("per_direction", "x", Market.US), obs, horizons=(1,), min_n=1)


def test_bullish_up_is_hit():
    # close rises 100 -> 110 over 1 bar; bullish -> e = +0.10 > 0 -> hit
    s = _series([100, 110])
    stat = _bucket([Obs(s, 0, SignalDirection.BULLISH)])
    assert stat is not None
    assert stat.horizons[0].hit_rate == 1.0


def test_bullish_down_is_miss():
    s = _series([100, 90])
    stat = _bucket([Obs(s, 0, SignalDirection.BULLISH)])
    assert stat is not None
    assert stat.horizons[0].hit_rate == 0.0


def test_bearish_down_is_hit():
    # THE load-bearing case: bearish + price down -> e = (-1)*(-0.10) = +0.10 > 0 -> HIT
    s = _series([100, 90])
    stat = _bucket([Obs(s, 0, SignalDirection.BEARISH)])
    assert stat is not None
    assert stat.horizons[0].hit_rate == 1.0


def test_bearish_up_is_miss():
    s = _series([100, 110])
    stat = _bucket([Obs(s, 0, SignalDirection.BEARISH)])
    assert stat is not None
    assert stat.horizons[0].hit_rate == 0.0


# --- neutral handling -----------------------------------------------------


def test_neutral_excluded_from_hit_rate_denominator():
    # 2 bullish (1 up=hit, 1 down=miss) + 1 neutral -> n=2, hit_rate=0.5, neutral_n=1
    up = _series([100, 110])
    down = _series([100, 90])
    flat = _series([100, 105])  # direction neutral -> excluded regardless of move
    stat = _bucket(
        [
            Obs(up, 0, SignalDirection.BULLISH),
            Obs(down, 0, SignalDirection.BULLISH),
            Obs(flat, 0, SignalDirection.NEUTRAL),
        ]
    )
    assert stat is not None
    h = stat.horizons[0]
    assert h.n == 2
    assert h.hit_rate == 0.5
    assert h.neutral_n == 1


# --- mean fwd return (signed edge) ---------------------------------------


def test_mean_fwd_return_pure_bullish_equals_raw_mean():
    # +0.10 and -0.10 -> raw mean 0.0; bullish sign +1 -> edge mean 0.0
    up = _series([100, 110])
    down = _series([100, 90])
    stat = _bucket([Obs(up, 0, SignalDirection.BULLISH), Obs(down, 0, SignalDirection.BULLISH)])
    assert stat is not None
    assert stat.horizons[0].mean_fwd_return == 0.0


def test_mean_fwd_return_mixed_bucket_uses_signed_edge():
    # bullish +0.10 -> e=+0.10 ; bearish on a -0.10 move -> e=+0.10 ; mean edge = +0.10
    up = _series([100, 110])
    down = _series([100, 90])
    stat = _bucket([Obs(up, 0, SignalDirection.BULLISH), Obs(down, 0, SignalDirection.BEARISH)])
    assert stat is not None
    assert stat.horizons[0].mean_fwd_return == 0.1


# --- reuse of S4 forward_returns -----------------------------------------


def test_forward_returns_reuse_matches_and_drops_boundary():
    # known series; anchor=0, horizon=2 -> uses forward_returns, including i+h>=len drop
    s = _series([100, 101, 110, 120])
    # horizon 2 from idx 0 -> (110-100)/100 = 0.10
    raw = forward_returns(s, [0], 2)
    assert raw == [0.10]
    stat = evaluate_bucket(
        ("per_direction", "x", Market.US),
        [Obs(s, 0, SignalDirection.BULLISH)],
        horizons=(2,),
        min_n=1,
    )
    assert stat is not None
    assert stat.horizons[0].mean_fwd_return == raw[0]


def test_boundary_observation_dropped_when_no_forward_bar():
    # anchor=2 (third bar), horizon=5 -> 2+5 >= len -> no forward bar -> obs dropped
    s = _series([100, 101, 110, 120])
    assert forward_returns(s, [2], 5) == []  # S4 boundary drop
    stat = evaluate_bucket(
        ("per_direction", "x", Market.US),
        [Obs(s, 2, SignalDirection.BULLISH)],
        horizons=(5,),
        min_n=1,
    )
    assert stat is None  # nothing survived -> bucket gated out


# --- sample gating --------------------------------------------------------


def test_horizon_dropped_below_min_eval_n():
    # 3 directional obs at horizon 1, MIN_EVAL_N=5 -> horizon dropped -> bucket gated
    s = _series([100, 110])
    obs = [Obs(s, 0, SignalDirection.BULLISH)] * (MIN_EVAL_N - 1)
    stat = evaluate_bucket(("per_direction", "x", Market.US), obs, horizons=(1,))
    assert stat is None


def test_horizon_kept_at_min_eval_n():
    s = _series([100, 110])
    obs = [Obs(s, 0, SignalDirection.BULLISH)] * MIN_EVAL_N
    stat = evaluate_bucket(("per_direction", "x", Market.US), obs, horizons=(1,))
    assert stat is not None
    assert stat.horizons[0].n == MIN_EVAL_N


def test_all_neutral_bucket_gated_out():
    # all-neutral -> directional n=0 at every horizon -> no division by zero, bucket gated
    flat = _series([100, 105])
    obs = [Obs(flat, 0, SignalDirection.NEUTRAL)] * 10
    stat = evaluate_bucket(("per_star", "3", Market.US), obs, horizons=(1,))
    assert stat is None
