from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from datetime import date, timedelta
from pathlib import Path

from mimir.core.source import Dataset
from mimir.storage.paths import DEFAULT_ROOT, partition_path
from mimir.storage.schema import Record


class JsonlStore:
    def __init__(self, root: Path = DEFAULT_ROOT) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def partition_dates(self, dataset: Dataset) -> list[date]:
        """Read-only: sorted partition dates for a dataset (empty if absent).

        Reconstructs the date from the `data/<dataset>/YYYY/MM/DD.jsonl` layout
        (the inverse of `partition_path`); lexicographic path order is chronological.
        """
        base = self._root / dataset.value
        if not base.exists():
            return []
        out: list[date] = []
        for path in sorted(base.rglob("*.jsonl")):
            out.append(date(int(path.parent.parent.name), int(path.parent.name), int(path.stem)))
        return out

    def _read_file(self, path: Path) -> Iterator[Record]:
        with path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if line:
                    yield Record.model_validate_json(line)

    def _existing_keys(self, path: Path) -> set[str]:
        if not path.exists():
            return set()
        return {rec.idempotency_key for rec in self._read_file(path)}

    def append(self, records: Iterable[Record], *, overwrite: bool = False) -> int:
        """Persist records into date partitions.

        Default is append-only with first-write-wins dedup (raw collected data is
        immutable). `overwrite=True` gives last-write-wins by rewriting the
        partition — use it for regenerated datasets (insights/historical) so a
        same-day re-run reflects the newest computation instead of the first.
        """
        by_path: dict[Path, list[Record]] = defaultdict(list)
        for rec in records:
            by_path[partition_path(rec.dataset, rec.ts.date(), self._root)].append(rec)

        written = 0
        for path, recs in by_path.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            written += (
                self._append_overwrite(path, recs)
                if overwrite
                else self._append_only(path, recs)
            )
        return written

    def _append_only(self, path: Path, recs: list[Record]) -> int:
        seen = self._existing_keys(path)
        appended = 0
        with path.open("a", encoding="utf-8") as fh:
            for rec in recs:
                if rec.idempotency_key in seen:
                    continue
                fh.write(rec.model_dump_json() + "\n")
                seen.add(rec.idempotency_key)
                appended += 1
        return appended

    def _append_overwrite(self, path: Path, recs: list[Record]) -> int:
        merged: dict[str, Record] = {}
        if path.exists():
            for rec in self._read_file(path):
                merged[rec.idempotency_key] = rec
        new_keys = 0
        for rec in recs:
            if rec.idempotency_key not in merged:
                new_keys += 1
            merged[rec.idempotency_key] = rec  # last-write-wins
        with path.open("w", encoding="utf-8") as fh:
            for rec in merged.values():
                fh.write(rec.model_dump_json() + "\n")
        return new_keys

    def read_window(
        self, dataset: Dataset, *, since: date | None = None, until: date | None = None
    ) -> Iterator[Record]:
        """Yield records for a dataset, opening only partitions in [since, until]
        when both bounds are given (partition pruning); otherwise scan the tree."""
        base = self._root / dataset.value
        if not base.exists():
            return
        if since is not None and until is not None:
            day = since
            while day <= until:
                path = partition_path(dataset, day, self._root)
                if path.exists():
                    yield from self._read_file(path)
                day += timedelta(days=1)
            return
        for path in sorted(base.rglob("*.jsonl")):
            for rec in self._read_file(path):
                if until is not None and rec.ts.date() > until:
                    continue
                yield rec

    def read_all(self, dataset: Dataset) -> Iterator[Record]:
        yield from self.read_window(dataset)
