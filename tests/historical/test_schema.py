from datetime import UTC, date, datetime

from mimir.core.source import Dataset, Market
from mimir.historical.analog import HorizonStat
from mimir.historical.schema import DISCLAIMER, HistoricalInsight, to_record
from mimir.storage.schema import Record


def _insight() -> HistoricalInsight:
    return HistoricalInsight(
        symbol="AAPL",
        market=Market.US,
        as_of=date(2026, 5, 31),
        event_type="sharp_drop",
        occurrences=12,
        triggered_today=False,
        horizons=[HorizonStat(horizon=5, n=12, median_return=0.004, pct_positive=0.58)],
        examples=["2024-08-05: -6.1% then +3.2% (5d)"],
    )


def test_historical_insight_has_disclaimer():
    assert _insight().disclaimer == DISCLAIMER
    assert "Past performance" in DISCLAIMER


def test_to_record_builds_historical_envelope():
    rec = to_record(_insight(), captured_at=datetime(2026, 5, 31, tzinfo=UTC))
    assert rec.source == "mimir_historical"
    assert rec.dataset is Dataset.HISTORICAL
    assert rec.idempotency_key == "historical:AAPL:sharp_drop:2026-05-31"
    again = Record.model_validate_json(rec.model_dump_json())
    assert isinstance(again.payload, HistoricalInsight)
    assert again.payload.event_type == "sharp_drop"
    assert again.payload.horizons[0].horizon == 5
