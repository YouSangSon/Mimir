import logging
from datetime import UTC, date, datetime
from pathlib import Path

from mimir.analysis.builder import build_signals
from mimir.analysis.engine import AnalysisEngine
from mimir.analysis.schema import Insight, to_record
from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

AS_OF = date(2026, 5, 31)


def _price(symbol, day, close, volume) -> Record:
    return Record(
        source="seed",
        dataset=Dataset.PRICES,
        market=Market.US,
        symbol=symbol,
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key=f"p:{symbol}:{day}",
        payload={
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": volume,
            "currency": "USD",
            "interval": "1d",
        },
    )


class _BullishTestSignal:
    id = "bullish_test"

    def evaluate(self, symbol, market, as_of, reader):
        return SignalResult(
            signal=self.id,
            direction=SignalDirection.BULLISH,
            strength=0.75,
            confidence=0.8,
            reason=f"{symbol} passed",
        )


class _AlwaysFailSignal:
    id = "broken_signal"

    def evaluate(self, symbol, market, as_of, reader):
        raise RuntimeError(f"{symbol} boom")


class _FailOnlyAaplSignal:
    id = "fail_only_aapl"

    def evaluate(self, symbol, market, as_of, reader):
        if symbol == "AAPL":
            raise RuntimeError("AAPL boom")
        return SignalResult(
            signal=self.id,
            direction=SignalDirection.BULLISH,
            strength=0.6,
            confidence=0.7,
            reason=f"{symbol} survived",
        )


def test_engine_produces_and_stores_bullish_insight(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append(
        [
            _price("AAPL", 27, 100.0, 1000),
            _price("AAPL", 28, 104.0, 1000),
            _price("AAPL", 29, 110.0, 5000),
        ]
    )
    engine = AnalysisEngine(build_signals(), DataReader(store), store)
    insights = engine.run(
        {"us": ["AAPL"], "kr": []}, AS_OF, captured_at=datetime(2026, 5, 31, tzinfo=UTC)
    )

    assert len(insights) == 1
    assert insights[0].direction is SignalDirection.BULLISH
    # persisted to the insights dataset, idempotently
    stored = list(store.read_all(Dataset.INSIGHTS))
    assert len(stored) == 1
    assert stored[0].idempotency_key == "insight:AAPL:2026-05-31"


def test_engine_skips_symbols_with_no_signals(tmp_path: Path):
    store = JsonlStore(root=tmp_path)  # empty: no data for anyone
    engine = AnalysisEngine(build_signals(), DataReader(store), store)
    insights = engine.run({"us": ["AAPL"], "kr": []}, AS_OF)
    assert insights == []
    assert list(store.read_all(Dataset.INSIGHTS)) == []


def test_engine_skips_failed_signal_and_scores_remaining_signal(
    tmp_path: Path, caplog
):
    store = JsonlStore(root=tmp_path)
    engine = AnalysisEngine(
        [_AlwaysFailSignal(), _BullishTestSignal()],
        DataReader(store),
        store,
    )

    with caplog.at_level(logging.ERROR, logger="mimir.analysis.engine"):
        insights = engine.run({"us": ["AAPL"], "kr": []}, AS_OF)

    assert len(insights) == 1
    assert insights[0].symbol == "AAPL"
    assert [result.signal for result in insights[0].signals] == ["bullish_test"]
    assert list(store.read_all(Dataset.INSIGHTS))[0].symbol == "AAPL"
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "broken_signal" in messages
    assert "us/AAPL" in messages


def test_engine_continues_to_next_symbol_after_signal_failure(
    tmp_path: Path, caplog
):
    store = JsonlStore(root=tmp_path)
    engine = AnalysisEngine([_FailOnlyAaplSignal()], DataReader(store), store)

    with caplog.at_level(logging.ERROR, logger="mimir.analysis.engine"):
        insights = engine.run({"us": ["AAPL", "MSFT"], "kr": []}, AS_OF)

    assert [insight.symbol for insight in insights] == ["MSFT"]
    assert [record.symbol for record in store.read_all(Dataset.INSIGHTS)] == ["MSFT"]
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "fail_only_aapl" in messages
    assert "us/AAPL" in messages


def test_engine_clears_stale_insights_when_rerun_has_no_signals(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    stale = Insight(
        symbol="AAPL",
        market=Market.US,
        as_of=AS_OF,
        direction=SignalDirection.BULLISH,
        stars=4,
        confidence=0.8,
        signals=[],
        reasons=["stale"],
    )
    store.append([to_record(stale, datetime(2026, 5, 31, tzinfo=UTC))])
    engine = AnalysisEngine(build_signals(), DataReader(store), store)

    insights = engine.run({"us": ["AAPL"], "kr": []}, AS_OF)

    assert insights == []
    assert list(store.read_all(Dataset.INSIGHTS)) == []
