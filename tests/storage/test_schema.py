from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from mimir.core.source import Dataset, Market
from mimir.storage.schema import Record


def test_record_serializes_to_json_line():
    rec = Record(
        source="stooq",
        dataset=Dataset.PRICES,
        market=Market.US,
        symbol="AAPL",
        ts=datetime(2026, 5, 29, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key="stooq:AAPL:2026-05-29",
        payload={"close": 195.1},
    )
    line = rec.model_dump_json()
    again = Record.model_validate_json(line)
    assert again.idempotency_key == "stooq:AAPL:2026-05-29"
    assert again.schema_version == 1


def test_record_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        Record(
            source="x",
            dataset=Dataset.PRICES,
            market=Market.US,
            symbol=None,
            ts=datetime(2026, 5, 29, tzinfo=UTC),
            captured_at=datetime(2026, 5, 29, tzinfo=UTC),
            payload={},
        )  # missing idempotency_key
