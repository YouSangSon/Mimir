from datetime import UTC, date, datetime
from pathlib import Path

from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.paths import partition_path
from mimir.storage.schema import Record


def _rec(day: int) -> Record:
    return Record(
        source="stooq",
        dataset=Dataset.PRICES,
        market=Market.US,
        symbol="AAPL",
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key=f"k{day}",
        payload={"close": 1.0},
    )


def test_root_property_exposes_store_root(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    assert store.root == tmp_path


def test_partition_dates_empty_when_dataset_absent(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    assert store.partition_dates(Dataset.MACRO) == []


def test_partition_dates_returns_sorted_dates(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec(30), _rec(28), _rec(29)])
    assert store.partition_dates(Dataset.PRICES) == [
        date(2026, 5, 28),
        date(2026, 5, 29),
        date(2026, 5, 30),
    ]


def test_partition_dates_round_trips_partition_path(tmp_path: Path):
    # Pin the layout assumption: a date written via partition_path is recovered.
    store = JsonlStore(root=tmp_path)
    d = date(2026, 5, 29)
    partition_path(Dataset.PRICES, d, tmp_path).parent.mkdir(parents=True, exist_ok=True)
    partition_path(Dataset.PRICES, d, tmp_path).write_text("", encoding="utf-8")
    assert store.partition_dates(Dataset.PRICES) == [d]
