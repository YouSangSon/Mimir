from __future__ import annotations

from datetime import UTC, date, datetime

from mimir.analysis.schema import Insight
from mimir.analysis.signals.base import SignalDirection
from mimir.core.source import Cadence, Dataset, Market
from mimir.doctor.report import DoctorReport, Finding, FindingKind, Severity
from mimir.evaluation.schema import BucketStat, HorizonEval
from mimir.historical.analog import HorizonStat
from mimir.historical.schema import HistoricalInsight
from mimir.manifest.manifest import RunRecord, SourceResult
from mimir.report.dashboard import build_dashboard_html

NOW = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)


def _insight(symbol: str = "AAPL", stars: int = 4) -> Insight:
    return Insight(
        symbol=symbol,
        market=Market.US,
        as_of=date(2026, 5, 31),
        direction=SignalDirection.BULLISH,
        stars=stars,
        confidence=0.8,
        signals=[],
        reasons=["[price_momentum] +6% over 6 sessions"],
    )


def _finding(severity: Severity = Severity.WARN) -> Finding:
    return Finding(
        dataset=Dataset.INSIGHTS,
        scope="TSLA",
        kind=FindingKind.STALE,
        severity=severity,
        message="latest partition 3 business days stale",
        latest_ts=date(2026, 5, 28),
        business_days_stale=3,
    )


def _report(findings: list[Finding] | None = None) -> DoctorReport:
    return DoctorReport(
        checked_at=NOW, data_root="data", findings=findings if findings is not None else []
    )


def _bucket() -> BucketStat:
    return BucketStat(
        dimension="per_signal",
        key="momentum",
        market=Market.US,
        horizons=[
            HorizonEval(
                horizon=5, n=12, hit_rate=0.58, mean_fwd_return=0.004, neutral_n=2
            )
        ],
    )


def _historical() -> HistoricalInsight:
    return HistoricalInsight(
        symbol="MSFT",
        market=Market.US,
        as_of=date(2026, 5, 31),
        event_type="sharp_drop",
        occurrences=12,
        triggered_today=True,
        horizons=[HorizonStat(horizon=5, n=12, median_return=0.004, pct_positive=0.58)],
        examples=["2024-08-05: -6.1% then +3.2% (5d)"],
    )


def _run() -> RunRecord:
    return RunRecord(
        ran_at=NOW,
        cadence=Cadence.DAILY,
        results=[
            SourceResult(source="sec_edgar", ok=True, fetched=10, stored=10),
            SourceResult(source="fred", ok=False, error="timeout"),
        ],
    )


def _full() -> str:
    return build_dashboard_html(
        doctor_report=_report([_finding(Severity.WARN)]),
        insights=[_insight("AAPL", 4), _insight("MSFT", 5), _insight("NVDA", 2)],
        buckets=[_bucket()],
        historical=[_historical()],
        run=_run(),
        lang="en",
        now=NOW,
    )


# --- full render ---------------------------------------------------------


def test_full_render_is_valid_html_with_title_and_timestamp():
    html = _full()
    assert html.startswith("<!doctype html>")
    assert 'lang="en"' in html
    assert "Mimir" in html
    assert "2026-05-31" in html  # generated-at timestamp


def test_full_render_disclaimer_present():
    assert "not financial advice" in _full().lower()


def test_health_section_renders_finding_and_severity_color():
    html = _full()
    assert "latest partition 3 business days stale" in html
    # WARN severity color appears in the severity-colored table
    assert "#d97706" in html or "#f59e0b" in html  # amber for WARN


def test_insights_sorted_by_stars_desc():
    html = _full()
    # MSFT(5) before AAPL(4) before NVDA(2)
    assert html.index("MSFT") < html.index("AAPL") < html.index("NVDA")


def test_insights_show_stars_and_confidence():
    html = _full()
    assert "★★★★★" in html  # MSFT 5 stars
    assert "0.8" in html  # confidence


def test_scorecard_renders_bucket_with_hit_rate_and_edge():
    html = _full()
    assert "per_signal" in html
    assert "momentum" in html
    assert "58" in html  # hit-rate 0.58 -> 58%
    assert "n=12" in html


def test_historical_section_renders():
    html = _full()
    assert "sharp_drop" in html
    assert "MSFT" in html


def test_collection_status_shows_sources():
    html = _full()
    assert "sec_edgar" in html
    assert "fred" in html


def test_badges_reflect_state():
    html = _full()
    assert "1/2" in html  # 1 of 2 sources OK
    assert "3" in html  # 3 insights


# --- empty / graceful ----------------------------------------------------


def _empty() -> str:
    return build_dashboard_html(
        doctor_report=_report([]),
        insights=[],
        buckets=[],
        historical=[],
        run=None,
        lang="en",
        now=NOW,
    )


def test_empty_render_is_valid_and_graceful():
    html = _empty()
    assert html.startswith("<!doctype html>")
    assert "All clear" in html  # doctor no findings
    assert "No insights yet" in html
    assert "Insufficient sample" in html
    assert "No historical analogs yet" in html
    assert "No collection run yet" in html
    assert "not financial advice" in html.lower()


# --- escaping ------------------------------------------------------------


def test_escapes_malicious_symbol_and_reason():
    evil = Insight(
        symbol="<script>alert(1)</script>",
        market=Market.US,
        as_of=date(2026, 5, 31),
        direction=SignalDirection.BULLISH,
        stars=3,
        confidence=0.5,
        signals=[],
        reasons=["<img src=x onerror=alert(2)>"],
    )
    html = build_dashboard_html(
        doctor_report=_report([]),
        insights=[evil],
        buckets=[],
        historical=[],
        run=None,
        lang="en",
        now=NOW,
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "<img src=x onerror=alert(2)>" not in html


def test_escapes_malicious_source_name_in_collection():
    run = RunRecord(
        ran_at=NOW,
        cadence=Cadence.DAILY,
        results=[SourceResult(source="<b>evil</b>", ok=True, fetched=1, stored=1)],
    )
    html = build_dashboard_html(
        doctor_report=_report([]),
        insights=[],
        buckets=[],
        historical=[],
        run=run,
        lang="en",
        now=NOW,
    )
    assert "<b>evil</b>" not in html
    assert "&lt;b&gt;evil&lt;/b&gt;" in html


# --- i18n ----------------------------------------------------------------


def test_renders_korean_labels():
    html = build_dashboard_html(
        doctor_report=_report([]),
        insights=[],
        buckets=[],
        historical=[],
        run=None,
        lang="ko",
        now=NOW,
    )
    assert 'lang="ko"' in html
    assert "대시보드" in html
    assert "투자 자문이 아닙니다" in html


def test_renders_chinese_labels():
    html = build_dashboard_html(
        doctor_report=_report([]),
        insights=[],
        buckets=[],
        historical=[],
        run=None,
        lang="zh",
        now=NOW,
    )
    assert 'lang="zh"' in html
    assert "仪表板" in html
    assert "不构成投资建议" in html
