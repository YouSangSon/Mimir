from datetime import UTC, date, datetime
from pathlib import Path

from mimir.analysis.schema import Insight, to_record
from mimir.analysis.signals.base import SignalDirection
from mimir.core.source import Market
from mimir.deliver import run_deliver
from mimir.storage.jsonl_store import JsonlStore


def _insight() -> Insight:
    return Insight(
        symbol="AAPL",
        market=Market.US,
        as_of=date(2026, 5, 31),
        direction=SignalDirection.BULLISH,
        stars=4,
        confidence=0.8,
        signals=[],
        reasons=["[price_momentum] +6%"],
    )


def test_run_deliver_writes_report_and_noops_telegram(tmp_path: Path):
    data_root = tmp_path / "data"
    reports_root = tmp_path / "reports"
    JsonlStore(root=data_root).append([to_record(_insight(), datetime(2026, 5, 31, tzinfo=UTC))])

    result = run_deliver(
        cadence="daily",
        env={},  # no telegram token -> graceful no-op
        data_root=data_root,
        reports_root=reports_root,
        as_of=date(2026, 5, 31),
    )
    assert result["insights"] == 1
    assert result["sent"] is False
    assert (reports_root / "2026/05/31.html").exists()
    assert (reports_root / "index.html").exists()


def test_run_deliver_empty_is_graceful(tmp_path: Path):
    result = run_deliver(
        cadence="daily",
        env={},
        data_root=tmp_path / "data",
        reports_root=tmp_path / "reports",
        as_of=date(2026, 5, 31),
    )
    assert result["insights"] == 0
    assert (tmp_path / "reports/2026/05/31.html").exists()
