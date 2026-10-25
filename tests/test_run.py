from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
import responses
from pydantic import BaseModel, ValidationError

from mimir import run as run_module
from mimir.analysis.schema import Insight
from mimir.core.source import Dataset
from mimir.manifest.manifest import Manifest
from mimir.run import run_pipeline
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader


def test_run_pipeline_chains_all_stages_no_network(tmp_path: Path):
    # Disable the keyless network sources so the full pipeline runs offline and
    # deterministically; this verifies the collect->analyze->history->evaluate->deliver wiring.
    result = run_pipeline(
        cadence="daily",
        env={},
        watchlist={"us": [], "kr": []},
        data_root=tmp_path / "data",
        reports_root=tmp_path / "reports",
        sources_config={"disabled_ids": ["sec_edgar", "rss"]},
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )
    assert result["collect_failures"] is False
    assert result["insights"] == 0
    assert result["historical"] == 0
    assert result["evaluation"] == 0
    assert result["telegram_sent"] is False
    assert (tmp_path / "reports/2026/05/31.html").exists()
    assert (tmp_path / "reports/index.html").exists()


def test_run_pipeline_collects_prices_to_reports_and_preserves_them_on_failure(tmp_path: Path):
    # Synthetic observations only. Five prior insights meet the evaluation sample gate.
    rows = []
    close = 100.0
    for offset in range(61):
        day = date(2026, 8, 24) + timedelta(days=offset)
        if day.weekday() < 5:
            close *= 0.93 if len(rows) % 10 == 5 else 1.02
            rows.append((day, f"{day},{close},{close},{close},{close},1000\n"))
    data, reports = tmp_path / "data", tmp_path / "reports"
    config = {
        "disabled_ids": ["sec_edgar", "rss"],
        "gray_enabled": False,
        "llm_sentiment_enabled": False,
    }
    # Prior observations mature by the final session; no future prices are returned early.
    for as_of in [day for day, _ in rows[-10:-5]] + [rows[-1][0]]:
        csv = "Date,Open,High,Low,Close,Volume\n" + "".join(
            line for day, line in rows if day <= as_of
        )
        with responses.RequestsMock() as http:
            http.get("https://stooq.com/q/d/l/", body=csv)
            result = run_pipeline(
                cadence="daily", env={"STOOQ_API_KEY": "synthetic-fixture"},
                watchlist={"us": ["AAPL"], "kr": []}, data_root=data,
                reports_root=reports, sources_config=config,
                now=datetime.combine(as_of, datetime.min.time(), tzinfo=UTC),
            )
            assert len(http.calls) == 1
        assert result["collect_failures"] is False
        assert result["insights"] == 1

    reader = DataReader(JsonlStore(root=data))
    assert len(reader.read(Dataset.PRICES)) == len(rows)
    assert {record.source for record in reader.read(Dataset.PRICES)} == {"stooq"}
    assert result["historical"] > 0
    assert result["evaluation"] > 0
    assert reader.read(Dataset.HISTORICAL) and reader.read(Dataset.EVALUATION)
    assert result["telegram_sent"] is False
    html = Path(result["report"]).read_text(encoding="utf-8")
    current = Insight.model_validate(
        reader.read(Dataset.INSIGHTS, since=as_of, until=as_of)[0].payload
    )
    assert current.reasons[0] in html
    assert "Signal scorecard" in html and "per_signal" in html and "(n=5)" in html
    prices_before = {path: path.read_bytes() for path in (data / "prices").rglob("*.jsonl")}
    for path in (Path(result["report"]), reports / "status.html", reports / "index.html"):
        path.unlink()  # Prove the failed run regenerates outputs, rather than finding old files.

    with responses.RequestsMock() as http:
        http.get("https://stooq.com/q/d/l/", status=403)
        failed = run_pipeline(
            cadence="daily", env={"STOOQ_API_KEY": "synthetic-fixture"},
            watchlist={"us": ["AAPL"], "kr": []}, data_root=data,
            reports_root=reports, sources_config=config,
            now=datetime.combine(as_of, datetime.min.time(), tzinfo=UTC),
        )
        assert len(http.calls) == 1
    assert failed["collect_failures"] is True
    assert failed["insights"] == 1 and failed["evaluation"] > 0
    assert prices_before == {path: path.read_bytes() for path in (data / "prices").rglob("*.jsonl")}
    latest = Manifest(data).latest_run()
    assert latest is not None
    source = next(result for result in latest.results if result.source == "stooq")
    assert source.ok is False and "HTTP 403" in (source.error or "")
    html = Path(failed["report"]).read_text(encoding="utf-8")
    assert current.reasons[0] in html and "Signal scorecard" in html
    assert "HTTP 403" in (reports / "status.html").read_text(encoding="utf-8")
    assert (reports / "index.html").exists()


def test_run_pipeline_runs_evaluation_before_delivery(tmp_path: Path, monkeypatch):
    called = {"evaluation": False}

    class _Report:
        buckets = [object(), object()]

    def _fake_evaluate(**kwargs: object) -> _Report:
        called["evaluation"] = True
        assert kwargs["data_root"] == tmp_path / "data"
        assert kwargs["as_of"] == datetime(2026, 5, 31).date()
        assert kwargs["captured_at"] == datetime(2026, 5, 31, tzinfo=UTC)
        return _Report()

    monkeypatch.setattr(run_module, "run_evaluate", _fake_evaluate, raising=False)
    result = run_pipeline(
        cadence="daily",
        env={},
        watchlist={"us": [], "kr": []},
        data_root=tmp_path / "data",
        reports_root=tmp_path / "reports",
        sources_config={"disabled_ids": ["sec_edgar", "rss"]},
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )
    assert called["evaluation"] is True
    assert result["evaluation"] == 2


def test_run_pipeline_uses_typed_runtime_config_for_lang(tmp_path: Path):
    result = run_pipeline(
        cadence="daily",
        env={},
        watchlist={"us": [], "kr": []},
        data_root=tmp_path / "data",
        reports_root=tmp_path / "reports",
        sources_config={"disabled_ids": ["sec_edgar", "rss"], "lang": "ko"},
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert result["collect_failures"] is False
    assert 'lang="ko"' in (tmp_path / "reports/2026/05/31.html").read_text(encoding="utf-8")


def test_main_uses_default_env_path(tmp_path: Path, monkeypatch):
    (tmp_path / "sources.yaml").write_text("gray_enabled: true\n", encoding="utf-8")
    (tmp_path / "watchlist.yaml").write_text("us: []\nkr: []\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def _fake_run_pipeline(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "collect_failures": False,
            "insights": 0,
            "historical": 0,
            "evaluation": 0,
            "report": tmp_path / "reports/2026/05/31.html",
            "telegram_sent": False,
        }

    monkeypatch.setattr(run_module, "run_pipeline", _fake_run_pipeline)

    rc = run_module.main(["--cadence", "daily", "--config-dir", str(tmp_path)])

    assert rc == 0
    assert "env" not in captured


def test_main_does_not_mask_downstream_validation_error(tmp_path: Path, monkeypatch):
    # A ValidationError raised DOWNSTREAM (e.g. building an Insight inside the
    # pipeline) must NOT be mislabeled "invalid sources.yaml". Config is valid here,
    # so the error must propagate, not be swallowed by the config-error handler.
    (tmp_path / "sources.yaml").write_text("gray_enabled: true\n", encoding="utf-8")
    (tmp_path / "watchlist.yaml").write_text("us: []\nkr: []\n", encoding="utf-8")

    class _Demo(BaseModel):
        x: int

    def _boom(**_: object) -> dict[str, object]:
        _Demo.model_validate({"x": "not-an-int"})  # raises a real ValidationError
        return {}

    monkeypatch.setattr(run_module, "run_pipeline", _boom)
    with pytest.raises(ValidationError):
        run_module.main(["--cadence", "daily", "--config-dir", str(tmp_path)])


def test_main_reports_sec_ticker_map_build_error(tmp_path: Path, capsys):
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

    rc = run_module.main(["--cadence", "daily", "--config-dir", str(tmp_path)])

    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("[mimir] invalid sources.yaml:")
    assert "SEC ticker CIK map file is not valid JSON" in err


def test_main_reports_missing_sec_ticker_mapping(tmp_path: Path, capsys):
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
    rc = run_module.main(["--cadence", "daily", "--config-dir", str(tmp_path)])

    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("[mimir] invalid sources.yaml:")
    assert f"SEC ticker CIK map has no entry for ticker MSFT in {map_path}" in err


def test_main_does_not_mask_non_config_value_error(tmp_path: Path, monkeypatch):
    (tmp_path / "sources.yaml").write_text("gray_enabled: true\n", encoding="utf-8")
    (tmp_path / "watchlist.yaml").write_text("us: []\nkr: []\n", encoding="utf-8")

    def _boom(**_: object) -> dict[str, object]:
        raise ValueError("plugin invariant exploded")

    monkeypatch.setattr(run_module, "run_pipeline", _boom)

    with pytest.raises(ValueError, match="plugin invariant exploded"):
        run_module.main(["--cadence", "daily", "--config-dir", str(tmp_path)])
