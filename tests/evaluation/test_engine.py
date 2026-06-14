from datetime import UTC, date, datetime
from pathlib import Path

from mimir.analysis.schema import Insight
from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.source import Dataset, Market
from mimir.evaluation.engine import EvaluationEngine
from mimir.evaluation.schema import BucketStat, EvaluationReport, HorizonEval
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

CAPTURED = datetime(2026, 5, 31, tzinfo=UTC)


def _price(symbol: str, market: Market, day: int, close: float) -> Record:
    return Record(
        source="seed",
        dataset=Dataset.PRICES,
        market=market,
        symbol=symbol,
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=CAPTURED,
        idempotency_key=f"p:{symbol}:{day}",
        payload={"close": close, "volume": 1000},
    )


def _insight_record(insight: Insight) -> Record:
    return Record(
        source="mimir_analysis",
        dataset=Dataset.INSIGHTS,
        market=insight.market,
        symbol=insight.symbol,
        ts=datetime(insight.as_of.year, insight.as_of.month, insight.as_of.day, tzinfo=UTC),
        captured_at=CAPTURED,
        idempotency_key=f"insight:{insight.symbol}:{insight.as_of.isoformat()}",
        payload=insight.model_dump(mode="json"),
    )


def _insight(
    symbol: str, market: Market, as_of_day: int, direction: SignalDirection, stars: int,
    signals: list[SignalResult],
) -> Insight:
    return Insight(
        symbol=symbol,
        market=market,
        as_of=date(2026, 5, as_of_day),
        direction=direction,
        stars=stars,
        confidence=0.7,
        signals=signals,
        reasons=["r"],
    )


def _sig(name: str, direction: SignalDirection) -> SignalResult:
    return SignalResult(signal=name, direction=direction, strength=0.5, confidence=0.7, reason="r")


def _seed_six_bullish_aapl(store: JsonlStore) -> None:
    """6 bullish insights on AAPL, each anchored 1 bar before a +10% move.

    AAPL closes rise every bar, so every bullish insight is a directional HIT
    at horizon 1 -> bucket survives MIN_EVAL_N=5 gating.
    """
    closes = [100.0, 110.0, 121.0, 133.1, 146.41, 161.05, 177.16, 194.87]
    store.append([_price("AAPL", Market.US, d + 1, c) for d, c in enumerate(closes)])
    # as_of on days 1..6 -> anchors at idx 1..6, each has a forward bar at h=1
    sig = [_sig("momentum", SignalDirection.BULLISH)]
    store.append(
        [
            _insight_record(
                _insight("AAPL", Market.US, d, SignalDirection.BULLISH, 4, sig)
            )
            for d in range(1, 7)
        ]
    )


def test_run_evaluates_and_stores_buckets(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    _seed_six_bullish_aapl(store)
    engine = EvaluationEngine(DataReader(store), store)
    report = engine.run(date(2026, 5, 31), captured_at=CAPTURED)

    assert report.sufficient is True
    assert report.insights_evaluated == 6
    dims = {b.dimension for b in report.buckets}
    assert dims == {"per_signal", "per_direction", "per_star"}
    # every bullish-up observation is a hit
    for b in report.buckets:
        assert b.market is Market.US
        for h in b.horizons:
            assert h.hit_rate == 1.0
    assert (tmp_path / "evaluation/2026/05/31.jsonl").exists()


def test_per_signal_uses_each_signals_own_direction(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    # AAPL rises; insight is aggregate-bullish but carries a bearish sub-signal.
    closes = [100.0, 110.0, 121.0, 133.1, 146.41, 161.05, 177.16]
    store.append([_price("AAPL", Market.US, d + 1, c) for d, c in enumerate(closes)])
    signals = [_sig("momentum", SignalDirection.BULLISH), _sig("meanrev", SignalDirection.BEARISH)]
    store.append(
        [
            _insight_record(_insight("AAPL", Market.US, d, SignalDirection.BULLISH, 4, signals))
            for d in range(1, 7)
        ]
    )
    engine = EvaluationEngine(DataReader(store), store)
    report = engine.run(date(2026, 5, 31), captured_at=CAPTURED)

    by_key = {(b.dimension, b.key): b for b in report.buckets}
    mom = by_key[("per_signal", "momentum")]
    rev = by_key[("per_signal", "meanrev")]
    # price goes up: bullish momentum hits, bearish meanrev misses
    assert mom.horizons[0].hit_rate == 1.0
    assert rev.horizons[0].hit_rate == 0.0


def test_markets_are_separated(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    _seed_six_bullish_aapl(store)
    # KR symbol, also 6 bullish, prices falling -> KR per_direction misses
    closes = [100.0, 90.0, 81.0, 72.9, 65.61, 59.05, 53.14, 47.83]
    store.append([_price("005930", Market.KR, d + 1, c) for d, c in enumerate(closes)])
    sig = [_sig("momentum", SignalDirection.BULLISH)]
    store.append(
        [
            _insight_record(_insight("005930", Market.KR, d, SignalDirection.BULLISH, 4, sig))
            for d in range(1, 7)
        ]
    )
    engine = EvaluationEngine(DataReader(store), store)
    report = engine.run(date(2026, 5, 31), captured_at=CAPTURED)

    markets = {(b.dimension, b.market) for b in report.buckets}
    assert (("per_direction"), Market.US) in markets
    assert (("per_direction"), Market.KR) in markets
    def _dir(market: Market) -> BucketStat:
        return next(
            b for b in report.buckets if b.dimension == "per_direction" and b.market is market
        )

    assert _dir(Market.US).horizons[0].hit_rate == 1.0  # US rising
    assert _dir(Market.KR).horizons[0].hit_rate == 0.0  # KR falling


def test_idempotent_rerun_keeps_record_count(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    _seed_six_bullish_aapl(store)
    engine = EvaluationEngine(DataReader(store), store)
    engine.run(date(2026, 5, 31), captured_at=CAPTURED)
    first = list(store.read_all(Dataset.EVALUATION))
    engine.run(date(2026, 5, 31), captured_at=CAPTURED)
    second = list(store.read_all(Dataset.EVALUATION))
    assert len(first) == len(second)


def test_cold_start_marks_insufficient(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    # only 2 insights -> below MIN_EVAL_N for any bucket
    closes = [100.0, 110.0, 121.0, 133.1]
    store.append([_price("AAPL", Market.US, d + 1, c) for d, c in enumerate(closes)])
    sig = [_sig("momentum", SignalDirection.BULLISH)]
    store.append(
        [
            _insight_record(_insight("AAPL", Market.US, d, SignalDirection.BULLISH, 4, sig))
            for d in range(1, 3)
        ]
    )
    engine = EvaluationEngine(DataReader(store), store)
    report = engine.run(date(2026, 5, 31), captured_at=CAPTURED)
    assert report.sufficient is False
    assert report.buckets == []


def test_lookahead_future_insight_contributes_nothing(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    _seed_six_bullish_aapl(store)
    # one extra insight as_of the LAST bar day -> no forward bar -> no observation
    sig = [_sig("momentum", SignalDirection.BULLISH)]
    store.append(
        [_insight_record(_insight("AAPL", Market.US, 8, SignalDirection.BULLISH, 4, sig))]
    )
    engine = EvaluationEngine(DataReader(store), store)
    report = engine.run(date(2026, 5, 31), captured_at=CAPTURED)
    # 7 read, but the day-8 one anchors past the series end -> n still reflects the 6
    assert report.insights_evaluated == 7
    star = next(b for b in report.buckets if b.dimension == "per_star")
    assert star.horizons[0].n == 6  # the too-recent insight added nothing


def _star_horizon(report: EvaluationReport, horizon: int) -> HorizonEval:
    star = next(b for b in report.buckets if b.dimension == "per_star")
    return next(h for h in star.horizons if h.horizon == horizon)


def test_future_price_bars_do_not_leak_through_until(tmp_path: Path):
    """Barrier (a): bars STORED after as_of must not become reachable forward bars.

    Prices span days 1-12 but we evaluate at as_of=day9, so `_load_bars(until=
    as_of)` must truncate to day9. Insights as_of days 1-9: those as_of 1-7 have
    an h=1 forward bar within the <=day9 window; as_of 8 and 9 do not. So
    per_star h1 n must be exactly 7. If the `until` truncation regressed (bars
    10-12 leaking in), as_of 8 and 9 would gain forward bars and n would be 9.
    """
    closes = [100.0 * (1.1**i) for i in range(12)]  # strictly rising, 12 bars
    store = JsonlStore(root=tmp_path)
    store.append([_price("AAPL", Market.US, d + 1, c) for d, c in enumerate(closes)])
    sig = [_sig("momentum", SignalDirection.BULLISH)]
    store.append(
        [
            _insight_record(_insight("AAPL", Market.US, d, SignalDirection.BULLISH, 4, sig))
            for d in range(1, 10)
        ]
    )
    engine = EvaluationEngine(DataReader(store), store)
    report = engine.run(date(2026, 5, 9), captured_at=CAPTURED)
    assert _star_horizon(report, 1).n == 7  # bars 10-12 did not leak into forward returns
