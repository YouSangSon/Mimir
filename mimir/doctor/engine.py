from __future__ import annotations

from datetime import datetime

from mimir.core.source import Cadence, Dataset
from mimir.doctor.checks import (
    check_dataset_freshness,
    check_macro_series,
    check_short_partition,
    check_watchlist_coverage,
)
from mimir.doctor.expectations import EXPECTED_DATASETS
from mimir.doctor.report import DoctorReport, Finding, FindingKind
from mimir.storage.jsonl_store import JsonlStore


def run_doctor(
    *, store: JsonlStore, watchlist: dict[str, list[str]], now: datetime
) -> DoctorReport:
    """Read-only orchestrator: scan stored data and assemble a DoctorReport.

    Expected coverage comes from EXPECTED_DATASETS (explicit constants), never from
    build_sources() — a missing dataset must be a finding, not a skipped row (§4.1).
    `now` is injected for determinism.
    """
    findings: list[Finding] = []

    for dataset, cadence in EXPECTED_DATASETS.items():
        # Macro freshness is per-series (§4.4), so for MACRO we only assert the
        # dataset exists/non-empty here and defer staleness to check_macro_series.
        if dataset is Dataset.MACRO:
            findings.extend(_macro_presence(store, now))
        else:
            findings.extend(check_dataset_freshness(store, dataset, cadence, now))
        findings.extend(check_short_partition(store, dataset))

    findings.extend(check_macro_series(store, now))
    findings.extend(check_watchlist_coverage(store, watchlist, now))

    # NB: payload schema-drift detection was removed here — it is now enforced at
    # the storage boundary by the typed Record.payload union (INC2/A4). A drifted
    # payload can no longer be stored or read, so a dedicated shallow key-existence
    # check would never fire. See expectations.py's original A4 note.

    return DoctorReport(checked_at=now, data_root=str(store.root), findings=findings)


def _macro_presence(store: JsonlStore, now: datetime) -> list[Finding]:
    """Dataset-level missing/empty for macro (staleness is per-series, not here)."""
    findings = check_dataset_freshness(store, Dataset.MACRO, Cadence.DAILY, now)
    # Drop dataset-level STALE for macro: per-series staleness is the correct lens
    # (§3.3). Keep missing/empty.
    return [f for f in findings if f.kind is not FindingKind.STALE]
