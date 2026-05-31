from datetime import UTC, date, datetime
from pathlib import Path

from mimir.analysis.builder import build_signals
from mimir.analysis.engine import AnalysisEngine
from mimir.analysis.reader import DataReader
from mimir.analysis.signals.base import SignalDirection
from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record

AS_OF = date(2026, 5, 31)


def _price(symbol, day, close, volume) -> Record:
    return Record(
        source="seed",
        dataset=Dataset.PRICES,
        market=Market.US,
        symbol=symbol,
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key=f"p:{symbol}:{day}",
        payload={"close": close, "volume": volume},
    )


def test_engine_produces_and_stores_bullish_insight(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append(
        [
            _price("AAPL", 27, 100.0, 1000),
            _price("AAPL", 28, 104.0, 1000),
            _price("AAPL", 29, 110.0, 5000),
        ]
    )
    engine = AnalysisEngine(build_signals(), DataReader(store), store)
    insights = engine.run(
        {"us": ["AAPL"], "kr": []}, AS_OF, captured_at=datetime(2026, 5, 31, tzinfo=UTC)
    )

    assert len(insights) == 1
    assert insights[0].direction is SignalDirection.BULLISH
    # persisted to the insights dataset, idempotently
    stored = list(store.read_all(Dataset.INSIGHTS))
    assert len(stored) == 1
    assert stored[0].idempotency_key == "insight:AAPL:2026-05-31"


def test_engine_skips_symbols_with_no_signals(tmp_path: Path):
    store = JsonlStore(root=tmp_path)  # empty: no data for anyone
    engine = AnalysisEngine(build_signals(), DataReader(store), store)
    insights = engine.run({"us": ["AAPL"], "kr": []}, AS_OF)
    assert insights == []
    assert list(store.read_all(Dataset.INSIGHTS)) == []
