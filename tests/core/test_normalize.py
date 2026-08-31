from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from mimir.core.errors import NormalizationError
from mimir.core.normalize import normalize
from mimir.core.payloads import PricePayload
from mimir.core.source import (
    Cadence,
    Dataset,
    LegalStatus,
    Market,
    RateLimit,
    RawRecord,
    SourceMeta,
)

META = SourceMeta(
    id="stooq",
    market=Market.US,
    dataset=Dataset.PRICES,
    cadence=Cadence.DAILY,
    legal_status=LegalStatus.OFFICIAL,
    rate_limit=RateLimit(),
)
CAPTURED = datetime(2026, 5, 31, tzinfo=UTC)

# A full, schema-conforming PRICES payload (parse_payload validates at normalize).
PRICE_PAYLOAD = {
    "open": 1.0,
    "high": 1.0,
    "low": 1.0,
    "close": 1.0,
    "volume": 1.0,
    "currency": "USD",
    "interval": "1d",
}


def test_normalize_builds_record_from_meta():
    raw = RawRecord(
        symbol="AAPL",
        ts=datetime(2026, 5, 29, tzinfo=UTC),
        idempotency_key="stooq:AAPL:2026-05-29",
        payload=dict(PRICE_PAYLOAD),
    )
    rec = normalize(raw, META, captured_at=CAPTURED)
    assert rec.source == "stooq"
    assert rec.dataset is Dataset.PRICES
    assert rec.market is Market.US
    assert rec.captured_at == CAPTURED
    assert isinstance(rec.payload, PricePayload)


def test_payload_boundary_does_not_need_type_ignore_comments():
    for path in (
        Path("mimir/core/normalize.py"),
        Path("mimir/core/payloads.py"),
        Path("tests/core/test_normalize.py"),
    ):
        assert "type: " "ignore" not in path.read_text(encoding="utf-8")


def test_normalize_rejects_payload_drift():
    # An unknown key is upstream drift; normalize must fail loudly, not silently.
    raw = RawRecord(
        symbol="AAPL",
        ts=datetime(2026, 5, 29, tzinfo=UTC),
        idempotency_key="stooq:AAPL:2026-05-29",
        payload={**PRICE_PAYLOAD, "unexpected": 1},
    )
    with pytest.raises(NormalizationError):
        normalize(raw, META, captured_at=CAPTURED)


def test_normalize_wraps_validation_failure():
    class Bad:
        symbol = "AAPL"
        ts = "not-a-datetime"
        idempotency_key = "k"
        payload: dict = {}

    with pytest.raises(NormalizationError):
        normalize(cast(RawRecord, Bad()), META, captured_at=CAPTURED)
