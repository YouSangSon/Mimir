from datetime import date
from pathlib import Path

from mimir.analysis.schema import Insight
from mimir.analysis.signals.base import SignalDirection
from mimir.core.source import Market
from mimir.evaluation.schema import BucketStat, HorizonEval
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


def _bucket(key: str = "price_momentum") -> BucketStat:
    return BucketStat(
        dimension="per_signal",
        key=key,
        market=Market.US,
        horizons=[
            HorizonEval(horizon=5, n=12, hit_rate=0.58, mean_fwd_return=0.004, neutral_n=2)
        ],
    )


def test_build_report_html_contains_insight():
    h = build_report_html([_insight()], date(2026, 5, 31))  # default lang = en
    assert "AAPL" in h
    assert "Bullish" in h
    assert "★★★★☆" in h
    assert "not financial advice" in h.lower()


def test_build_report_html_empty_is_graceful():
    h = build_report_html([], date(2026, 5, 31))
    assert "Nothing notable" in h


def test_build_report_html_korean():
    h = build_report_html([_insight()], date(2026, 5, 31), lang="ko")
    assert 'lang="ko"' in h
    assert "강세" in h  # Bullish
    assert "투자 자문이 아닙니다" in h  # disclaimer


def test_build_report_html_chinese():
    h = build_report_html([_insight()], date(2026, 5, 31), lang="zh")
    assert 'lang="zh"' in h
    assert "看涨" in h  # Bullish
    assert "不构成投资建议" in h  # disclaimer


def test_build_report_html_sanitizes_lang_attribute():
    h = build_report_html(
        [_insight()],
        date(2026, 5, 31),
        lang='en" onmouseover="alert(1)',
    )
    assert 'lang="en"' in h
    assert "onmouseover" not in h


def test_build_report_html_empty_korean():
    h = build_report_html([], date(2026, 5, 31), lang="ko")
    assert "특이사항 없음" in h


def test_build_report_html_contains_evaluation_scorecard():
    h = build_report_html([_insight()], date(2026, 5, 31), evaluation=[_bucket()])
    assert "Signal scorecard" in h
    assert "per_signal" in h
    assert "price_momentum" in h
    assert "5d: hit 58%" in h
    assert "edge +0.4%" in h
    assert "n=12" in h


def test_build_report_html_evaluation_scorecard_korean():
    h = build_report_html([_insight()], date(2026, 5, 31), evaluation=[_bucket()], lang="ko")
    assert "시그널 성적표" in h
    assert "5일: 적중 58%" in h


def test_build_report_html_escapes_evaluation_bucket_key():
    h = build_report_html(
        [_insight()],
        date(2026, 5, 31),
        evaluation=[_bucket("<script>alert(1)</script>")],
    )
    assert "<script>alert(1)</script>" not in h
    assert "&lt;script&gt;" in h


def test_build_report_html_escapes_untrusted_data():
    # A malicious filing name / news title must not inject markup into the report.
    evil = _insight()
    evil.reasons = ["<script>alert(1)</script>"]
    h = build_report_html([evil], date(2026, 5, 31))
    assert "<script>alert(1)</script>" not in h
    assert "&lt;script&gt;" in h


def test_save_report_and_rebuild_index(tmp_path: Path):
    save_report(build_report_html([_insight()], date(2026, 5, 31)), date(2026, 5, 31), tmp_path)
    assert (tmp_path / "2026/05/31.html").exists()
    index = rebuild_index(tmp_path)
    assert index.exists()
    assert "2026/05/31.html" in index.read_text()


def test_rebuild_index_sanitizes_lang_attribute(tmp_path: Path):
    index = rebuild_index(tmp_path, lang='en" onmouseover="alert(1)')
    html_doc = index.read_text()
    assert 'lang="en"' in html_doc
    assert "onmouseover" not in html_doc
