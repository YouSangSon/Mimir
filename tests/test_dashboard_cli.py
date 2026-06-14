from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

from mimir.analysis.schema import Insight
from mimir.analysis.schema import to_record as insight_to_record
from mimir.analysis.signals.base import SignalDirection
from mimir.core.source import Cadence, Market
from mimir.dashboard import main, run_dashboard
from mimir.evaluation.schema import BucketStat, HorizonEval
from mimir.evaluation.schema import to_record as eval_to_record
from mimir.historical.analog import HorizonStat
from mimir.historical.schema import HistoricalInsight
from mimir.historical.schema import to_record as historical_to_record
from mimir.manifest.manifest import Manifest, SourceResult
from mimir.storage.jsonl_store import JsonlStore

AS_OF = date(2026, 5, 31)
CAP = datetime(2026, 5, 31, tzinfo=UTC)
NOW = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)


def _seed(data_root: Path) -> None:
    store = JsonlStore(root=data_root)
    store.append(
        [
            insight_to_record(
                Insight(
                    symbol="AAPL",
                    market=Market.US,
                    as_of=AS_OF,
                    direction=SignalDirection.BULLISH,
                    stars=4,
                    confidence=0.8,
                    signals=[],
                    reasons=["[price_momentum] +6%"],
                ),
                CAP,
            )
        ]
    )
    store.append(
        [
            historical_to_record(
                HistoricalInsight(
                    symbol="MSFT",
                    market=Market.US,
                    as_of=AS_OF,
                    event_type="sharp_drop",
                    occurrences=12,
                    triggered_today=True,
                    horizons=[
                        HorizonStat(horizon=5, n=12, median_return=0.004, pct_positive=0.58)
                    ],
                    examples=["2024-08-05: -6.1% then +3.2% (5d)"],
                ),
                CAP,
            )
        ]
    )
    store.append(
        [
            eval_to_record(
                BucketStat(
                    dimension="per_signal",
                    key="momentum",
                    market=Market.US,
                    horizons=[
                        HorizonEval(
                            horizon=5, n=12, hit_rate=0.58, mean_fwd_return=0.004, neutral_n=2
                        )
                    ],
                ),
                AS_OF,
                CAP,
            )
        ],
        overwrite=True,
    )
    Manifest(root=data_root).write(
        now=NOW,
        cadence=Cadence.DAILY,
        results=[SourceResult(source="sec_edgar", ok=True, fetched=5, stored=5)],
    )


def _snapshot(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_run_dashboard_writes_file_with_all_sections(tmp_path: Path):
    data_root = tmp_path / "data"
    reports_root = tmp_path / "reports"
    _seed(data_root)

    out = run_dashboard(
        data_root=data_root, reports_root=reports_root, as_of=None, lang="en", now=NOW
    )

    assert out == reports_root / "dashboard.html"
    html = out.read_text(encoding="utf-8")
    assert "AAPL" in html  # insight
    assert "sharp_drop" in html  # historical
    assert "per_signal" in html  # scorecard bucket
    assert "sec_edgar" in html  # collection
    assert "not financial advice" in html.lower()


def test_run_dashboard_empty_repo_is_graceful(tmp_path: Path):
    out = run_dashboard(
        data_root=tmp_path / "data",
        reports_root=tmp_path / "reports",
        as_of=None,
        lang="en",
        now=NOW,
    )
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "No insights yet" in html
    assert "Insufficient sample" in html
    # brand-new repo: doctor reports MISSING datasets -> not "all clear"
    assert "not financial advice" in html.lower()


def test_run_dashboard_is_read_only(tmp_path: Path):
    data_root = tmp_path / "data"
    reports_root = tmp_path / "reports"
    _seed(data_root)
    before = _snapshot(data_root)

    run_dashboard(
        data_root=data_root, reports_root=reports_root, as_of=None, lang="en", now=NOW
    )

    assert _snapshot(data_root) == before  # data/ byte-unchanged


def test_main_returns_zero_and_writes(tmp_path: Path):
    data_root = tmp_path / "data"
    reports_root = tmp_path / "reports"
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    _seed(data_root)

    code = main(
        [
            "--data-root",
            str(data_root),
            "--reports-root",
            str(reports_root),
            "--config-dir",
            str(config_dir),
            "--date",
            "2026-05-31",
            "--lang",
            "ko",
        ]
    )
    assert code == 0
    html = (reports_root / "dashboard.html").read_text(encoding="utf-8")
    assert 'lang="ko"' in html
