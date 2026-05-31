from __future__ import annotations

from mimir.historical.series import Bar

SHARP_DROP_THRESHOLD = 0.05
VOLUME_SPIKE_RATIO = 2.0
VOLUME_SPIKE_WINDOW = 20


def detect_sharp_drops(series: list[Bar], threshold: float = SHARP_DROP_THRESHOLD) -> list[int]:
    """Indices i where the day's return (close[i]/close[i-1] - 1) <= -threshold."""
    idxs: list[int] = []
    for i in range(1, len(series)):
        prev = series[i - 1].close
        if prev and (series[i].close - prev) / prev <= -threshold:
            idxs.append(i)
    return idxs


def detect_volume_spikes(
    series: list[Bar],
    ratio: float = VOLUME_SPIKE_RATIO,
    window: int = VOLUME_SPIKE_WINDOW,
) -> list[int]:
    """Indices i where volume[i] > ratio * mean(volume over the prior `window` bars)."""
    idxs: list[int] = []
    for i in range(1, len(series)):
        vol = series[i].volume
        if vol is None:
            continue
        prior = [b.volume for b in series[max(0, i - window) : i] if b.volume is not None]
        if not prior:
            continue
        avg = sum(prior) / len(prior)
        if avg and vol > ratio * avg:
            idxs.append(i)
    return idxs
