from __future__ import annotations

from datetime import date, timedelta

from mimir.core.source import Cadence
from mimir.doctor.policy import BUSINESS_DAY_CADENCES

WEEKDAY_FRIDAY = 4  # Monday=0 ... Friday=4; Saturday/Sunday are 5/6.


def business_days_between(start: date, end: date) -> int:
    """Count Mon-Fri days in (start, end] — start excluded, end included.

    Holidays are intentionally not modeled (§5); the cadence policy slack absorbs
    short closures. Returns 0 when end <= start.
    """
    days = 0
    d = start
    while d < end:
        d += timedelta(days=1)
        if d.weekday() <= WEEKDAY_FRIDAY:
            days += 1
    return days


def staleness_age(cadence: Cadence, latest: date, now: date) -> int:
    """Age of `latest` as of `now`, in the unit the cadence's policy expects.

    DAILY/HOURLY: business days (weekend-aware, §5). WEEKLY/MONTHLY: calendar days.
    """
    if cadence in BUSINESS_DAY_CADENCES:
        return business_days_between(latest, now)
    return (now - latest).days
