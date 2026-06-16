from datetime import UTC, date, datetime
from pathlib import Path

from mimir.core.source import Dataset, Market
from mimir.historical.analog import HorizonStat
from mimir.historical.engine import HistoricalEngine
from mimir.historical.schema import HistoricalInsight, to_record
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

# 12 sessions with sharp drops at idx 2, 5, 8 (each ~-10%), each followed by recoveries.
CLOSES = [100, 100, 90, 95, 96, 86, 92, 93, 83, 90, 92, 95]


def _price_payload(close: float, volume: float = 1000.0) -> dict:
    return {
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": volume,
        "currency": "USD",
        "interval": "1d",
    }


def _seed_store(tmp_path: Path) -> JsonlStore:
    store = JsonlStore(root=tmp_path)
    records = [
        Record(
            source="seed",
            dataset=Dataset.PRICES,
            market=Market.US,
            symbol="AAPL",
            ts=datetime(2026, 5, day + 1, tzinfo=UTC),
            captured_at=datetime(2026, 5, 31, tzinfo=UTC),
            idempotency_key=f"p:AAPL:{day}",
            payload=_price_payload(float(close)),
        )
        for day, close in enumerate(CLOSES)
    ]
    store.append(records)
    return store


def test_engine_emits_sharp_drop_insight(tmp_path: Path):
    store = _seed_store(tmp_path)
    engine = HistoricalEngine(DataReader(store), store)
    insights = engine.run(
        {"us": ["AAPL"], "kr": []}, date(2026, 5, 31), captured_at=datetime(2026, 5, 31, tzinfo=UTC)
    )
    drop = [i for i in insights if i.event_type == "sharp_drop"]
    assert len(drop) == 1
    assert drop[0].occurrences == 3
    assert drop[0].horizons  # has forward-return stats
    stored = list(store.read_all(Dataset.HISTORICAL))
    assert any(r.idempotency_key == "historical:AAPL:sharp_drop:2026-05-31" for r in stored)


def test_engine_skips_below_min_occurrences(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    # only one drop -> below MIN_OCCURRENCES
    store.append(
        [
            Record(
                source="seed",
                dataset=Dataset.PRICES,
                market=Market.US,
                symbol="AAPL",
                ts=datetime(2026, 5, d, tzinfo=UTC),
                captured_at=datetime(2026, 5, 31, tzinfo=UTC),
                idempotency_key=f"p:AAPL:{d}",
                payload=_price_payload(c),
            )
            for d, c in [(1, 100.0), (2, 90.0), (3, 95.0)]
        ]
    )
    engine = HistoricalEngine(DataReader(store), store)
    insights = engine.run({"us": ["AAPL"], "kr": []}, date(2026, 5, 31))
    assert all(i.event_type != "sharp_drop" for i in insights)


def test_engine_clears_stale_historical_when_rerun_has_no_events(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    stale = HistoricalInsight(
        symbol="AAPL",
        market=Market.US,
        as_of=date(2026, 5, 31),
        event_type="sharp_drop",
        occurrences=3,
        triggered_today=False,
        horizons=[HorizonStat(horizon=5, n=2, median_return=0.01, pct_positive=0.5)],
        examples=[],
    )
    store.append([to_record(stale, datetime(2026, 5, 31, tzinfo=UTC))])
    store.append(
        [
            Record(
                source="seed",
                dataset=Dataset.PRICES,
                market=Market.US,
                symbol="AAPL",
                ts=datetime(2026, 5, d, tzinfo=UTC),
                captured_at=datetime(2026, 5, 31, tzinfo=UTC),
                idempotency_key=f"p:AAPL:{d}",
                payload=_price_payload(c),
            )
            for d, c in [(1, 100.0), (2, 101.0), (3, 102.0)]
        ]
    )
    engine = HistoricalEngine(DataReader(store), store)

    insights = engine.run({"us": ["AAPL"], "kr": []}, date(2026, 5, 31))

    assert insights == []
    assert list(store.read_all(Dataset.HISTORICAL)) == []
