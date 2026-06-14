"""§8.1 acceptance matrix — run_doctor end-to-end against synthetic trees.

Every case injects a fixed `now`; no test touches the network or real `data/`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from mimir.core.source import Dataset
from mimir.doctor.engine import run_doctor
from mimir.doctor.report import DoctorReport, FindingKind, Severity
from mimir.storage.jsonl_store import JsonlStore
from tests.doctor.conftest import make_record, write_fresh_tree, write_partition

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)  # a Monday
EMPTY_WATCHLIST: dict[str, list[str]] = {"us": [], "kr": []}


def _kinds(report: DoctorReport, dataset: Dataset, kind: FindingKind) -> list:
    return [f for f in report.findings if f.dataset is dataset and f.kind is kind]


def test_fresh_tree_all_ok_exit_zero(tmp_path: Path):
    store = write_fresh_tree(tmp_path, NOW)
    report = run_doctor(store=store, watchlist=EMPTY_WATCHLIST, now=NOW)
    assert report.worst is Severity.OK
    assert report.exit_code == 0


def test_stale_prices_is_critical_exit_one(tmp_path: Path):
    store = write_fresh_tree(tmp_path, NOW)
    # Remove all prices partitions, re-write one latest = 6 business days ago.
    import shutil

    shutil.rmtree(tmp_path / "prices")
    stale_day = date(2026, 6, 5)  # Fri; 6 business days before Mon 6/15
    write_partition(
        tmp_path, Dataset.PRICES, stale_day,
        [make_record(Dataset.PRICES, stale_day, symbol="S0", key="p-stale")],
    )
    report = run_doctor(store=store, watchlist=EMPTY_WATCHLIST, now=NOW)
    stale = _kinds(report, Dataset.PRICES, FindingKind.STALE)
    assert stale and stale[0].severity is Severity.CRITICAL
    assert report.exit_code == 1


def test_missing_macro_is_critical(tmp_path: Path):
    store = write_fresh_tree(tmp_path, NOW)
    import shutil

    shutil.rmtree(tmp_path / "macro")
    report = run_doctor(store=store, watchlist=EMPTY_WATCHLIST, now=NOW)
    missing = _kinds(report, Dataset.MACRO, FindingKind.MISSING)
    assert missing and missing[0].severity is Severity.CRITICAL
    assert report.exit_code == 1


def test_empty_latest_prices_is_critical(tmp_path: Path):
    store = write_fresh_tree(tmp_path, NOW)
    # Overwrite the latest prices partition with zero records.
    write_partition(tmp_path, Dataset.PRICES, NOW.date(), [])
    report = run_doctor(store=store, watchlist=EMPTY_WATCHLIST, now=NOW)
    empty = _kinds(report, Dataset.PRICES, FindingKind.EMPTY)
    assert empty and empty[0].severity is Severity.CRITICAL
    assert report.exit_code == 1


def test_short_latest_prices_is_warn(tmp_path: Path):
    store = write_fresh_tree(tmp_path, NOW)
    # Prior partitions have median ~40; latest has 3 -> below 30%.
    import shutil

    shutil.rmtree(tmp_path / "prices")
    today = NOW.date()
    for offset in (4, 3, 2, 1):
        day = date.fromordinal(today.toordinal() - offset)
        write_partition(
            tmp_path, Dataset.PRICES, day,
            [make_record(Dataset.PRICES, day, symbol=f"S{i}", key=f"p-{day}-{i}")
             for i in range(40)],
        )
    write_partition(
        tmp_path, Dataset.PRICES, today,
        [make_record(Dataset.PRICES, today, symbol=f"S{i}", key=f"p-{today}-{i}")
         for i in range(3)],
    )
    report = run_doctor(store=store, watchlist=EMPTY_WATCHLIST, now=NOW)
    short = _kinds(report, Dataset.PRICES, FindingKind.SHORT)
    assert short and short[0].severity is Severity.WARN


def test_short_skipped_with_info_when_too_few_partitions(tmp_path: Path):
    store = write_fresh_tree(tmp_path, NOW)
    import shutil

    shutil.rmtree(tmp_path / "prices")
    today = NOW.date()
    # Only 2 partitions total -> fewer than 3 baseline samples -> skip + INFO.
    for offset in (1, 0):
        day = date.fromordinal(today.toordinal() - offset)
        write_partition(
            tmp_path, Dataset.PRICES, day,
            [make_record(Dataset.PRICES, day, symbol="S0", key=f"p-{day}")],
        )
    report = run_doctor(store=store, watchlist=EMPTY_WATCHLIST, now=NOW)
    info = [f for f in _kinds(report, Dataset.PRICES, FindingKind.INFO)
            if "short" in f.message.lower()]
    assert info
    assert not _kinds(report, Dataset.PRICES, FindingKind.SHORT)


def test_weekend_boundary_no_false_alarm(tmp_path: Path):
    store = write_fresh_tree(tmp_path, NOW)
    import shutil

    shutil.rmtree(tmp_path / "prices")
    friday = date(2026, 6, 12)  # latest = Friday, now = Monday 6/15
    for off in (0, 1, 2):  # a few partitions so short-check has a baseline
        day = date.fromordinal(friday.toordinal() - off)
        write_partition(
            tmp_path, Dataset.PRICES, day,
            [make_record(Dataset.PRICES, day, symbol=f"S{i}", key=f"p-{day}-{i}")
             for i in range(10)],
        )
    report = run_doctor(store=store, watchlist=EMPTY_WATCHLIST, now=NOW)
    assert not _kinds(report, Dataset.PRICES, FindingKind.STALE)


def test_monthly_macro_series_not_false_alarmed(tmp_path: Path):
    store = write_fresh_tree(tmp_path, NOW)
    # CPIAUCSL (MONTHLY-registered) latest 20 days ago must be OK, not CRITICAL,
    # even though the macro dataset floor is DAILY.
    cpi_day = date(2026, 5, 26)  # 20 calendar days before 6/15
    write_partition(
        tmp_path, Dataset.MACRO, cpi_day,
        [make_record(Dataset.MACRO, cpi_day, symbol="CPIAUCSL", key="cpi")],
    )
    report = run_doctor(store=store, watchlist=EMPTY_WATCHLIST, now=NOW)
    cpi = [f for f in report.findings if f.scope == "CPIAUCSL"]
    assert all(f.severity is Severity.OK for f in cpi)
    assert not [f for f in cpi if f.severity is Severity.CRITICAL]


def test_unregistered_macro_series_reported_info_and_loose_cadence(tmp_path: Path):
    store = write_fresh_tree(tmp_path, NOW)
    # A series not in MACRO_SERIES_CADENCE, latest 20 days ago.
    day = date(2026, 5, 26)
    write_partition(
        tmp_path, Dataset.MACRO, day,
        [make_record(Dataset.MACRO, day, symbol="NEWSERIES", key="ns")],
    )
    report = run_doctor(store=store, watchlist=EMPTY_WATCHLIST, now=NOW)
    info = [f for f in report.findings
            if f.scope == "NEWSERIES" and f.kind is FindingKind.INFO]
    assert info  # presence reported as a sync hint
    # MONTHLY fallback -> 20 days is OK, not CRITICAL.
    assert not [f for f in report.findings
                if f.scope == "NEWSERIES" and f.severity is Severity.CRITICAL]


def test_watchlist_gap_is_critical_missing(tmp_path: Path):
    store = write_fresh_tree(tmp_path, NOW)
    report = run_doctor(store=store, watchlist={"us": ["XYZ"], "kr": []}, now=NOW)
    gap = [f for f in report.findings
           if f.dataset is Dataset.PRICES and f.scope == "XYZ"
           and f.kind is FindingKind.MISSING]
    assert gap and gap[0].severity is Severity.CRITICAL
    assert report.exit_code == 1


def test_fred_key_absent_still_flags_missing_macro(tmp_path: Path):
    # Regression: the expected set comes from EXPECTED_DATASETS, not build_sources().
    # No macro data at all (as if FRED key were absent) must still be CRITICAL missing.
    store = JsonlStore(root=tmp_path)
    report = run_doctor(store=store, watchlist=EMPTY_WATCHLIST, now=NOW)
    missing = _kinds(report, Dataset.MACRO, FindingKind.MISSING)
    assert missing and missing[0].severity is Severity.CRITICAL


def test_read_only_data_unchanged(tmp_path: Path):
    import hashlib

    store = write_fresh_tree(tmp_path, NOW)

    def snapshot() -> dict[str, str]:
        out: dict[str, str] = {}
        for p in sorted((tmp_path).rglob("*.jsonl")):
            out[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        return out

    before = snapshot()
    run_doctor(store=store, watchlist={"us": ["XYZ"], "kr": []}, now=NOW)
    after = snapshot()
    assert before == after
