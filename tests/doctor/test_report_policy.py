from datetime import UTC, datetime

from mimir.core.source import Cadence, Dataset
from mimir.doctor.policy import severity_for_age
from mimir.doctor.report import DoctorReport, Finding, FindingKind, Severity


def _finding(severity: Severity) -> Finding:
    return Finding(
        dataset=Dataset.PRICES,
        scope=None,
        kind=FindingKind.STALE,
        severity=severity,
        message="x",
        latest_ts=None,
        business_days_stale=None,
    )


def test_worst_is_ok_when_no_findings():
    report = DoctorReport(
        checked_at=datetime(2026, 6, 13, tzinfo=UTC), data_root="data", findings=[]
    )
    assert report.worst is Severity.OK
    assert report.exit_code == 0


def test_worst_escalates_to_critical():
    report = DoctorReport(
        checked_at=datetime(2026, 6, 13, tzinfo=UTC),
        data_root="data",
        findings=[_finding(Severity.OK), _finding(Severity.WARN), _finding(Severity.CRITICAL)],
    )
    assert report.worst is Severity.CRITICAL
    assert report.exit_code == 1


def test_worst_warn_keeps_exit_zero():
    report = DoctorReport(
        checked_at=datetime(2026, 6, 13, tzinfo=UTC),
        data_root="data",
        findings=[_finding(Severity.OK), _finding(Severity.WARN)],
    )
    assert report.worst is Severity.WARN
    assert report.exit_code == 0


def test_severity_for_age_daily_thresholds():
    assert severity_for_age(Cadence.DAILY, 1) is Severity.OK
    assert severity_for_age(Cadence.DAILY, 2) is Severity.OK  # at warn boundary (>2)
    assert severity_for_age(Cadence.DAILY, 3) is Severity.WARN
    assert severity_for_age(Cadence.DAILY, 4) is Severity.WARN  # at critical boundary (>4)
    assert severity_for_age(Cadence.DAILY, 5) is Severity.CRITICAL


def test_severity_for_age_monthly_absorbs_release_lag():
    assert severity_for_age(Cadence.MONTHLY, 20) is Severity.OK  # CPI release lag
    assert severity_for_age(Cadence.MONTHLY, 71) is Severity.CRITICAL
