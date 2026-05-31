from datetime import date

from mimir.historical.analog import forward_returns, summarize
from mimir.historical.events import detect_sharp_drops, detect_volume_spikes
from mimir.historical.series import Bar


def _bars(closes, volumes=None):
    volumes = volumes or [1000] * len(closes)
    pairs = zip(closes, volumes, strict=True)
    return [Bar(date(2026, 5, i + 1), c, v) for i, (c, v) in enumerate(pairs)]


def test_detect_sharp_drops():
    # day-over-day: idx2 = -10%, idx3 = +5.6%, idx4 = -10%
    bars = _bars([100, 100, 90, 95, 85])
    assert detect_sharp_drops(bars, threshold=0.05) == [2, 4]


def test_detect_volume_spikes():
    bars = _bars([100] * 6, volumes=[100, 100, 100, 100, 100, 500])
    # idx5 volume 500 > 2 * mean(prior 100s)
    assert detect_volume_spikes(bars, ratio=2.0, window=20) == [5]


def test_forward_returns_excludes_out_of_range():
    bars = _bars([100, 90, 99, 90, 99])  # events at idx 1 and 3
    # horizon 1: idx1 -> (99-90)/90, idx3 -> (99-90)/90
    assert forward_returns(bars, [1, 3], horizon=1) == [round(9 / 90, 10)] * 2
    # horizon 4: idx1 -> idx5 out of range (len 5), idx3 -> out of range -> empty
    assert forward_returns(bars, [1, 3], horizon=4) == []


def test_summarize_reports_median_and_pct_positive():
    bars = _bars([100, 90, 99, 90, 99])
    stats = summarize(bars, [1, 3], horizons=(1,))
    assert len(stats) == 1
    s = stats[0]
    assert s.horizon == 1
    assert s.n == 2
    assert s.pct_positive == 1.0
    assert s.median_return > 0


def test_summarize_drops_horizon_below_min_n():
    bars = _bars([100, 90, 99, 90, 99])  # events at idx 1 and 3
    # h=1: n=2 (kept). h=3: idx1->idx4 exists, idx3->idx6 out of range => n=1 (dropped at min_n=2).
    stats = summarize(bars, [1, 3], horizons=(1, 3), min_n=2)
    assert {s.horizon for s in stats} == {1}
