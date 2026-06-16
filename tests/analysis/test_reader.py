from datetime import UTC, date, datetime
from pathlib import Path

from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record


def _rec(
    symbol: str, day: int, dataset: Dataset = Dataset.PRICES, captured_day: int = 31
) -> Record:
    payload = (
        {
            "title": f"{symbol} headline",
            "url": "https://example.com/news",
            "publisher": "Example",
            "market": "US",
            "published_at": None,
            "summary": "",
        }
        if dataset is Dataset.NEWS
        else {
            "open": float(day),
            "high": float(day),
            "low": float(day),
            "close": float(day),
            "volume": 1.0,
            "currency": "USD",
            "interval": "1d",
        }
    )
    return Record(
        source="stooq",
        dataset=dataset,
        market=Market.US,
        symbol=symbol,
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, captured_day, tzinfo=UTC),
        idempotency_key=f"{dataset.value}:{symbol}:{day}:{captured_day}",
        payload=payload,
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


def test_read_captured_window_filters_by_captured_at_date(tmp_path: Path):
    records = [
        _rec("AAPL", 30, Dataset.NEWS, captured_day=31),
        _rec("AAPL", 30, Dataset.NEWS, captured_day=30),
        _rec("AAPL", 31, Dataset.NEWS, captured_day=30),
    ]
    reader = _reader(tmp_path, records)

    recs = reader.read_captured_window(
        Dataset.NEWS, since=date(2026, 5, 31), until=date(2026, 5, 31)
    )

    assert len(recs) == 1
    assert recs[0].captured_at.date() == date(2026, 5, 31)


def test_read_captured_window_applies_symbol_and_inclusive_bounds(tmp_path: Path):
    records = [
        _rec("AAPL", 20, Dataset.NEWS, captured_day=24),
        _rec("MSFT", 20, Dataset.NEWS, captured_day=24),
        _rec("AAPL", 20, Dataset.NEWS, captured_day=30),
        _rec("AAPL", 20, Dataset.NEWS, captured_day=31),
    ]
    reader = _reader(tmp_path, records)

    recs = reader.read_captured_window(
        Dataset.NEWS,
        symbol="AAPL",
        since=date(2026, 5, 24),
        until=date(2026, 5, 30),
    )

    assert {r.symbol for r in recs} == {"AAPL"}
    assert {r.captured_at.date() for r in recs} == {date(2026, 5, 24), date(2026, 5, 30)}
