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
