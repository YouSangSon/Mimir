from datetime import date
from pathlib import Path

from mimir.core.source import Dataset
from mimir.storage.paths import partition_path


def test_partition_path_uses_dataset_and_date():
    p = partition_path(Dataset.PRICES, date(2026, 5, 31), root=Path("data"))
    assert p == Path("data/prices/2026/05/31.jsonl")


def test_partition_path_accepts_string_dataset():
    p = partition_path("filings", date(2026, 1, 9), root=Path("/tmp/x"))
    assert p == Path("/tmp/x/filings/2026/01/09.jsonl")
