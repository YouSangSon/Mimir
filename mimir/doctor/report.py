from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel

from mimir.core.source import Dataset

_SEVERITY_RANK: dict[str, int] = {"ok": 0, "warn": 1, "critical": 2}


class Severity(StrEnum):
    OK = "ok"
    WARN = "warn"
    CRITICAL = "critical"


class FindingKind(StrEnum):
    STALE = "stale"  # latest partition older than cadence allows
    MISSING = "missing"  # expected dataset/symbol has no data at all
    EMPTY = "empty"  # partition exists but holds 0 records
    SHORT = "short"  # record count abnormally low vs baseline
    SCHEMA = "schema"  # required payload key missing
    INFO = "info"  # skipped check / sync hint (no silent gaps)


class Finding(BaseModel):
    dataset: Dataset
    scope: str | None  # symbol/series; None for dataset-wide
    kind: FindingKind
    severity: Severity
    message: str  # human-readable one-liner (language-neutral facts)
    latest_ts: date | None  # newest data date (None if absent)
    business_days_stale: int | None


class DoctorReport(BaseModel):
    checked_at: datetime
    data_root: str
    findings: list[Finding]

    @property
    def worst(self) -> Severity:
        worst = Severity.OK
        for f in self.findings:
            if _SEVERITY_RANK[f.severity] > _SEVERITY_RANK[worst]:
                worst = f.severity
        return worst

    @property
    def exit_code(self) -> int:
        return 1 if self.worst is Severity.CRITICAL else 0
