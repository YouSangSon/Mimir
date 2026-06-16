from datetime import UTC, date, datetime
from pathlib import Path

from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record


def _rec(
    key: str,
    day: int,
    close: float = 1.0,
    captured_at: datetime = datetime(2026, 5, 31, tzinfo=UTC),
) -> Record:
    return Record(
        source="stooq",
        dataset=Dataset.PRICES,
        market=Market.US,
        symbol="AAPL",
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=captured_at,
        idempotency_key=key,
        payload={
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1.0,
            "currency": "USD",
            "interval": "1d",
        },
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


def test_append_overwrite_is_last_write_wins(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k1", 29, close=1.0)])
    store.append([_rec("k1", 29, close=99.0)], overwrite=True)  # same key, revised payload
    recs = list(store.read_all(Dataset.PRICES))
    assert len(recs) == 1  # not duplicated
    assert recs[0].payload.close == 99.0  # newest value wins (typed payload)


def test_append_overwrite_counts_replaced_records(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k1", 29, close=1.0)])

    changed = store.append([_rec("k1", 29, close=99.0)], overwrite=True)

    assert changed == 1


def test_append_overwrite_counts_repeated_batch_key_once(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k1", 29, close=1.0)])

    changed = store.append(
        [
            _rec("k1", 29, close=2.0),
            _rec("k1", 29, close=3.0),
        ],
        overwrite=True,
    )

    recs = list(store.read_all(Dataset.PRICES))
    assert changed == 1
    assert len(recs) == 1
    assert recs[0].payload.close == 3.0


def test_append_overwrite_ignores_capture_time_only_changes(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    first_seen = datetime(2026, 5, 31, tzinfo=UTC)
    seen_again = datetime(2026, 6, 1, tzinfo=UTC)
    store.append([_rec("k1", 29, close=1.0, captured_at=first_seen)], overwrite=True)

    changed = store.append(
        [_rec("k1", 29, close=1.0, captured_at=seen_again)], overwrite=True
    )

    recs = list(store.read_all(Dataset.PRICES))
    assert changed == 0
    assert recs[0].captured_at == first_seen


def test_append_overwrite_noop_does_not_rewrite_partition(tmp_path: Path, monkeypatch):
    store = JsonlStore(root=tmp_path)
    first_seen = datetime(2026, 5, 31, tzinfo=UTC)
    seen_again = datetime(2026, 6, 1, tzinfo=UTC)
    store.append([_rec("k1", 29, close=1.0, captured_at=first_seen)], overwrite=True)
    partition = tmp_path / "prices/2026/05/29.jsonl"
    original_open = Path.open

    def fail_on_partition_write(self, mode="r", *args, **kwargs):
        if self == partition and "w" in mode:
            raise AssertionError("no-op overwrite must not rewrite partition")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_on_partition_write)

    changed = store.append([_rec("k1", 29, close=1.0, captured_at=seen_again)], overwrite=True)

    assert changed == 0


def test_replace_partition_removes_stale_records_when_new_result_is_empty(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("stale", 29)])

    written = store.replace_partition(Dataset.PRICES, date(2026, 5, 29), [])

    assert written == 0
    recs = list(
        store.read_window(Dataset.PRICES, since=date(2026, 5, 29), until=date(2026, 5, 29))
    )
    assert recs == []
    assert not (tmp_path / "prices/2026/05/29.jsonl").exists()


def test_replace_partition_replaces_stale_subset(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("stale", 29), _rec("keep", 29, close=1.0)])

    written = store.replace_partition(
        Dataset.PRICES, date(2026, 5, 29), [_rec("keep", 29, close=99.0)]
    )

    assert written == 1
    recs = list(store.read_window(Dataset.PRICES, since=date(2026, 5, 29), until=date(2026, 5, 29)))
    assert [r.idempotency_key for r in recs] == ["keep"]
    assert recs[0].payload.close == 99.0


def test_read_window_prunes_to_date_range(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k27", 27), _rec("k29", 29), _rec("k31", 31)])
    # both bounds -> only partitions in [29, 30] are opened
    keys = {
        r.idempotency_key
        for r in store.read_window(Dataset.PRICES, since=date(2026, 5, 29), until=date(2026, 5, 30))
    }
    assert keys == {"k29"}
    # until-only fallback still cuts off later partitions
    keys2 = {r.idempotency_key for r in store.read_window(Dataset.PRICES, until=date(2026, 5, 29))}
    assert keys2 == {"k27", "k29"}
    # since-only fallback still cuts off earlier partitions
    keys3 = {r.idempotency_key for r in store.read_window(Dataset.PRICES, since=date(2026, 5, 29))}
    assert keys3 == {"k29", "k31"}
