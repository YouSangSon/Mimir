from datetime import UTC, datetime
from pathlib import Path

import responses

from mimir.collect import run_collect

CSV = "Date,Open,High,Low,Close,Volume\n2026-05-29,1.0,2.0,0.5,1.5,100\n"
TICKERS = '{"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}'
SUBS = (
    '{"filings": {"recent": {"accessionNumber": [], "form": [], '
    '"filingDate": [], "primaryDocument": []}}}'
)


@responses.activate
def test_run_collect_writes_data_and_status(tmp_path: Path):
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)
    responses.add(
        responses.GET, "https://www.sec.gov/files/company_tickers.json", body=TICKERS, status=200
    )
    responses.add(
        responses.GET,
        "https://data.sec.gov/submissions/CIK0000320193.json",
        body=SUBS,
        status=200,
    )

    summary = run_collect(
        cadence="daily",
        env={"STOOQ_API_KEY": "test-key"},  # enable Stooq so prices are collected
        watchlist={"us": ["AAPL"], "kr": []},
        data_root=tmp_path / "data",
        status_path=tmp_path / "reports/status.html",
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )
    assert summary.had_failures is False
    assert (tmp_path / "data/prices/2026/05/29.jsonl").exists()
    assert (tmp_path / "reports/status.html").exists()
