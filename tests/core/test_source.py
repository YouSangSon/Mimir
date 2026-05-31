from datetime import UTC, datetime

from mimir.core.source import (
    Cadence,
    Dataset,
    FetchContext,
    LegalStatus,
    Market,
    RateLimit,
    RawRecord,
    Source,
    SourceMeta,
)


def test_source_meta_round_trips():
    meta = SourceMeta(
        id="stooq",
        market=Market.US,
        dataset=Dataset.PRICES,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1.0),
    )
    assert meta.id == "stooq"
    assert meta.legal_status is LegalStatus.OFFICIAL
    assert meta.requires_secret is None


def test_raw_record_requires_idempotency_key():
    rec = RawRecord(
        symbol="AAPL",
        ts=datetime(2026, 5, 29, tzinfo=UTC),
        idempotency_key="stooq:AAPL:2026-05-29",
        payload={"close": 1.0},
    )
    assert rec.idempotency_key == "stooq:AAPL:2026-05-29"


def test_source_protocol_is_runtime_checkable():
    class Dummy:
        meta = SourceMeta(
            id="d",
            market=Market.US,
            dataset=Dataset.PRICES,
            cadence=Cadence.DAILY,
            legal_status=LegalStatus.OFFICIAL,
            rate_limit=RateLimit(),
        )

        def fetch(self, ctx: FetchContext):
            return []

    assert isinstance(Dummy(), Source)
