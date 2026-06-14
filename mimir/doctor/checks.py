from __future__ import annotations

import statistics
from datetime import date, datetime

from mimir.core.source import Cadence, Dataset
from mimir.doctor.expectations import (
    DEFAULT_MACRO_CADENCE,
    EXPECTED_PAYLOAD_KEYS,
    MACRO_SERIES_CADENCE,
)
from mimir.doctor.freshness import staleness_age
from mimir.doctor.policy import BUSINESS_DAY_CADENCES, severity_for_age
from mimir.doctor.report import Finding, FindingKind, Severity
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

SHORT_MIN_BASELINE_PARTITIONS = 3  # need >= 3 prior samples for a stable median
SHORT_BASELINE_WINDOW = 20  # median over the most recent N prior partitions (§4.6)
SHORT_RATIO = 0.3  # latest below 30% of baseline median -> WARN (short)


def _records_on(reader: DataReader, dataset: Dataset, day: date) -> list[Record]:
    """Records in exactly one partition (since==until opens only that file)."""
    return reader.read(dataset, since=day, until=day)


def _stale_age(cadence: Cadence, latest: date, now_date: date) -> int:
    return staleness_age(cadence, latest, now_date)


def check_dataset_freshness(
    store: JsonlStore, dataset: Dataset, cadence: Cadence, now: datetime
) -> list[Finding]:
    """Missing / empty / stale for a dataset, keyed on the partition-PATH date.

    Using the path date (not max record ts) means an empty latest partition is
    reported as `empty` rather than silently falling back to an older partition.
    """
    dates = store.partition_dates(dataset)
    if not dates:
        return [
            Finding(
                dataset=dataset, scope=None, kind=FindingKind.MISSING,
                severity=Severity.CRITICAL,
                message=f"no partitions for expected dataset '{dataset.value}'",
                latest_ts=None, business_days_stale=None,
            )
        ]
    latest = dates[-1]
    reader = DataReader(store)
    if not _records_on(reader, dataset, latest):
        return [
            Finding(
                dataset=dataset, scope=None, kind=FindingKind.EMPTY,
                severity=Severity.CRITICAL,
                message=f"latest partition {latest} for '{dataset.value}' has 0 records",
                latest_ts=latest, business_days_stale=None,
            )
        ]
    age = _stale_age(cadence, latest, now.date())
    severity = severity_for_age(cadence, age)
    if severity is Severity.OK:
        return []
    unit = "business" if cadence in BUSINESS_DAY_CADENCES else "calendar"
    return [
        Finding(
            dataset=dataset, scope=None, kind=FindingKind.STALE, severity=severity,
            message=f"'{dataset.value}' latest {latest} is {age} {unit} day(s) old",
            latest_ts=latest,
            business_days_stale=age if cadence in BUSINESS_DAY_CADENCES else None,
        )
    ]


def _latest_ts_date(reader: DataReader, dataset: Dataset, symbol: str) -> date | None:
    recs = reader.read(dataset, symbol=symbol)
    if not recs:
        return None
    return max(r.ts.date() for r in recs)


def check_macro_series(store: JsonlStore, now: datetime) -> list[Finding]:
    """Per-series macro freshness (§4.4). Loops the EXPLICIT registered series for
    the freshness obligation; also reports unregistered series present in data."""
    reader = DataReader(store)
    findings: list[Finding] = []
    present: set[str] = {
        r.symbol for r in reader.read(Dataset.MACRO) if r.symbol is not None
    }
    for series, cadence in MACRO_SERIES_CADENCE.items():
        latest = _latest_ts_date(reader, Dataset.MACRO, series)
        # Registered-but-absent is NOT per-series CRITICAL: the table mixes FRED and
        # ECOS series, so requiring all of them would force every operator to hold
        # both keys. Total macro absence is caught at the dataset level (§4.1). The
        # registered table exists to apply the CORRECT cadence to series that ARE
        # present (e.g. CPIAUCSL as MONTHLY, not the DAILY floor).
        if latest is None:
            continue
        finding = _series_freshness_finding(series, cadence, latest, now.date())
        # Match the dataset-level and unregistered-series convention: only surface
        # problems. A fresh series is not a STALE finding (avoids a "stale but OK,
        # 0 days old" contradiction).
        if finding.severity is not Severity.OK:
            findings.append(finding)
    for series in sorted(present - set(MACRO_SERIES_CADENCE)):
        findings.append(
            Finding(
                dataset=Dataset.MACRO, scope=series, kind=FindingKind.INFO,
                severity=Severity.OK,
                message=(
                    f"macro series '{series}' is not in MACRO_SERIES_CADENCE; "
                    f"evaluated with default cadence {DEFAULT_MACRO_CADENCE.value}"
                ),
                latest_ts=None, business_days_stale=None,
            )
        )
        latest = _latest_ts_date(reader, Dataset.MACRO, series)
        if latest is not None:
            finding = _series_freshness_finding(
                series, DEFAULT_MACRO_CADENCE, latest, now.date()
            )
            if finding.severity is not Severity.OK:
                findings.append(finding)
    return findings


def _series_freshness_finding(
    series: str, cadence: Cadence, latest: date, now_date: date
) -> Finding:
    age = _stale_age(cadence, latest, now_date)
    severity = severity_for_age(cadence, age)
    return Finding(
        dataset=Dataset.MACRO, scope=series, kind=FindingKind.STALE, severity=severity,
        message=f"macro series '{series}' latest {latest} is {age} day(s) old "
        f"(cadence {cadence.value})",
        latest_ts=latest,
        business_days_stale=age if cadence in BUSINESS_DAY_CADENCES else None,
    )


def check_watchlist_coverage(
    store: JsonlStore, watchlist: dict[str, list[str]], now: datetime
) -> list[Finding]:
    """Per-symbol prices coverage (§4.5). PRICES is DAILY -> business-day age."""
    reader = DataReader(store)
    symbols = [s for market in ("us", "kr") for s in watchlist.get(market, [])]
    findings: list[Finding] = []
    for symbol in symbols:
        latest = _latest_ts_date(reader, Dataset.PRICES, symbol)
        if latest is None:
            findings.append(
                Finding(
                    dataset=Dataset.PRICES, scope=symbol, kind=FindingKind.MISSING,
                    severity=Severity.CRITICAL,
                    message=f"watchlist symbol '{symbol}' has never been collected in prices",
                    latest_ts=None, business_days_stale=None,
                )
            )
            continue
        age = _stale_age(Cadence.DAILY, latest, now.date())
        severity = severity_for_age(Cadence.DAILY, age)
        if severity is not Severity.OK:
            findings.append(
                Finding(
                    dataset=Dataset.PRICES, scope=symbol, kind=FindingKind.STALE,
                    severity=severity,
                    message=f"watchlist symbol '{symbol}' latest {latest} is "
                    f"{age} business day(s) old",
                    latest_ts=latest, business_days_stale=age,
                )
            )
    return findings


def check_short_partition(store: JsonlStore, dataset: Dataset) -> list[Finding]:
    """Latest partition record count vs the median of recent prior partitions (§4.6).

    Baseline excludes the latest partition and is capped to SHORT_BASELINE_WINDOW.
    Needs >= 3 prior samples; otherwise the check is skipped and an INFO finding
    records that (no silent gaps)."""
    reader = DataReader(store)
    dates = store.partition_dates(dataset)
    if not dates:
        return []
    latest = dates[-1]
    # Bound the baseline to the most recent N partitions (§4.6): keeps the scan
    # latest-relative instead of opening the whole history on long-lived datasets.
    prior = dates[:-1][-SHORT_BASELINE_WINDOW:]
    if len(prior) < SHORT_MIN_BASELINE_PARTITIONS:
        return [
            Finding(
                dataset=dataset, scope=None, kind=FindingKind.INFO, severity=Severity.OK,
                message=f"short check skipped for '{dataset.value}': only "
                f"{len(prior)} prior partition(s) (< {SHORT_MIN_BASELINE_PARTITIONS})",
                latest_ts=latest, business_days_stale=None,
            )
        ]
    latest_count = len(_records_on(reader, dataset, latest))
    if latest_count == 0:
        return []  # empty is handled by the freshness check; don't double-report
    baseline = statistics.median(len(_records_on(reader, dataset, d)) for d in prior)
    if latest_count < baseline * SHORT_RATIO:
        return [
            Finding(
                dataset=dataset, scope=None, kind=FindingKind.SHORT, severity=Severity.WARN,
                message=f"'{dataset.value}' latest partition {latest} has {latest_count} "
                f"records vs baseline median {baseline:g}",
                latest_ts=latest, business_days_stale=None,
            )
        ]
    return []


def check_payload_schema(store: JsonlStore, dataset: Dataset) -> list[Finding]:
    """Shallow key-existence on the latest partition's records (§4.7)."""
    required = EXPECTED_PAYLOAD_KEYS.get(dataset)
    if not required:
        return []
    reader = DataReader(store)
    dates = store.partition_dates(dataset)
    if not dates:
        return []
    latest = dates[-1]
    findings: list[Finding] = []
    for rec in _records_on(reader, dataset, latest):
        missing = required - rec.payload.keys()
        if missing:
            findings.append(
                Finding(
                    dataset=dataset, scope=rec.symbol, kind=FindingKind.SCHEMA,
                    severity=Severity.WARN,
                    message=f"'{dataset.value}' payload missing key(s): "
                    f"{', '.join(sorted(missing))}",
                    latest_ts=latest, business_days_stale=None,
                )
            )
    return findings
