import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import responses

from mimir.backfill import main, run_backfill
from mimir.manifest.manifest import Manifest

CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2018-01-02,1.0,2.0,0.5,1.5,100\n"
    "2018-01-03,1.5,2.5,1.0,2.0,200\n"
)

FRED_OBS = {"observations": [{"date": "2024-01-02", "value": "4.00"}]}
FRED_REVISED_OBS = {"observations": [{"date": "2024-01-02", "value": "4.25"}]}
CSV_REVISED = (
    "Date,Open,High,Low,Close,Volume\n"
    "2018-01-02,9.0,9.0,9.0,9.5,900\n"
    "2018-01-03,9.5,9.5,9.5,10.0,1000\n"
)


@responses.activate
def test_backfill_stooq_loads_history(tmp_path: Path):
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)
    appended = run_backfill(
        source_id="stooq",
        since=date(2018, 1, 1),
        env={"STOOQ_API_KEY": "test-key"},
        watchlist={"us": ["AAPL"], "kr": []},
        data_root=tmp_path / "data",
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )
    assert appended == 2
    assert (tmp_path / "data/prices/2018/01/02.jsonl").exists()
    latest = Manifest(root=tmp_path / "data").latest_run()
    assert latest is not None
    assert latest.cadence == "daily"
    result = latest.results[0]
    assert result.source == "stooq"
    assert result.ok is True
    assert result.fetched == 2
    assert result.stored == 2
    assert result.invalid == 0


@responses.activate
def test_backfill_fred_honors_configured_series(tmp_path: Path):
    # A FRED series supplied via sources_config flows end-to-end; the persisted
    # record's idempotency_key keeps the canonical `fred:{series}:{day}` format
    # regardless of whether the series came from config or the code default.
    responses.add(
        responses.GET,
        "https://api.stlouisfed.org/fred/series/observations",
        body=json.dumps(FRED_OBS),
        status=200,
    )
    appended = run_backfill(
        source_id="fred",
        since=date(2024, 1, 1),
        env={"FRED_API_KEY": "test-key"},
        watchlist={"us": [], "kr": []},
        data_root=tmp_path / "data",
        sources_config={"sources": {"fred": {"series": ["DGS10"]}}},
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )
    assert appended == 1
    partition = tmp_path / "data/macro/2024/01/02.jsonl"
    assert partition.exists()
    record = json.loads(partition.read_text(encoding="utf-8").strip())
    assert record["idempotency_key"] == "fred:DGS10:2024-01-02"  # invariant 2
    assert record["payload"]["series_id"] == "DGS10"


@responses.activate
def test_backfill_fred_revisions_overwrite_existing_observation(tmp_path: Path):
    responses.add(
        responses.GET,
        "https://api.stlouisfed.org/fred/series/observations",
        body=json.dumps(FRED_OBS),
        status=200,
    )
    responses.add(
        responses.GET,
        "https://api.stlouisfed.org/fred/series/observations",
        body=json.dumps(FRED_REVISED_OBS),
        status=200,
    )
    kwargs = {
        "source_id": "fred",
        "since": date(2024, 1, 1),
        "env": {"FRED_API_KEY": "test-key"},
        "watchlist": {"us": [], "kr": []},
        "data_root": tmp_path / "data",
        "sources_config": {"sources": {"fred": {"series": ["DGS10"]}}},
        "now": datetime(2026, 5, 31, tzinfo=UTC),
    }

    run_backfill(**kwargs)
    revised = run_backfill(**kwargs)

    partition = tmp_path / "data/macro/2024/01/02.jsonl"
    lines = partition.read_text(encoding="utf-8").strip().splitlines()
    record = json.loads(lines[0])
    latest = Manifest(root=tmp_path / "data").latest_run()
    assert revised == 1
    assert len(lines) == 1
    assert record["payload"]["value"] == 4.25
    assert latest is not None
    assert latest.results[0].stored == 1


@responses.activate
def test_backfill_fred_unchanged_observation_does_not_update_capture_time(tmp_path: Path):
    responses.add(
        responses.GET,
        "https://api.stlouisfed.org/fred/series/observations",
        body=json.dumps(FRED_OBS),
        status=200,
    )
    responses.add(
        responses.GET,
        "https://api.stlouisfed.org/fred/series/observations",
        body=json.dumps(FRED_OBS),
        status=200,
    )
    kwargs = {
        "source_id": "fred",
        "since": date(2024, 1, 1),
        "env": {"FRED_API_KEY": "test-key"},
        "watchlist": {"us": [], "kr": []},
        "data_root": tmp_path / "data",
        "sources_config": {"sources": {"fred": {"series": ["DGS10"]}}},
    }

    run_backfill(**kwargs, now=datetime(2026, 5, 31, tzinfo=UTC))
    stored = run_backfill(**kwargs, now=datetime(2026, 6, 1, tzinfo=UTC))

    partition = tmp_path / "data/macro/2024/01/02.jsonl"
    record = json.loads(partition.read_text(encoding="utf-8").strip())
    latest = Manifest(root=tmp_path / "data").latest_run()
    assert stored == 0
    assert record["captured_at"] == "2026-05-31T00:00:00Z"
    assert latest is not None
    assert latest.results[0].stored == 0


@responses.activate
def test_backfill_stooq_keeps_first_write_wins_for_prices(tmp_path: Path):
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV_REVISED, status=200)
    kwargs = {
        "source_id": "stooq",
        "since": date(2018, 1, 1),
        "env": {"STOOQ_API_KEY": "test-key"},
        "watchlist": {"us": ["AAPL"], "kr": []},
        "data_root": tmp_path / "data",
        "now": datetime(2026, 5, 31, tzinfo=UTC),
    }

    run_backfill(**kwargs)
    stored = run_backfill(**kwargs)

    partition = tmp_path / "data/prices/2018/01/02.jsonl"
    record = json.loads(partition.read_text(encoding="utf-8").strip())
    latest = Manifest(root=tmp_path / "data").latest_run()
    assert stored == 0
    assert record["payload"]["close"] == 1.5
    assert latest is not None
    assert latest.results[0].stored == 0


@responses.activate
def test_backfill_records_invalid_count_in_manifest(tmp_path: Path, monkeypatch):
    from mimir import backfill as backfill_mod
    from mimir.core.errors import NormalizationError

    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)
    real_normalize = backfill_mod.normalize
    calls = {"n": 0}

    def flaky_normalize(raw, meta, *, captured_at):
        calls["n"] += 1
        if calls["n"] == 1:
            raise NormalizationError("bad record")
        return real_normalize(raw, meta, captured_at=captured_at)

    monkeypatch.setattr(backfill_mod, "normalize", flaky_normalize)

    appended = run_backfill(
        source_id="stooq",
        since=date(2018, 1, 1),
        env={"STOOQ_API_KEY": "test-key"},
        watchlist={"us": ["AAPL"], "kr": []},
        data_root=tmp_path / "data",
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert appended == 1
    latest = Manifest(root=tmp_path / "data").latest_run()
    assert latest is not None
    result = latest.results[0]
    assert result.fetched == 2
    assert result.stored == 1
    assert result.invalid == 1


def test_backfill_records_failure_manifest_before_reraising(tmp_path: Path, monkeypatch):
    from mimir import backfill as backfill_mod
    from mimir.core.source import (
        Cadence,
        Dataset,
        FetchContext,
        LegalStatus,
        Market,
        RateLimit,
        SourceMeta,
    )

    class FailSource:
        meta = SourceMeta(
            id="fail",
            market=Market.US,
            dataset=Dataset.PRICES,
            cadence=Cadence.DAILY,
            legal_status=LegalStatus.OFFICIAL,
            rate_limit=RateLimit(),
        )

        def fetch(self, ctx: FetchContext):
            raise RuntimeError("upstream down")

    monkeypatch.setattr(backfill_mod, "build_sources", lambda settings, config: [FailSource()])

    with pytest.raises(RuntimeError, match="upstream down"):
        run_backfill(
            source_id="fail",
            since=date(2018, 1, 1),
            env={},
            watchlist={"us": ["AAPL"], "kr": []},
            data_root=tmp_path / "data",
            now=datetime(2026, 5, 31, tzinfo=UTC),
        )

    latest = Manifest(root=tmp_path / "data").latest_run()
    assert latest is not None
    result = latest.results[0]
    assert result.source == "fail"
    assert result.ok is False
    assert "upstream down" in (result.error or "")


@responses.activate
def test_backfill_preserves_original_error_when_failure_manifest_write_fails(
    tmp_path: Path, monkeypatch
):
    from mimir import backfill as backfill_mod

    class FailingManifest:
        def __init__(self, root: Path) -> None:
            self.root = root

        def write(self, **kwargs):
            raise OSError("manifest write failed")

    def exploding_normalize(raw, meta, *, captured_at):
        raise ValueError("normalize exploded")

    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)
    monkeypatch.setattr(backfill_mod, "Manifest", FailingManifest)
    monkeypatch.setattr(backfill_mod, "normalize", exploding_normalize)

    with pytest.raises(ValueError, match="normalize exploded"):
        run_backfill(
            source_id="stooq",
            since=date(2018, 1, 1),
            env={"STOOQ_API_KEY": "test-key"},
            watchlist={"us": ["AAPL"], "kr": []},
            data_root=tmp_path / "data",
            now=datetime(2026, 5, 31, tzinfo=UTC),
        )


def test_main_reports_invalid_sources_yaml(tmp_path: Path, capsys):
    # A malformed sources.yaml surfaces as a friendly `[mimir] invalid sources.yaml:`
    # message and a non-zero exit (spec §5), not a raw pydantic traceback.
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "sources.yaml").write_text(
        "sources:\n  fred:\n    serie: [DGS10]\n", encoding="utf-8"
    )
    (config_dir / "watchlist.yaml").write_text("us: []\nkr: []\n", encoding="utf-8")

    rc = main(["--source", "fred", "--since", "2024-01-01", "--config-dir", str(config_dir)])

    assert rc != 0
    assert "[mimir] invalid sources.yaml:" in capsys.readouterr().err
