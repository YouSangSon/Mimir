from __future__ import annotations

from datetime import date

from mimir.core.source import Dataset
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record


class DataReader:
    """Read-only access to stored JSONL, filtered by dataset/symbol/date window.

    Date bounds are pushed down to the store for partition pruning; the exact
    `since`/`until` and `symbol` filters are re-applied here as a correctness guard.
    """

    def __init__(self, store: JsonlStore) -> None:
        self._store = store
        self._captured_index: dict[Dataset, tuple[int, dict[date, tuple[Record, ...]]]] = {}

    def read(
        self,
        dataset: Dataset,
        *,
        symbol: str | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> list[Record]:
        out: list[Record] = []
        for rec in self._store.read_window(dataset, since=since, until=until):
            if symbol is not None and rec.symbol != symbol:
                continue
            day = rec.ts.date()
            if since is not None and day < since:
                continue
            if until is not None and day > until:
                continue
            out.append(rec)
        return out

    def read_captured_window(
        self,
        dataset: Dataset,
        *,
        symbol: str | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> list[Record]:
        out: list[Record] = []
        index = self._captured_date_index(dataset)
        for day in sorted(index):
            if since is not None and day < since:
                continue
            if until is not None and day > until:
                continue
            for rec in index[day]:
                if symbol is not None and rec.symbol != symbol:
                    continue
                out.append(rec)
        return out

    def _captured_date_index(self, dataset: Dataset) -> dict[date, tuple[Record, ...]]:
        revision = self._store.revision
        cached = self._captured_index.get(dataset)
        if cached is not None and cached[0] == revision:
            return cached[1]

        buckets: dict[date, list[Record]] = {}
        # Partitions are keyed by rec.ts.date(), so captured_at windows cannot
        # safely use read_window() pruning without dropping late-captured records.
        for rec in self._store.read_all(dataset):
            buckets.setdefault(rec.captured_at.date(), []).append(rec)
        index = {day: tuple(records) for day, records in buckets.items()}
        self._captured_index[dataset] = (revision, index)
        return index
