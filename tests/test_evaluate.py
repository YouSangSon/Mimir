from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from mimir.analysis.schema import Insight
from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.source import Dataset, Market
from mimir.evaluate import main, run_evaluate
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record

CAPTURED = datetime(2026, 5, 31, tzinfo=UTC)


def _seed(store: JsonlStore, n_insights: int) -> None:
    closes = [100.0, 110.0, 121.0, 133.1, 146.41, 161.05, 177.16, 194.87]
    store.append(
        [
            Record(
                source="seed",
                dataset=Dataset.PRICES,
                market=Market.US,
                symbol="AAPL",
                ts=datetime(2026, 5, d + 1, tzinfo=UTC),
                captured_at=CAPTURED,
                idempotency_key=f"p:AAPL:{d}",
                payload={"close": c, "volume": 1000},
            )
            for d, c in enumerate(closes)
        ]
    )
    sig = [
        SignalResult(
            signal="momentum",
            direction=SignalDirection.BULLISH,
            strength=0.5,
            confidence=0.7,
            reason="r",
        )
    ]
    store.append(
        [
            Record(
                source="mimir_analysis",
                dataset=Dataset.INSIGHTS,
                market=Market.US,
                symbol="AAPL",
                ts=datetime(2026, 5, d, tzinfo=UTC),
                captured_at=CAPTURED,
                idempotency_key=f"insight:AAPL:2026-05-{d:02d}",
                payload=Insight(
                    symbol="AAPL",
                    market=Market.US,
                    as_of=date(2026, 5, d),
                    direction=SignalDirection.BULLISH,
                    stars=4,
                    confidence=0.7,
                    signals=sig,
                    reasons=["r"],
                ).model_dump(mode="json"),
            )
            for d in range(1, n_insights + 1)
        ]
    )


def test_run_evaluate_writes_partition(tmp_path: Path):
    data_root = tmp_path / "data"
    store = JsonlStore(root=data_root)
    _seed(store, 6)
    report = run_evaluate(
        data_root=data_root, as_of=date(2026, 5, 31), captured_at=CAPTURED
    )
    assert report.sufficient is True
    assert (data_root / "evaluation/2026/05/31.jsonl").exists()


def test_main_prints_buckets(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    data_root = tmp_path / "data"
    _seed(JsonlStore(root=data_root), 6)
    rc = main(["--date", "2026-05-31", "--data-root", str(data_root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "bucket" in out.lower()


def test_main_reports_insufficient_sample(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    data_root = tmp_path / "data"
    _seed(JsonlStore(root=data_root), 2)  # cold start
    rc = main(["--date", "2026-05-31", "--data-root", str(data_root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "insufficient sample" in out.lower()
