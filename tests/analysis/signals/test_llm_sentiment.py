"""LLM news-sentiment signal — fake-classifier tests (INC5 seam).

Every test injects a FakeClassifier: NO network, NO key, NO real `anthropic`
import. The default pipeline never builds the real classifier, so these tests
exercise the full seam (aggregation, gate, cap, resilience) offline.
"""

import itertools
import logging
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from mimir.analysis.signals.base import SignalDirection
from mimir.analysis.signals.llm_sentiment import (
    HeadlineVerdict,
    LlmSentimentSignal,
)
from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

AS_OF = date(2026, 5, 31)
_KEY = itertools.count()


class FakeClassifier:
    """HeadlineClassifier fixture: scripted verdicts keyed by headline text.

    Records every batch it was handed so tests can assert exactly which text was
    sent (AC8: title+summary only) and how many calls happened (AC5/AC6).
    """

    def __init__(self, scripted: dict[str, HeadlineVerdict]) -> None:
        self._scripted = scripted
        self.calls: list[list[str]] = []

    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]:
        self.calls.append(list(headlines))
        return [self._scripted[h] for h in headlines]


class BoomClassifier:
    """Raises at runtime to prove one bad LLM call returns None, not a crash."""

    def __init__(self) -> None:
        self.calls = 0

    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]:
        self.calls += 1
        raise RuntimeError("upstream API exploded")


class CardinalityMismatchClassifier:
    """Returns a scripted batch length to simulate malformed structured output."""

    def __init__(self, verdicts: list[HeadlineVerdict]) -> None:
        self._verdicts = verdicts
        self.calls: list[list[str]] = []

    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]:
        self.calls.append(list(headlines))
        return list(self._verdicts)


def _news(title: str | None, summary: str) -> dict:
    return {
        "title": title,
        "url": "https://example.com/a",
        "publisher": "SEC",
        "market": "US",
        "published_at": None,
        "summary": summary,
    }


def _rec(symbol, day, payload, market=Market.US, captured_day: int = 31) -> Record:
    return Record(
        source="seed",
        dataset=Dataset.NEWS,
        market=market,
        symbol=symbol,
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, captured_day, tzinfo=UTC),
        idempotency_key=f"news:{symbol}:{day}:{next(_KEY)}",
        payload=payload,
    )


def _reader(tmp_path: Path, records) -> DataReader:
    store = JsonlStore(root=tmp_path)
    store.append(records)
    return DataReader(store)


def _verdict(direction: SignalDirection, confidence: float) -> HeadlineVerdict:
    return HeadlineVerdict(direction=direction, confidence=confidence, rationale="r")


def test_returns_none_when_no_mentions(tmp_path: Path):
    recs = [_rec(None, 31, _news("Unrelated headline", ""))]
    sig = LlmSentimentSignal(classifier=FakeClassifier({}), max_headlines=50)
    assert sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs)) is None


def test_matches_configured_alias_without_symbol_in_headline(tmp_path: Path):
    recs = [_rec(None, 31, _news("Apple announces supplier update", ""))]
    scripted = {
        "Apple announces supplier update": _verdict(SignalDirection.BULLISH, 0.8),
    }
    fake = FakeClassifier(scripted)
    sig = LlmSentimentSignal(
        classifier=fake,
        max_headlines=50,
        aliases={"AAPL": ["Apple"]},
    )

    r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is not None
    assert r.signal == "llm_sentiment"
    assert fake.calls == [["Apple announces supplier update"]]


def test_llm_sentiment_matches_symbol_tagged_feed_without_text_mention(tmp_path: Path):
    recs = [_rec("AAPL", 31, _news("Supplier update", ""))]
    scripted = {"Supplier update": _verdict(SignalDirection.BULLISH, 0.8)}
    fake = FakeClassifier(scripted)
    sig = LlmSentimentSignal(classifier=fake, max_headlines=50)

    r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is not None
    assert r.signal == "llm_sentiment"
    assert fake.calls == [["Supplier update"]]


def test_llm_sentiment_classifies_news_captured_today_even_when_published_yesterday(
    tmp_path: Path,
):
    recs = [_rec(None, 30, _news("AAPL late update", ""), captured_day=31)]
    fake = FakeClassifier({"AAPL late update": _verdict(SignalDirection.BULLISH, 0.8)})
    sig = LlmSentimentSignal(classifier=fake, max_headlines=50)

    r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is not None
    assert r.signal == "llm_sentiment"
    assert fake.calls == [["AAPL late update"]]


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_headline_verdict_rejects_out_of_range_confidence(confidence: float):
    with pytest.raises(ValidationError):
        HeadlineVerdict(
            direction=SignalDirection.BULLISH,
            confidence=confidence,
            rationale="r",
        )


def test_aggregate_mixed_verdicts_is_bullish(tmp_path: Path):
    # 2 bullish (0.8, 0.6) + 1 bearish (0.4) -> mean_signed = (0.8+0.6-0.4)/3 = +0.333
    recs = [
        _rec(None, 31, _news("AAPL soars on earnings", "")),
        _rec(None, 31, _news("AAPL wins big contract", "")),
        _rec(None, 31, _news("AAPL faces AAPL probe", "")),
    ]
    scripted = {
        "AAPL soars on earnings": _verdict(SignalDirection.BULLISH, 0.8),
        "AAPL wins big contract": _verdict(SignalDirection.BULLISH, 0.6),
        "AAPL faces AAPL probe": _verdict(SignalDirection.BEARISH, 0.4),
    }
    sig = LlmSentimentSignal(classifier=FakeClassifier(scripted), max_headlines=50)
    r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    assert r.signal == "llm_sentiment"
    assert r.direction is SignalDirection.BULLISH
    assert r.strength == pytest.approx((0.8 + 0.6 - 0.4) / 3, abs=1e-6)
    assert "2 bull" in r.reason and "1 bear" in r.reason


def test_aggregate_bearish(tmp_path: Path):
    recs = [_rec(None, 31, _news("AAPL plunges on warning", ""))]
    scripted = {"AAPL plunges on warning": _verdict(SignalDirection.BEARISH, 0.9)}
    sig = LlmSentimentSignal(classifier=FakeClassifier(scripted), max_headlines=50)
    r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    assert r.direction is SignalDirection.BEARISH


def test_aggregate_neutral_within_eps(tmp_path: Path):
    # one bullish + one bearish at equal confidence -> mean_signed == 0 -> NEUTRAL
    recs = [
        _rec(None, 31, _news("AAPL up", "")),
        _rec(None, 31, _news("AAPL down", "")),
    ]
    scripted = {
        "AAPL up": _verdict(SignalDirection.BULLISH, 0.5),
        "AAPL down": _verdict(SignalDirection.BEARISH, 0.5),
    }
    sig = LlmSentimentSignal(classifier=FakeClassifier(scripted), max_headlines=50)
    r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    assert r.direction is SignalDirection.NEUTRAL
    assert r.strength == pytest.approx(0.0, abs=1e-6)


def test_single_headline_downweights_confidence(tmp_path: Path):
    # 1 headline -> volume_factor = 1/FULL_CONFIDENCE_VOLUME (=1/3); conf scaled down.
    recs = [_rec(None, 31, _news("AAPL strong quarter", ""))]
    scripted = {"AAPL strong quarter": _verdict(SignalDirection.BULLISH, 0.9)}
    sig = LlmSentimentSignal(classifier=FakeClassifier(scripted), max_headlines=50)
    r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    assert r.confidence == pytest.approx(0.9 * (1 / 3), abs=1e-6)


def test_three_headlines_full_confidence(tmp_path: Path):
    recs = [
        _rec(None, 31, _news(f"AAPL news {i}", "")) for i in range(3)
    ]
    scripted = {f"AAPL news {i}": _verdict(SignalDirection.BULLISH, 0.6) for i in range(3)}
    sig = LlmSentimentSignal(classifier=FakeClassifier(scripted), max_headlines=50)
    r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    # volume_factor saturates at 1.0 for >=3 headlines -> confidence == mean(conf)
    assert r.confidence == pytest.approx(0.6, abs=1e-6)


def test_signalresult_contract_fields_present(tmp_path: Path):
    recs = [_rec(None, 31, _news("AAPL update", ""))]
    scripted = {"AAPL update": _verdict(SignalDirection.BULLISH, 0.7)}
    sig = LlmSentimentSignal(classifier=FakeClassifier(scripted), max_headlines=50, weight=0.8)
    r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    assert 0.0 <= r.strength <= 1.0
    assert 0.0 <= r.confidence <= 1.0
    assert r.weight == 0.8
    assert r.reason


def test_only_title_and_summary_sent(tmp_path: Path):
    # AC8: the classifier must receive only stored title+summary, never more.
    recs = [_rec(None, 31, _news("AAPL beats", "Quarterly profit up 20%"))]
    scripted = {
        "AAPL beats\nQuarterly profit up 20%": _verdict(SignalDirection.BULLISH, 0.7),
    }
    fake = FakeClassifier(scripted)
    sig = LlmSentimentSignal(classifier=fake, max_headlines=50)
    sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert fake.calls == [["AAPL beats\nQuarterly profit up 20%"]]


def test_cap_logs_and_marks_partial(tmp_path: Path, caplog):
    # 4 mentions, cap=2 -> only 2 classified, reason notes the unclassified remainder.
    recs = [_rec(None, 31, _news(f"AAPL item {i}", "")) for i in range(4)]
    scripted = {f"AAPL item {i}": _verdict(SignalDirection.BULLISH, 0.5) for i in range(4)}
    fake = FakeClassifier(scripted)
    sig = LlmSentimentSignal(classifier=fake, max_headlines=2)
    with caplog.at_level(logging.WARNING):
        r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is not None
    # only 2 headlines were sent for classification
    assert sum(len(c) for c in fake.calls) == 2
    assert "2 unclassified" in r.reason
    assert any("cap" in m.lower() for m in caplog.messages)


def test_classifier_too_few_verdicts_returns_none(tmp_path: Path, caplog):
    recs = [
        _rec(None, 31, _news("AAPL item 1", "")),
        _rec(None, 31, _news("AAPL item 2", "")),
    ]
    classifier = CardinalityMismatchClassifier(
        [_verdict(SignalDirection.BULLISH, 0.8)]
    )
    sig = LlmSentimentSignal(classifier=classifier, max_headlines=50)

    with caplog.at_level(logging.WARNING):
        r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is None
    assert classifier.calls == [["AAPL item 1", "AAPL item 2"]]
    assert any(
        "returned 1 verdicts for 2 headlines" in message
        and "llm_sentiment" in message
        and "AAPL" in message
        for message in caplog.messages
    )


def test_classifier_too_many_verdicts_returns_none(tmp_path: Path, caplog):
    recs = [_rec(None, 31, _news("AAPL item 1", ""))]
    classifier = CardinalityMismatchClassifier(
        [
            _verdict(SignalDirection.BULLISH, 0.8),
            _verdict(SignalDirection.BEARISH, 0.4),
        ]
    )
    sig = LlmSentimentSignal(classifier=classifier, max_headlines=50)

    with caplog.at_level(logging.WARNING):
        r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is None
    assert classifier.calls == [["AAPL item 1"]]
    assert any(
        "returned 2 verdicts for 1 headlines" in message
        and "llm_sentiment" in message
        and "AAPL" in message
        for message in caplog.messages
    )


def test_runtime_classifier_error_returns_none(tmp_path: Path, caplog):
    recs = [_rec(None, 31, _news("AAPL surprise", ""))]
    boom = BoomClassifier()
    sig = LlmSentimentSignal(classifier=boom, max_headlines=50)
    with caplog.at_level(logging.ERROR):
        r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert r is None  # one bad LLM call must not crash the pipeline
    assert boom.calls == 1
    assert any("llm_sentiment" in m for m in caplog.messages)
