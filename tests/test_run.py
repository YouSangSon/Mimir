from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from mimir import run as run_module
from mimir.run import run_pipeline


def test_run_pipeline_chains_all_stages_no_network(tmp_path: Path):
    # Disable the keyless network sources so the full pipeline runs offline and
    # deterministically; this verifies the collect->analyze->history->deliver wiring.
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
    assert result["telegram_sent"] is False
    assert (tmp_path / "reports/2026/05/31.html").exists()
    assert (tmp_path / "reports/index.html").exists()


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
