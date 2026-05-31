import pytest
from datetime import UTC, datetime

from mimir.core.errors import NormalizationError
from mimir.core.normalize import normalize
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


def test_normalize_builds_record_from_meta():
    raw = RawRecord(
        symbol="AAPL",
        ts=datetime(2026, 5, 29, tzinfo=UTC),
        idempotency_key="stooq:AAPL:2026-05-29",
        payload={"close": 1.0},
    )
    rec = normalize(raw, META, captured_at=CAPTURED)
    assert rec.source == "stooq"
    assert rec.dataset is Dataset.PRICES
    assert rec.market is Market.US
    assert rec.captured_at == CAPTURED


def test_normalize_wraps_validation_failure():
    class Bad:
        symbol = "AAPL"
        ts = "not-a-datetime"
        idempotency_key = "k"
        payload: dict = {}

    with pytest.raises(NormalizationError):
        normalize(Bad(), META, captured_at=CAPTURED)  # type: ignore[arg-type]
