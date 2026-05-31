from datetime import UTC, datetime

import pytest
import requests
import responses

from mimir.core.errors import FetchError
from mimir.core.source import Cadence, Dataset, FetchContext, LegalStatus, Market
from mimir.sources.stooq import StooqSource

CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2026-05-28,1.0,2.0,0.5,1.5,100\n"
    "2026-05-29,1.5,2.5,1.0,2.0,200\n"
)


def _ctx(symbols):
    return FetchContext(watchlist={"us": symbols}, now=datetime(2026, 5, 31, tzinfo=UTC))


@responses.activate
def test_stooq_parses_daily_bars():
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)
    src = StooqSource(session=requests.Session())
    recs = list(src.fetch(_ctx(["AAPL"])))
    assert len(recs) == 2
    first = recs[0]
    assert first.symbol == "AAPL"
    assert first.idempotency_key == "stooq:AAPL:2026-05-28"
    assert first.payload["close"] == 1.5
    assert first.ts == datetime(2026, 5, 28, tzinfo=UTC)


def test_stooq_meta_is_official_daily_prices():
    assert StooqSource.meta.market is Market.US
    assert StooqSource.meta.dataset is Dataset.PRICES
    assert StooqSource.meta.cadence is Cadence.DAILY
    assert StooqSource.meta.legal_status is LegalStatus.OFFICIAL
    assert StooqSource.meta.requires_secret == "STOOQ_API_KEY"


@responses.activate
def test_stooq_raises_on_non_csv_response():
    # When the apikey is missing/invalid, Stooq returns an instructional message,
    # not CSV. That must surface as a failure, not a silent zero-row success.
    responses.add(
        responses.GET,
        "https://stooq.com/q/d/l/",
        body="Get your apikey:\n\n1. Open ...",
        status=200,
    )
    src = StooqSource(session=requests.Session())
    with pytest.raises(FetchError):
        list(src.fetch(_ctx(["AAPL"])))
