from __future__ import annotations

from datetime import date

from mimir.core.source import Dataset
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record


class DataReader:
    """Read-only access to S1's stored JSONL, filtered by dataset/symbol/date window."""

    def __init__(self, store: JsonlStore) -> None:
        self._store = store

    def read(
        self,
        dataset: Dataset,
        *,
        symbol: str | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> list[Record]:
        out: list[Record] = []
        for rec in self._store.read_all(dataset):
            if symbol is not None and rec.symbol != symbol:
                continue
            day = rec.ts.date()
            if since is not None and day < since:
                continue
            if until is not None and day > until:
                continue
            out.append(rec)
        return out
