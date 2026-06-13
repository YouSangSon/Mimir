import json
from datetime import UTC, date, datetime
from pathlib import Path

import responses

from mimir.backfill import run_backfill

CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2018-01-02,1.0,2.0,0.5,1.5,100\n"
    "2018-01-03,1.5,2.5,1.0,2.0,200\n"
)

FRED_OBS = {"observations": [{"date": "2024-01-02", "value": "4.00"}]}


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
