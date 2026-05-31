from __future__ import annotations

from pydantic import BaseModel

from mimir.historical.series import Bar

DEFAULT_HORIZONS = (1, 5, 20)


class HorizonStat(BaseModel):
    horizon: int
    n: int
    median_return: float
    pct_positive: float


def forward_returns(series: list[Bar], idxs: list[int], horizon: int) -> list[float]:
    """Return (close[i+h]/close[i] - 1) for each event i that has `horizon` bars ahead."""
    out: list[float] = []
    for i in idxs:
        j = i + horizon
        if j < len(series) and series[i].close:
            out.append((series[j].close - series[i].close) / series[i].close)
    return out


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def summarize(
    series: list[Bar],
    idxs: list[int],
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    min_n: int = 1,
) -> list[HorizonStat]:
    stats: list[HorizonStat] = []
    for h in horizons:
        rets = forward_returns(series, idxs, h)
        # Drop horizons with too few forward observations: a "median over 20d"
        # computed from n=1 reads as robust but isn't. n is also exposed below.
        if len(rets) < min_n:
            continue
        pct_positive = sum(1 for r in rets if r > 0) / len(rets)
        stats.append(
            HorizonStat(
                horizon=h,
                n=len(rets),
                median_return=round(_median(rets), 4),
                pct_positive=round(pct_positive, 3),
            )
        )
    return stats
