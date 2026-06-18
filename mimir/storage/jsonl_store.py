from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from datetime import date, timedelta
from pathlib import Path

from mimir.core.source import Dataset
from mimir.storage.paths import DEFAULT_ROOT, partition_path
from mimir.storage.schema import Record


def _same_stored_record(left: Record, right: Record) -> bool:
    return left.model_dump(exclude={"captured_at"}) == right.model_dump(exclude={"captured_at"})


class JsonlStore:
    def __init__(self, root: Path = DEFAULT_ROOT) -> None:
        self._root = root
        self._revision = 0

    @property
    def root(self) -> Path:
        return self._root

    @property
    def revision(self) -> int:
        return self._revision

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
        immutable). `overwrite=True` gives last-write-wins when callers provide
        replacement records for keyed data. Regenerated daily outputs should use
        `replace_partition` so stale rows are removed when a rerun produces an
        empty or smaller result set.
        """
        by_path: dict[Path, list[Record]] = defaultdict(list)
        for rec in records:
            by_path[partition_path(rec.dataset, rec.ts.date(), self._root)].append(rec)

        written = 0
        for path, recs in by_path.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            written += (
                self._append_overwrite(path, recs) if overwrite else self._append_only(path, recs)
            )
        if written:
            self._revision += 1
        return written

    def replace_partition(self, dataset: Dataset, day: date, records: Iterable[Record]) -> int:
        """Replace one dataset/day partition exactly with ``records``.

        Regenerated datasets such as insights, historical, and evaluation need
        whole-partition replacement. If a rerun produces zero records, stale
        records from the previous run must disappear instead of surviving because
        there is no new key to overwrite.
        """
        path = partition_path(dataset, day, self._root)
        recs = list(records)
        for rec in recs:
            if rec.dataset != dataset or rec.ts.date() != day:
                raise ValueError(
                    "replace_partition records must all match the target dataset and day"
                )
        if not recs:
            if path.exists():
                path.unlink()
                self._revision += 1
            return 0
        if path.exists():
            existing = list(self._read_file(path))
            if [rec.model_dump() for rec in existing] == [rec.model_dump() for rec in recs]:
                return 0
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for rec in recs:
                fh.write(rec.model_dump_json() + "\n")
        self._revision += 1
        return len(recs)

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
        incoming: dict[str, Record] = {}
        for rec in recs:
            incoming[rec.idempotency_key] = rec
        changed = 0
        for rec in incoming.values():
            current = merged.get(rec.idempotency_key)
            if current is None or not _same_stored_record(current, rec):
                changed += 1
                merged[rec.idempotency_key] = rec  # last-write-wins
        if changed == 0:
            return 0
        with path.open("w", encoding="utf-8") as fh:
            for rec in merged.values():
                fh.write(rec.model_dump_json() + "\n")
        return changed

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
                if since is not None and rec.ts.date() < since:
                    continue
                if until is not None and rec.ts.date() > until:
                    continue
                yield rec

    def read_all(self, dataset: Dataset) -> Iterator[Record]:
        yield from self.read_window(dataset)
