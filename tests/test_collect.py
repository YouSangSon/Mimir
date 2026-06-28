from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import responses

from mimir.collect import main, run_collect

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


@responses.activate
def test_run_collect_explicit_env_does_not_load_dotenv(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("STOOQ_API_KEY=fromdotenv\n", encoding="utf-8")
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)

    summary = run_collect(
        cadence="daily",
        env={},
        watchlist={"us": ["AAPL"], "kr": []},
        data_root=tmp_path / "data",
        status_path=tmp_path / "reports/status.html",
        sources_config={"disabled_ids": ["sec_edgar", "rss"]},
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert summary.had_failures is False
    assert len(responses.calls) == 0
    assert not (tmp_path / "data/prices/2026/05/29.jsonl").exists()


def test_run_collect_uses_typed_runtime_config_for_registry_and_lang(tmp_path: Path):
    summary = run_collect(
        cadence="daily",
        env={},
        watchlist={"us": [], "kr": []},
        data_root=tmp_path / "data",
        status_path=tmp_path / "reports/status.html",
        sources_config={
            "gray_enabled": False,
            "disabled_ids": ["sec_edgar", "rss"],
            "lang": "ko",
        },
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )

    html = (tmp_path / "reports/status.html").read_text(encoding="utf-8")
    assert summary.had_failures is False
    assert 'lang="ko"' in html
    assert "source(s)" not in html


@responses.activate
def test_collect_cli_auto_loads_dotenv(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("STOOQ_API_KEY=fromdotenv\n", encoding="utf-8")
    (tmp_path / "sources.yaml").write_text(
        "disabled_ids: [sec_edgar, rss]\n",
        encoding="utf-8",
    )
    (tmp_path / "watchlist.yaml").write_text("us: [AAPL]\nkr: []\n", encoding="utf-8")
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)

    assert main(["--cadence", "daily", "--config-dir", str(tmp_path)]) == 0

    assert (tmp_path / "data/prices/2026/05/29.jsonl").exists()


@responses.activate
def test_collect_cli_real_env_overrides_dotenv(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("STOOQ_API_KEY=fromdotenv\n", encoding="utf-8")
    (tmp_path / "sources.yaml").write_text(
        "disabled_ids: [sec_edgar, rss]\n",
        encoding="utf-8",
    )
    (tmp_path / "watchlist.yaml").write_text("us: [AAPL]\nkr: []\n", encoding="utf-8")
    monkeypatch.setenv("STOOQ_API_KEY", "fromrealenv")
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)

    assert main(["--cadence", "daily", "--config-dir", str(tmp_path)]) == 0

    query = parse_qs(urlparse(responses.calls[0].request.url).query)
    assert query["apikey"] == ["fromrealenv"]


def test_collect_cli_reports_sec_ticker_map_build_error(tmp_path: Path, capsys):
    (tmp_path / "sources.yaml").write_text(
        """
        sources:
          rss:
            sec:
              ticker_cik_map_path: company_tickers.json
              company_filings:
                - ticker: AAPL
        """,
        encoding="utf-8",
    )
    (tmp_path / "company_tickers.json").write_text("{", encoding="utf-8")
    (tmp_path / "watchlist.yaml").write_text("us: []\nkr: []\n", encoding="utf-8")

    rc = main(["--cadence", "daily", "--config-dir", str(tmp_path)])

    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("[mimir] invalid sources.yaml:")
    assert "SEC ticker CIK map file is not valid JSON" in err


def test_collect_cli_reports_invalid_watchlist_yaml(tmp_path: Path, capsys):
    (tmp_path / "watchlist.yaml").write_text("us: AAPL\nkr: []\n", encoding="utf-8")

    code = main(["--cadence", "daily", "--config-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 1
    assert "[mimir] invalid watchlist.yaml:" in captured.err
    assert str(tmp_path / "watchlist.yaml") in captured.err


def test_collect_cli_reports_missing_sec_ticker_mapping(tmp_path: Path, capsys):
    (tmp_path / "sources.yaml").write_text(
        """
        sources:
          rss:
            sec:
              ticker_cik_map_path: company_tickers.json
              company_filings:
                - ticker: MSFT
        """,
        encoding="utf-8",
    )
    (tmp_path / "company_tickers.json").write_text(
        '{"0": {"cik_str": 320193, "ticker": "AAPL"}}',
        encoding="utf-8",
    )
    (tmp_path / "watchlist.yaml").write_text("us: []\nkr: []\n", encoding="utf-8")

    map_path = tmp_path / "company_tickers.json"
    rc = main(["--cadence", "daily", "--config-dir", str(tmp_path)])

    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("[mimir] invalid sources.yaml:")
    assert f"SEC ticker CIK map has no entry for ticker MSFT in {map_path}" in err


def test_collect_cli_uses_watchlist_for_sec_watchlist_filing_feeds(
    tmp_path: Path, capsys
):
    (tmp_path / "sources.yaml").write_text(
        """
        sources:
          rss:
            sec:
              ticker_cik_map_path: company_tickers.json
              watchlist_company_filings:
                enabled: true
                forms: ["10-K"]
        """,
        encoding="utf-8",
    )
    (tmp_path / "company_tickers.json").write_text(
        '{"0": {"cik_str": 789019, "ticker": "MSFT"}}',
        encoding="utf-8",
    )
    (tmp_path / "watchlist.yaml").write_text("us: [AAPL]\nkr: []\n", encoding="utf-8")

    map_path = tmp_path / "company_tickers.json"
    rc = main(["--cadence", "daily", "--config-dir", str(tmp_path)])

    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("[mimir] invalid sources.yaml:")
    assert f"SEC ticker CIK map has no entry for ticker AAPL in {map_path}" in err
