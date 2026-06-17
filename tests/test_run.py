from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from mimir import run as run_module
from mimir.run import run_pipeline


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

    rc = run_module.main(["--cadence", "daily", "--config-dir", str(tmp_path)])

    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("[mimir] invalid sources.yaml:")
    assert "SEC ticker CIK map has no entry for ticker MSFT" in err


def test_main_does_not_mask_non_config_value_error(tmp_path: Path, monkeypatch):
    (tmp_path / "sources.yaml").write_text("gray_enabled: true\n", encoding="utf-8")
    (tmp_path / "watchlist.yaml").write_text("us: []\nkr: []\n", encoding="utf-8")

    def _boom(**_: object) -> dict[str, object]:
        raise ValueError("plugin invariant exploded")

    monkeypatch.setattr(run_module, "run_pipeline", _boom)

    with pytest.raises(ValueError, match="plugin invariant exploded"):
        run_module.main(["--cadence", "daily", "--config-dir", str(tmp_path)])
