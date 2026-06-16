from datetime import UTC, datetime

import pytest

from mimir.core.errors import FetchError
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


def test_pykrx_retries_ohlcv_failure_then_parses_records():
    calls: list[str] = []
    sleeps: list[float] = []

    def flaky_ohlcv_fn(fromdate, todate, ticker):
        calls.append(ticker)
        if len(calls) == 1:
            raise RuntimeError("temporary upstream error")
        return _fake_ohlcv_fn(fromdate, todate, ticker)

    src = PykrxSource(
        ohlcv_fn=flaky_ohlcv_fn,
        max_retries=1,
        backoff=0.25,
        sleep=sleeps.append,
    )

    recs = list(src.fetch(_ctx()))

    assert len(calls) == 2
    assert sleeps == [0.25]
    assert len(recs) == 2
    assert recs[0].idempotency_key == "pykrx:005930:2026-05-28"


def test_pykrx_raises_fetch_error_after_retry_exhaustion():
    calls: list[str] = []
    sleeps: list[float] = []

    def down_ohlcv_fn(fromdate, todate, ticker):
        calls.append(ticker)
        raise RuntimeError("naver timeout")

    src = PykrxSource(
        ohlcv_fn=down_ohlcv_fn,
        max_retries=2,
        backoff=0.1,
        sleep=sleeps.append,
    )

    with pytest.raises(FetchError) as ei:
        list(src.fetch(_ctx()))

    assert len(calls) == 3
    assert sleeps == [0.1, 0.2]
    assert "pykrx OHLCV failed after 3 attempts for 005930" in str(ei.value)
    assert "naver timeout" in str(ei.value)


class _SpyThrottle:
    def __init__(self):
        self.calls = 0

    def wait(self):
        self.calls += 1


def test_pykrx_throttles_every_ohlcv_attempt():
    calls = 0
    throttle = _SpyThrottle()

    def flaky_ohlcv_fn(fromdate, todate, ticker):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary upstream error")
        return _fake_ohlcv_fn(fromdate, todate, ticker)

    src = PykrxSource(
        ohlcv_fn=flaky_ohlcv_fn,
        throttle=throttle,
        max_retries=1,
        sleep=lambda seconds: None,
    )

    list(src.fetch(_ctx()))

    assert throttle.calls == 2


def test_pykrx_meta_is_gray():
    assert PykrxSource.meta.market is Market.KR
    assert PykrxSource.meta.dataset is Dataset.PRICES
    assert PykrxSource.meta.cadence is Cadence.DAILY
    assert PykrxSource.meta.legal_status is LegalStatus.GRAY  # scraping -> gray, toggleable
