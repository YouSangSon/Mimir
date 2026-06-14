from datetime import UTC, date, datetime

from mimir.core.source import Dataset, Market
from mimir.evaluation.schema import (
    DISCLAIMER,
    EVALUATION_SOURCE,
    BucketStat,
    EvaluationReport,
    HorizonEval,
    to_record,
)
from mimir.storage.schema import Record


def _stat() -> BucketStat:
    return BucketStat(
        dimension="per_signal",
        key="momentum",
        market=Market.US,
        horizons=[
            HorizonEval(horizon=1, n=31, hit_rate=0.55, mean_fwd_return=0.003, neutral_n=4),
            HorizonEval(horizon=5, n=28, hit_rate=0.61, mean_fwd_return=0.012, neutral_n=4),
        ],
    )


def test_report_has_disclaimer_by_default():
    report = EvaluationReport(
        as_of=date(2026, 6, 13), insights_evaluated=0, buckets=[], sufficient=False
    )
    assert report.disclaimer == DISCLAIMER


def test_to_record_builds_evaluation_envelope():
    rec = to_record(_stat(), date(2026, 6, 13), captured_at=datetime(2026, 6, 13, 12, tzinfo=UTC))
    assert rec.source == EVALUATION_SOURCE
    assert rec.dataset is Dataset.EVALUATION
    assert rec.market is Market.US
    assert rec.symbol is None
    assert rec.ts == datetime(2026, 6, 13, tzinfo=UTC)
    assert rec.idempotency_key == "evaluation:per_signal:momentum:US:2026-06-13"
    assert rec.payload["dimension"] == "per_signal"
    assert rec.payload["horizons"][0]["hit_rate"] == 0.55


def test_to_record_round_trips_through_json():
    rec = to_record(_stat(), date(2026, 6, 13), captured_at=datetime(2026, 6, 13, 12, tzinfo=UTC))
    again = Record.model_validate_json(rec.model_dump_json())
    assert again.symbol is None
    assert again.idempotency_key == rec.idempotency_key
    restored = BucketStat.model_validate(again.payload)
    assert restored.key == "momentum"
    assert restored.market is Market.US
    assert restored.horizons[1].horizon == 5
