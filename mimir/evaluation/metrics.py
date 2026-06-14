from __future__ import annotations

from datetime import date
from typing import NamedTuple

from mimir.analysis.signals.base import DIRECTION_SIGN, SignalDirection
from mimir.core.source import Market
from mimir.evaluation.schema import BucketStat, HorizonEval
from mimir.historical.analog import DEFAULT_HORIZONS, forward_returns
from mimir.historical.series import Bar

MIN_EVAL_N = 5  # drop a horizon with fewer directional observations (S4 MIN_HORIZON_N mirror)
ROUND_PLACES = 6


class Obs(NamedTuple):
    """One scored observation: a price series, its entry index, and the
    direction to score that entry with (the signal's/insight's own direction)."""

    series: list[Bar]
    anchor: int
    direction: SignalDirection


def anchor_index(series: list[Bar], as_of: date) -> int | None:
    """Index of the first bar STRICTLY AFTER as_of (the evaluation entry point).

    The insight's information set ends at as_of's close, so the earliest price we
    may score against is the next available bar. Returns None when no such bar
    exists yet (too-recent insight) -> that insight contributes nothing.
    """
    for i, bar in enumerate(series):
        if bar.day > as_of:
            return i
    return None


def _horizon_eval(horizon: int, obs: list[Obs], min_n: int) -> HorizonEval | None:
    """Apply the direction-aware metrics for one horizon, or None if gated.

    `n` counts only directional observations that have a forward bar at this
    horizon; neutral observations are excluded from `n` (and thus from hit-rate
    and the mean) and counted in `neutral_n`. Computing `n` before any ratio
    avoids a 0/0 on all-neutral buckets.
    """
    edges: list[float] = []  # signed returns e for directional obs with a forward bar
    neutral_n = 0
    for series, anchor, direction in obs:
        rets = forward_returns(series, [anchor], horizon)
        if not rets:  # no forward bar at this horizon (S4 boundary drop)
            continue
        sign = DIRECTION_SIGN[direction]
        if sign == 0.0:  # neutral: excluded from hit-rate denominator
            neutral_n += 1
            continue
        edges.append(sign * rets[0])

    n = len(edges)
    if n < min_n:
        return None
    hit_rate = sum(1 for e in edges if e > 0) / n
    mean_fwd_return = sum(edges) / n
    return HorizonEval(
        horizon=horizon,
        n=n,
        hit_rate=round(hit_rate, ROUND_PLACES),
        mean_fwd_return=round(mean_fwd_return, ROUND_PLACES),
        neutral_n=neutral_n,
    )


def evaluate_bucket(
    key: tuple[str, str, Market],
    obs: list[Obs],
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    min_n: int = MIN_EVAL_N,
) -> BucketStat | None:
    """Build a BucketStat for one (dimension, key, market) bucket, or None when
    every horizon is gated out (fully insufficient sample)."""
    dimension, bucket_key, market = key
    evals = [e for e in (_horizon_eval(h, obs, min_n) for h in horizons) if e is not None]
    if not evals:
        return None
    return BucketStat(dimension=dimension, key=bucket_key, market=market, horizons=evals)
