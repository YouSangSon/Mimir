from datetime import UTC, datetime
from pathlib import Path

from mimir.core.orchestrator import Orchestrator
from mimir.core.registry import Registry
from mimir.core.source import (
    Cadence,
    Dataset,
    FetchContext,
    LegalStatus,
    Market,
    RateLimit,
    RawRecord,
    SourceMeta,
)
from mimir.manifest.manifest import Manifest
from mimir.storage.jsonl_store import JsonlStore


def _meta(id_: str) -> SourceMeta:
    return SourceMeta(
        id=id_,
        market=Market.US,
        dataset=Dataset.PRICES,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1000.0),
    )


def _price_payload(close: float) -> dict:
    # A full, schema-conforming PRICES payload (normalize now validates payloads).
    return {
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 1.0,
        "currency": "USD",
        "interval": "1d",
    }


class _OkSource:
    meta = _meta("ok")

    def fetch(self, ctx: FetchContext):
        yield RawRecord(
            symbol="AAPL",
            ts=datetime(2026, 5, 29, tzinfo=UTC),
            idempotency_key="ok:AAPL:1",
            payload=_price_payload(1.0),
        )


class _BoomSource:
    meta = _meta("boom")

    def fetch(self, ctx: FetchContext):
        raise RuntimeError("upstream down")


def _ctx():
    return FetchContext(watchlist={"us": ["AAPL"]}, now=datetime(2026, 5, 31, tzinfo=UTC))


def test_one_source_failure_does_not_block_others(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    manifest = Manifest(root=tmp_path)
    orch = Orchestrator(Registry([_BoomSource(), _OkSource()]), store, manifest)
    summary = orch.run(Cadence.DAILY, _ctx())
    by_id = {r.source: r for r in summary.results}
    assert by_id["ok"].ok is True
    assert by_id["ok"].stored == 1
    assert by_id["boom"].ok is False
    assert "upstream down" in (by_id["boom"].error or "")
    assert summary.had_failures is True


def test_records_are_persisted(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    orch = Orchestrator(Registry([_OkSource()]), store, Manifest(root=tmp_path))
    orch.run(Cadence.DAILY, _ctx())
    keys = {r.idempotency_key for r in store.read_all(Dataset.PRICES)}
    assert keys == {"ok:AAPL:1"}


class _TwoRecordSource:
    meta = _meta("two")

    def fetch(self, ctx: FetchContext):
        for i in (1, 2):
            yield RawRecord(
                symbol="AAPL",
                ts=datetime(2026, 5, 29, tzinfo=UTC),
                idempotency_key=f"two:AAPL:{i}",
                payload=_price_payload(float(i)),
            )


def test_one_invalid_record_is_counted_not_fatal(tmp_path: Path, monkeypatch):
    # The orchestrator's core resilience guarantee: a bad record is counted as
    # invalid and skipped, but the good ones in the same batch still persist.
    from mimir.core import orchestrator as orch_mod
    from mimir.core.errors import NormalizationError

    real = orch_mod.normalize
    calls = {"n": 0}

    def flaky_normalize(raw, meta, *, captured_at):
        calls["n"] += 1
        if calls["n"] == 1:
            raise NormalizationError("bad record")
        return real(raw, meta, captured_at=captured_at)

    monkeypatch.setattr(orch_mod, "normalize", flaky_normalize)
    store = JsonlStore(root=tmp_path)
    orch = Orchestrator(Registry([_TwoRecordSource()]), store, Manifest(root=tmp_path))
    summary = orch.run(Cadence.DAILY, _ctx())
    result = summary.results[0]
    assert result.ok is True
    assert result.fetched == 2
    assert result.stored == 1
    assert result.invalid == 1


def test_pykrx_retry_exhaustion_is_manifested_as_source_failure(tmp_path: Path):
    from mimir.sources.pykrx_source import PykrxSource

    def down_ohlcv_fn(fromdate, todate, ticker):
        raise RuntimeError("naver timeout")

    src = PykrxSource(
        ohlcv_fn=down_ohlcv_fn,
        max_retries=1,
        backoff=0.1,
        sleep=lambda seconds: None,
    )
    ctx = FetchContext(watchlist={"kr": ["005930"]}, now=datetime(2026, 5, 31, tzinfo=UTC))
    orch = Orchestrator(Registry([src]), JsonlStore(root=tmp_path), Manifest(root=tmp_path))

    summary = orch.run(Cadence.DAILY, ctx)

    result = summary.results[0]
    assert result.source == "pykrx"
    assert result.ok is False
    assert result.error is not None
    assert "pykrx OHLCV failed after 2 attempts for 005930" in result.error
    assert "naver timeout" in result.error
    assert summary.had_failures is True
