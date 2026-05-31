from datetime import UTC, datetime
from pathlib import Path

from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record


def _rec(key: str, day: int) -> Record:
    return Record(
        source="stooq",
        dataset=Dataset.PRICES,
        market=Market.US,
        symbol="AAPL",
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key=key,
        payload={"close": 1.0},
    )


def test_append_writes_partitioned_file(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    n = store.append([_rec("k1", 29)])
    assert n == 1
    assert (tmp_path / "prices/2026/05/29.jsonl").exists()


def test_append_is_idempotent(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k1", 29)])
    added = store.append([_rec("k1", 29), _rec("k2", 29)])
    assert added == 1  # k1 already present, only k2 is new
    lines = (tmp_path / "prices/2026/05/29.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2


def test_append_groups_records_by_day(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k1", 29), _rec("k2", 30)])
    assert (tmp_path / "prices/2026/05/29.jsonl").exists()
    assert (tmp_path / "prices/2026/05/30.jsonl").exists()


def test_read_all_yields_records(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k1", 29), _rec("k2", 30)])
    keys = {r.idempotency_key for r in store.read_all(Dataset.PRICES)}
    assert keys == {"k1", "k2"}
