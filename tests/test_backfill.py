from datetime import UTC, date, datetime
from pathlib import Path

import responses

from mimir.backfill import run_backfill

CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2018-01-02,1.0,2.0,0.5,1.5,100\n"
    "2018-01-03,1.5,2.5,1.0,2.0,200\n"
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
