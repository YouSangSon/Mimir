from mimir.core.source import Dataset
from mimir.storage.policy import append_overwrite_enabled


def test_append_overwrite_enabled_only_for_macro_sources():
    assert append_overwrite_enabled(Dataset.MACRO) is True
    assert append_overwrite_enabled(Dataset.PRICES) is False
    assert append_overwrite_enabled(Dataset.FILINGS) is False
    assert append_overwrite_enabled(Dataset.NEWS) is False
