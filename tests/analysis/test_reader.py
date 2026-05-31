from datetime import UTC, date, datetime
from pathlib import Path

from mimir.analysis.reader import DataReader
from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record


def _rec(symbol: str, day: int, dataset: Dataset = Dataset.PRICES) -> Record:
    return Record(
        source="stooq",
        dataset=dataset,
        market=Market.US,
        symbol=symbol,
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key=f"{dataset.value}:{symbol}:{day}",
        payload={"close": float(day)},
    )


def _reader(tmp_path: Path, records) -> DataReader:
    store = JsonlStore(root=tmp_path)
    store.append(records)
    return DataReader(store)


def test_read_filters_by_symbol(tmp_path: Path):
    reader = _reader(tmp_path, [_rec("AAPL", 28), _rec("MSFT", 28)])
    recs = reader.read(Dataset.PRICES, symbol="AAPL")
    assert {r.symbol for r in recs} == {"AAPL"}


def test_read_filters_by_window(tmp_path: Path):
    reader = _reader(tmp_path, [_rec("AAPL", 27), _rec("AAPL", 29), _rec("AAPL", 31)])
    recs = reader.read(
        Dataset.PRICES, symbol="AAPL", since=date(2026, 5, 28), until=date(2026, 5, 30)
    )
    assert {r.ts.day for r in recs} == {29}


def test_read_empty_dataset_returns_empty(tmp_path: Path):
    reader = _reader(tmp_path, [_rec("AAPL", 28)])
    assert reader.read(Dataset.NEWS) == []
