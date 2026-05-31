from __future__ import annotations

from datetime import date
from pathlib import Path

from mimir.core.source import Dataset

DEFAULT_ROOT = Path("data")


def partition_path(dataset: Dataset | str, dt: date, root: Path = DEFAULT_ROOT) -> Path:
    name = dataset.value if isinstance(dataset, Dataset) else str(dataset)
    return root / name / f"{dt:%Y}" / f"{dt:%m}" / f"{dt:%d}.jsonl"
