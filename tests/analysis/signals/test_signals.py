import itertools
from datetime import UTC, date, datetime
from pathlib import Path

from mimir.analysis.reader import DataReader
from mimir.analysis.signals.base import SignalDirection
from mimir.analysis.signals.filing_event import FilingEventSignal
from mimir.analysis.signals.macro_regime import MacroRegimeSignal
from mimir.analysis.signals.news_volume import NewsVolumeSignal
from mimir.analysis.signals.price_momentum import PriceMomentumSignal
from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record

AS_OF = date(2026, 5, 31)
_KEY = itertools.count()


def _rec(dataset, symbol, day, payload, market=Market.US) -> Record:
    return Record(
        source="seed",
        dataset=dataset,
        market=market,
        symbol=symbol,
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key=f"{dataset.value}:{symbol}:{day}:{next(_KEY)}",
        payload=payload,
    )


def _reader(tmp_path: Path, records) -> DataReader:
    store = JsonlStore(root=tmp_path)
    store.append(records)
    return DataReader(store)


def test_price_momentum_bullish_with_volume_surge(tmp_path: Path):
    recs = [
        _rec(Dataset.PRICES, "AAPL", 27, {"close": 100.0, "volume": 1000}),
        _rec(Dataset.PRICES, "AAPL", 28, {"close": 103.0, "volume": 1000}),
        _rec(Dataset.PRICES, "AAPL", 29, {"close": 110.0, "volume": 5000}),  # +10%, vol surge
    ]
    r = PriceMomentumSignal().evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    assert r.direction is SignalDirection.BULLISH
    assert r.strength >= 0.9
    assert r.confidence == 0.85  # volume surge


def test_price_momentum_none_with_insufficient_data(tmp_path: Path):
    recs = [_rec(Dataset.PRICES, "AAPL", 29, {"close": 100.0, "volume": 1000})]
    assert PriceMomentumSignal().evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs)) is None


def test_filing_event_flags_material_8k(tmp_path: Path):
    recs = [_rec(Dataset.FILINGS, "AAPL", 29, {"form_type": "8-K", "title": "8-K"})]
    r = FilingEventSignal().evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    assert r.direction is SignalDirection.NEUTRAL
    assert "material" in r.reason


def test_filing_event_none_without_filings(tmp_path: Path):
    recs = [_rec(Dataset.PRICES, "AAPL", 29, {"close": 1.0})]
    assert FilingEventSignal().evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs)) is None


def test_news_volume_matches_symbol_in_title(tmp_path: Path):
    recs = [
        _rec(Dataset.NEWS, None, 31, {"title": "AAPL hits record", "summary": ""}),
        _rec(Dataset.NEWS, None, 31, {"title": "Unrelated", "summary": ""}),
    ]
    r = NewsVolumeSignal().evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    assert r.direction is SignalDirection.NEUTRAL


def test_news_volume_none_when_no_mentions(tmp_path: Path):
    recs = [_rec(Dataset.NEWS, None, 31, {"title": "Unrelated", "summary": ""})]
    assert NewsVolumeSignal().evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs)) is None


def test_macro_regime_rising_rate_is_bearish(tmp_path: Path):
    recs = [
        _rec(Dataset.MACRO, "FEDFUNDS", 1, {"value": 4.0}),
        _rec(Dataset.MACRO, "FEDFUNDS", 20, {"value": 4.5}),
    ]
    r = MacroRegimeSignal().evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    assert r.direction is SignalDirection.BEARISH  # rates up -> risk-off


def test_macro_regime_none_without_series(tmp_path: Path):
    recs = [_rec(Dataset.MACRO, "FEDFUNDS", 20, {"value": 4.5})]  # single point
    assert MacroRegimeSignal().evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs)) is None
