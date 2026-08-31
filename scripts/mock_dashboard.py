"""Render the dashboard with realistic MOCK data for the README showcase.

Not part of the product — a one-off generator so the README hero image shows a
populated dashboard instead of the empty-state page. Run:

    .venv/bin/python scripts/mock_dashboard.py > /tmp/mimir_showcase/dashboard.html
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from mimir.analysis.schema import Insight
from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.source import Cadence, Dataset, Market
from mimir.doctor.report import DoctorReport, Finding, FindingKind, Severity
from mimir.evaluation.schema import BucketStat, HorizonEval
from mimir.historical.analog import HorizonStat
from mimir.historical.schema import HistoricalInsight
from mimir.manifest.manifest import RunRecord, SourceResult
from mimir.report.dashboard import build_dashboard_html

NOW = datetime(2026, 6, 14, 6, 30, tzinfo=UTC)
AS_OF = date(2026, 6, 14)


def _sig(name: str, d: SignalDirection, strength: float, reason: str) -> SignalResult:
    return SignalResult(signal=name, direction=d, strength=strength, confidence=0.8, reason=reason)


INSIGHTS = [
    Insight(
        symbol="AAPL", market=Market.US, as_of=AS_OF, direction=SignalDirection.BULLISH,
        stars=5, confidence=0.88, attention=0.7,
        signals=[_sig("price_momentum", SignalDirection.BULLISH, 0.9, "20d momentum +6.2%"),
                 _sig("filing_event", SignalDirection.BULLISH, 0.6, "8-K buyback filed")],
        reasons=["20-day momentum +6.2%", "8-K buyback authorization"],
    ),
    Insight(
        symbol="NVDA", market=Market.US, as_of=AS_OF, direction=SignalDirection.BULLISH,
        stars=4, confidence=0.81, attention=0.9,
        signals=[_sig("price_momentum", SignalDirection.BULLISH, 0.8, "breakout vs 50d high")],
        reasons=["Breakout above 50-day high", "Elevated news volume"],
    ),
    Insight(
        symbol="005930", market=Market.KR, as_of=AS_OF, direction=SignalDirection.BULLISH,
        stars=4, confidence=0.76, attention=0.5,
        signals=[_sig("macro_regime", SignalDirection.BULLISH, 0.7, "easing rate regime")],
        reasons=["Supportive macro regime (BOK hold)", "Foreign net buying"],
    ),
    Insight(
        symbol="TSLA", market=Market.US, as_of=AS_OF, direction=SignalDirection.BEARISH,
        stars=3, confidence=0.64, attention=0.8,
        signals=[_sig("price_momentum", SignalDirection.BEARISH, 0.6, "-4.1% below 20d")],
        reasons=["Below 20-day trend -4.1%", "Delivery miss headlines"],
    ),
    Insight(
        symbol="MSFT", market=Market.US, as_of=AS_OF, direction=SignalDirection.NEUTRAL,
        stars=2, confidence=0.55, attention=0.3,
        signals=[_sig("news_volume", SignalDirection.NEUTRAL, 0.4, "news in normal range")],
        reasons=["No directional edge; activity in normal range"],
    ),
]

BUCKETS = [
    BucketStat(dimension="per_signal", key="price_momentum", market=Market.US, horizons=[
        HorizonEval(horizon=1, n=42, hit_rate=0.55, mean_fwd_return=0.003, neutral_n=6),
        HorizonEval(horizon=5, n=38, hit_rate=0.61, mean_fwd_return=0.014, neutral_n=6),
        HorizonEval(horizon=20, n=31, hit_rate=0.58, mean_fwd_return=0.041, neutral_n=5)]),
    BucketStat(dimension="per_direction", key="bullish", market=Market.US, horizons=[
        HorizonEval(horizon=5, n=55, hit_rate=0.58, mean_fwd_return=0.011, neutral_n=0),
        HorizonEval(horizon=20, n=44, hit_rate=0.62, mean_fwd_return=0.037, neutral_n=0)]),
    BucketStat(dimension="per_star", key="5", market=Market.US, horizons=[
        HorizonEval(horizon=5, n=19, hit_rate=0.68, mean_fwd_return=0.022, neutral_n=0),
        HorizonEval(horizon=20, n=16, hit_rate=0.75, mean_fwd_return=0.058, neutral_n=0)]),
]

HISTORICAL = [
    HistoricalInsight(
        symbol="AAPL", market=Market.US, as_of=AS_OF, event_type="buyback_8k",
        occurrences=14, triggered_today=True,
        horizons=[HorizonStat(horizon=5, n=14, median_return=0.018, pct_positive=0.71),
                  HorizonStat(horizon=20, n=14, median_return=0.043, pct_positive=0.64)],
        examples=["2021-04-28", "2023-05-04", "2024-05-02"]),
    HistoricalInsight(
        symbol="NVDA", market=Market.US, as_of=AS_OF, event_type="50d_breakout",
        occurrences=9, triggered_today=True,
        horizons=[HorizonStat(horizon=5, n=9, median_return=0.027, pct_positive=0.67)],
        examples=["2023-05-25", "2024-02-22"]),
]

FINDINGS = [
    Finding(
        dataset=Dataset.NEWS, scope=None, kind=FindingKind.STALE, severity=Severity.WARN,
        message="'news' latest 2026-06-11 is 3 business day(s) old",
        latest_ts=date(2026, 6, 11), business_days_stale=3),
    Finding(
        dataset=Dataset.MACRO, scope="722Y001.0101000", kind=FindingKind.INFO, severity=Severity.OK,
        message="macro series '722Y001.0101000' evaluated as MONTHLY (fresh)",
        latest_ts=date(2026, 5, 31), business_days_stale=None),
]
DOCTOR = DoctorReport(checked_at=NOW, data_root="data", findings=FINDINGS)

RUN = RunRecord(ran_at=NOW, cadence=Cadence.DAILY, results=[
    SourceResult(source="sec_edgar", ok=True, fetched=18, stored=18),
    SourceResult(source="rss", ok=True, fetched=64, stored=61),
    SourceResult(source="stooq", ok=True, fetched=40, stored=40),
    SourceResult(source="ecos", ok=True, fetched=2, stored=2),
    SourceResult(source="dart", ok=True, fetched=7, stored=7),
])

print(build_dashboard_html(
    doctor_report=DOCTOR, insights=INSIGHTS, buckets=BUCKETS,
    historical=HISTORICAL, run=RUN, lang="en", now=NOW,
))
