from datetime import UTC, datetime
from pathlib import Path

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


def test_stooq_parser_does_not_need_arg_type_ignore():
    assert "type: ignore[arg-type]" not in Path("mimir/sources/stooq.py").read_text(
        encoding="utf-8"
    )


@responses.activate
def test_stooq_optional_numeric_nd_values_parse_as_none():
    responses.add(
        responses.GET,
        "https://stooq.com/q/d/l/",
        body="Date,Open,High,Low,Close,Volume\n2026-05-28,N/D,,0.5,1.5,N/D\n",
        status=200,
    )
    src = StooqSource(session=requests.Session())

    rec = next(iter(src.fetch(_ctx(["AAPL"]))))

    assert rec.payload["open"] is None
    assert rec.payload["high"] is None
    assert rec.payload["low"] == 0.5
    assert rec.payload["close"] == 1.5
    assert rec.payload["volume"] is None


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
