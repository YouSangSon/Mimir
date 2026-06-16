from __future__ import annotations

from mimir.core.source import Dataset

OVERWRITE_ON_APPEND_DATASETS = frozenset({Dataset.MACRO})


def append_overwrite_enabled(dataset: Dataset) -> bool:
    return dataset in OVERWRITE_ON_APPEND_DATASETS
