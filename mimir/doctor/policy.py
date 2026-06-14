from __future__ import annotations

from pydantic import BaseModel

from mimir.core.source import Cadence
from mimir.doctor.report import Severity


class StalenessThreshold(BaseModel):
    """Age (in the cadence's unit) above which a dataset/series is WARN or CRITICAL.

    DAILY/HOURLY ages are measured in *business days* (§5); WEEKLY/MONTHLY in
    *calendar days* (thresholds are wide enough that holidays are absorbed).
    """

    warn_above: int
    critical_above: int


# §4.3 cadence -> allowed staleness. Conservative on purpose (false alarm < miss);
# tighten with real false-positive data. Kept as data (no magic numbers in logic).
STALENESS_POLICY: dict[Cadence, StalenessThreshold] = {
    # Partitions are day-granular (UTC midnight), so hourly is treated as daily.
    Cadence.HOURLY: StalenessThreshold(warn_above=1, critical_above=2),
    Cadence.DAILY: StalenessThreshold(warn_above=2, critical_above=4),
    Cadence.WEEKLY: StalenessThreshold(warn_above=9, critical_above=16),
    Cadence.MONTHLY: StalenessThreshold(warn_above=38, critical_above=70),
}

# Cadences whose staleness age is measured in business days (vs calendar days).
BUSINESS_DAY_CADENCES: frozenset[Cadence] = frozenset({Cadence.HOURLY, Cadence.DAILY})


def severity_for_age(cadence: Cadence, age: int) -> Severity:
    """Map a staleness age to a severity using STALENESS_POLICY."""
    threshold = STALENESS_POLICY[cadence]
    if age > threshold.critical_above:
        return Severity.CRITICAL
    if age > threshold.warn_above:
        return Severity.WARN
    return Severity.OK
