from datetime import date

from mimir.analysis.schema import Insight
from mimir.analysis.signals.base import SignalDirection
from mimir.core.source import Market
from mimir.report.digest import build_digest


def _insight(symbol="AAPL", stars=4) -> Insight:
    return Insight(
        symbol=symbol,
        market=Market.US,
        as_of=date(2026, 5, 31),
        direction=SignalDirection.BULLISH,
        stars=stars,
        confidence=0.8,
        signals=[],
        reasons=["[price_momentum] +6%"],
    )


def test_build_digest_lists_top_insight():
    d = build_digest([_insight()], "daily", date(2026, 5, 31))
    assert "Mimir daily" in d
    assert "AAPL" in d
    assert "★★★★" in d
    assert "not financial advice" in d.lower()


def test_build_digest_empty_is_graceful():
    d = build_digest([], "daily", date(2026, 5, 31))  # default lang = en
    assert "Nothing notable" in d


def test_build_digest_korean_and_chinese():
    ko = build_digest([_insight()], "daily", date(2026, 5, 31), lang="ko")
    assert "강세" in ko and "투자 자문이 아닙니다" in ko
    zh = build_digest([_insight()], "daily", date(2026, 5, 31), lang="zh")
    assert "看涨" in zh and "不构成投资建议" in zh
