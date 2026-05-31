from datetime import date
from pathlib import Path

from mimir.analysis.schema import Insight
from mimir.analysis.signals.base import SignalDirection
from mimir.core.source import Market
from mimir.report.daily_report import build_report_html, rebuild_index, save_report


def _insight(symbol="AAPL", stars=4, direction=SignalDirection.BULLISH) -> Insight:
    return Insight(
        symbol=symbol,
        market=Market.US,
        as_of=date(2026, 5, 31),
        direction=direction,
        stars=stars,
        confidence=0.8,
        signals=[],
        reasons=["[price_momentum] +6% over 6 sessions"],
    )


def test_build_report_html_contains_insight():
    h = build_report_html([_insight()], date(2026, 5, 31))
    assert "AAPL" in h
    assert "강세" in h
    assert "★★★★☆" in h
    assert "not financial advice" in h.lower()


def test_build_report_html_empty_is_graceful():
    h = build_report_html([], date(2026, 5, 31))
    assert "특이사항 없음" in h


def test_save_report_and_rebuild_index(tmp_path: Path):
    save_report(build_report_html([_insight()], date(2026, 5, 31)), date(2026, 5, 31), tmp_path)
    assert (tmp_path / "2026/05/31.html").exists()
    index = rebuild_index(tmp_path)
    assert index.exists()
    assert "2026/05/31.html" in index.read_text()
