from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.paths import partition_path
from mimir.storage.schema import Record


def make_record(
    dataset: Dataset,
    day: date,
    *,
    symbol: str | None = None,
    key: str,
    payload: dict[str, Any] | None = None,
) -> Record:
    return Record(
        source="test",
        dataset=dataset,
        market=Market.US,
        symbol=symbol,
        ts=datetime(day.year, day.month, day.day, tzinfo=UTC),
        captured_at=datetime(day.year, day.month, day.day, tzinfo=UTC),
        idempotency_key=key,
        payload=payload or {},
    )


def write_partition(
    root: Path, dataset: Dataset, day: date, records: list[Record]
) -> Path:
    """Write a synthetic partition file directly (bypasses dedup/append logic).

    Allows writing an *empty* partition (records=[]) to exercise the `empty` check.
    """
    path = partition_path(dataset, day, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(rec.model_dump_json() + "\n")
    return path


def write_fresh_tree(root: Path, now: datetime) -> JsonlStore:
    """Every expected dataset has a non-empty latest partition dated `now`,
    plus enough prior prices partitions that `short` has a baseline."""
    today = now.date()
    store = JsonlStore(root=root)
    # prices: several prior days so the short-check median has >= 3 samples.
    for offset in (4, 3, 2, 1, 0):
        day = date.fromordinal(today.toordinal() - offset)
        recs = [
            make_record(Dataset.PRICES, day, symbol=f"S{i}", key=f"p-{day}-{i}",
                        payload={"close": 1.0})
            for i in range(10)
        ]
        write_partition(root, Dataset.PRICES, day, recs)
    for dataset in (Dataset.FILINGS, Dataset.NEWS, Dataset.INSIGHTS):
        write_partition(
            root, dataset, today,
            [make_record(dataset, today, key=f"{dataset.value}-{today}")],
        )
    # macro: DGS10 (daily) fresh today.
    write_partition(
        root, Dataset.MACRO, today,
        [make_record(Dataset.MACRO, today, symbol="DGS10", key=f"m-{today}",
                     payload={"series_id": "DGS10", "value": 4.0})],
    )
    return store
