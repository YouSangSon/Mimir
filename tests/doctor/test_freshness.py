from datetime import date

from mimir.core.source import Cadence
from mimir.doctor.freshness import business_days_between, staleness_age


def test_business_days_same_day_is_zero():
    assert business_days_between(date(2026, 6, 8), date(2026, 6, 8)) == 0


def test_business_days_friday_to_monday_is_one():
    # Fri 2026-06-12 -> Mon 2026-06-15 : the weekend does not count (§5 headline).
    assert business_days_between(date(2026, 6, 12), date(2026, 6, 15)) == 1


def test_business_days_across_full_week():
    # Mon -> next Mon = 5 business days (Tue..Fri + Mon).
    assert business_days_between(date(2026, 6, 8), date(2026, 6, 15)) == 5


def test_business_days_within_weekend_is_zero():
    # Sat -> Sun : no weekdays in between.
    assert business_days_between(date(2026, 6, 13), date(2026, 6, 14)) == 0


def test_staleness_age_daily_uses_business_days():
    # Fri latest, Mon now -> business-day age 1 (not calendar age 3).
    assert staleness_age(Cadence.DAILY, date(2026, 6, 12), date(2026, 6, 15)) == 1


def test_staleness_age_monthly_uses_calendar_days():
    assert staleness_age(Cadence.MONTHLY, date(2026, 5, 26), date(2026, 6, 15)) == 20
