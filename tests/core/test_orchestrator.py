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


class _OkSource:
    meta = _meta("ok")

    def fetch(self, ctx: FetchContext):
        yield RawRecord(
            symbol="AAPL",
            ts=datetime(2026, 5, 29, tzinfo=UTC),
            idempotency_key="ok:AAPL:1",
            payload={"close": 1.0},
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
