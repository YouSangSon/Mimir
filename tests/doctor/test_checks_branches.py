"""Branch coverage for stale (not just missing) symbol/series paths."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from mimir.core.source import Dataset
from mimir.doctor.checks import check_macro_series, check_watchlist_coverage
from mimir.doctor.report import FindingKind, Severity
from mimir.storage.jsonl_store import JsonlStore
from tests.doctor.conftest import make_record, write_partition

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


def test_watchlist_symbol_present_but_stale_is_flagged(tmp_path: Path):
    # AAPL has prices, but latest is 6 business days ago (Fri 6/5 -> Mon 6/15).
    stale_day = date(2026, 6, 5)
    write_partition(
        tmp_path, Dataset.PRICES, stale_day,
        [make_record(Dataset.PRICES, stale_day, symbol="AAPL", key="a")],
    )
    store = JsonlStore(root=tmp_path)
    findings = check_watchlist_coverage(store, {"us": ["AAPL"], "kr": []}, NOW)
    stale = [f for f in findings if f.scope == "AAPL" and f.kind is FindingKind.STALE]
    assert stale and stale[0].severity is Severity.CRITICAL


def test_unregistered_macro_series_stale_emits_finding(tmp_path: Path):
    # Unregistered series, MONTHLY fallback, latest 80 days ago -> CRITICAL.
    old_day = date(2026, 3, 27)  # 80 calendar days before 6/15
    write_partition(
        tmp_path, Dataset.MACRO, old_day,
        [make_record(Dataset.MACRO, old_day, symbol="ZZZ", key="z")],
    )
    store = JsonlStore(root=tmp_path)
    findings = check_macro_series(store, NOW)
    stale = [f for f in findings if f.scope == "ZZZ" and f.kind is FindingKind.STALE]
    assert stale and stale[0].severity is Severity.CRITICAL
    # And the presence INFO is still emitted.
    assert [f for f in findings if f.scope == "ZZZ" and f.kind is FindingKind.INFO]
