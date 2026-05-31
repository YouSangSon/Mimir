from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

from mimir.core.source import Dataset
from mimir.storage.paths import DEFAULT_ROOT, partition_path
from mimir.storage.schema import Record


class JsonlStore:
    def __init__(self, root: Path = DEFAULT_ROOT) -> None:
        self._root = root

    def _existing_keys(self, path: Path) -> set[str]:
        if not path.exists():
            return set()
        keys: set[str] = set()
        with path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if line:
                    keys.add(Record.model_validate_json(line).idempotency_key)
        return keys

    def append(self, records: Iterable[Record]) -> int:
        by_path: dict[Path, list[Record]] = defaultdict(list)
        for rec in records:
            by_path[partition_path(rec.dataset, rec.ts.date(), self._root)].append(rec)

        appended = 0
        for path, recs in by_path.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            seen = self._existing_keys(path)
            with path.open("a", encoding="utf-8") as fh:
                for rec in recs:
                    if rec.idempotency_key in seen:
                        continue
                    fh.write(rec.model_dump_json() + "\n")
                    seen.add(rec.idempotency_key)
                    appended += 1
        return appended

    def read_all(self, dataset: Dataset) -> Iterator[Record]:
        base = self._root / dataset.value
        if not base.exists():
            return
        for path in sorted(base.rglob("*.jsonl")):
            with path.open("r", encoding="utf-8") as fh:
                for raw_line in fh:
                    line = raw_line.strip()
                    if line:
                        yield Record.model_validate_json(line)
