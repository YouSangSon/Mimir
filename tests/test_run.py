from datetime import UTC, datetime
from pathlib import Path

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
