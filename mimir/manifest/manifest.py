from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from mimir.core.source import Cadence
from mimir.storage.paths import DEFAULT_ROOT


class SourceResult(BaseModel):
    source: str
    ok: bool
    fetched: int = 0
    stored: int = 0
    invalid: int = 0
    error: str | None = None


class RunRecord(BaseModel):
    ran_at: datetime
    cadence: Cadence
    results: list[SourceResult]


class Manifest:
    def __init__(self, root: Path = DEFAULT_ROOT) -> None:
        self._root = root

    def write(
        self, *, now: datetime, cadence: Cadence, results: list[SourceResult]
    ) -> RunRecord:
        record = RunRecord(ran_at=now, cadence=cadence, results=results)
        path = self._root / "_manifest" / f"{now:%Y}" / f"{now:%m}" / f"{now:%d}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(record.model_dump_json() + "\n")
        return record
