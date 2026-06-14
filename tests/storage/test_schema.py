from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from mimir.core.source import Dataset, Market
from mimir.storage.schema import Record

# A full, schema-conforming PRICES payload (Record.payload is now the typed union).
PRICE_PAYLOAD = {
    "open": 195.1,
    "high": 195.1,
    "low": 195.1,
    "close": 195.1,
    "volume": 1.0,
    "currency": "USD",
    "interval": "1d",
}


def test_record_serializes_to_json_line():
    rec = Record(
        source="stooq",
        dataset=Dataset.PRICES,
        market=Market.US,
        symbol="AAPL",
        ts=datetime(2026, 5, 29, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key="stooq:AAPL:2026-05-29",
        payload=dict(PRICE_PAYLOAD),
    )
    line = rec.model_dump_json()
    again = Record.model_validate_json(line)
    assert again.idempotency_key == "stooq:AAPL:2026-05-29"
    assert again.schema_version == 1


def test_record_rejects_missing_required_field():
    # Payload is valid so the ONLY failure is the missing idempotency_key, which
    # must surface as a pydantic ValidationError (not a PayloadSchemaError).
    with pytest.raises(ValidationError):
        Record(
            source="x",
            dataset=Dataset.PRICES,
            market=Market.US,
            symbol=None,
            ts=datetime(2026, 5, 29, tzinfo=UTC),
            captured_at=datetime(2026, 5, 29, tzinfo=UTC),
            payload=dict(PRICE_PAYLOAD),
        )  # missing idempotency_key
