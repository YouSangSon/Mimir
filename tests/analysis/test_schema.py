from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from mimir.analysis.schema import DISCLAIMER, Insight, to_record
from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.source import Dataset, Market
from mimir.storage.schema import Record


def _insight() -> Insight:
    return Insight(
        symbol="AAPL",
        market=Market.US,
        as_of=date(2026, 5, 31),
        direction=SignalDirection.BULLISH,
        stars=4,
        confidence=0.78,
        signals=[
            SignalResult(
                signal="price_momentum",
                direction=SignalDirection.BULLISH,
                strength=0.6,
                confidence=0.85,
                reason="+6% over 6 sessions",
            )
        ],
        reasons=["[price_momentum] +6% over 6 sessions"],
    )


def test_insight_has_disclaimer_by_default():
    assert _insight().disclaimer == DISCLAIMER


def test_to_record_builds_insights_envelope():
    rec = to_record(_insight(), captured_at=datetime(2026, 5, 31, 12, 0, tzinfo=UTC))
    assert rec.source == "mimir_analysis"
    assert rec.dataset is Dataset.INSIGHTS
    assert rec.symbol == "AAPL"
    assert rec.idempotency_key == "insight:AAPL:2026-05-31"
    assert rec.ts == datetime(2026, 5, 31, tzinfo=UTC)
    assert isinstance(rec.payload, Insight)
    assert rec.payload.direction == "bullish"
    assert rec.payload.stars == 4
    # round-trips through JSON like any other Record
    again = Record.model_validate_json(rec.model_dump_json())
    assert isinstance(again.payload, Insight)
    assert again.payload.as_of == date(2026, 5, 31)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("strength", -0.1),
        ("strength", 1.1),
        ("confidence", -0.1),
        ("confidence", 1.1),
    ],
)
def test_signal_result_rejects_out_of_range_scores(field: str, value: float):
    data = {
        "signal": "demo",
        "direction": SignalDirection.BULLISH,
        "strength": 0.5,
        "confidence": 0.5,
        "reason": "r",
    }
    data[field] = value
    with pytest.raises(ValidationError):
        SignalResult.model_validate(data)
