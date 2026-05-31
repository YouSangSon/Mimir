from datetime import UTC, datetime

from mimir.core.source import Cadence, Dataset, FetchContext, LegalStatus, Market
from mimir.sources.pykrx_source import PykrxSource


class _FakeDF:
    """Minimal stand-in for the pandas DataFrame pykrx returns."""

    def __init__(self, rows):
        self._rows = rows  # list of (index_with_strftime, row_dict)

    def iterrows(self):
        return iter(self._rows)


def _row(o, h, lo, c, v):
    return {"시가": o, "고가": h, "저가": lo, "종가": c, "거래량": v}


def _fake_ohlcv_fn(fromdate, todate, ticker):
    return _FakeDF(
        [
            (datetime(2026, 5, 28), _row(70000, 71000, 69500, 70500, 1000)),
            (datetime(2026, 5, 29), _row(70500, 72000, 70000, 71800, 1500)),
        ]
    )


def _ctx():
    return FetchContext(watchlist={"kr": ["005930"]}, now=datetime(2026, 5, 31, tzinfo=UTC))


def test_pykrx_parses_ohlcv():
    src = PykrxSource(ohlcv_fn=_fake_ohlcv_fn)
    recs = list(src.fetch(_ctx()))
    assert len(recs) == 2
    first = recs[0]
    assert first.symbol == "005930"
    assert first.idempotency_key == "pykrx:005930:2026-05-28"
    assert first.payload["close"] == 70500.0
    assert first.payload["currency"] == "KRW"
    assert first.ts == datetime(2026, 5, 28, tzinfo=UTC)


def test_pykrx_meta_is_gray():
    assert PykrxSource.meta.market is Market.KR
    assert PykrxSource.meta.dataset is Dataset.PRICES
    assert PykrxSource.meta.cadence is Cadence.DAILY
    assert PykrxSource.meta.legal_status is LegalStatus.GRAY  # scraping -> gray, toggleable
