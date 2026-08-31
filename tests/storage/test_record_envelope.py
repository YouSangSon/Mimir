"""§8.5 envelope round-trip — byte-identity of the typed Record.payload union.

After phase 4 `Record.payload` is the typed `Payload` union, parsed by a
model_validator(mode="before") keyed on the envelope `dataset`. These tests
prove the on-disk format is unchanged:

  - a Record built from a dict payload serializes byte-identically to a Record
    whose payload is the parsed model (no data migration, no git churn);
  - model_validate_json(model_dump_json(rec)) is byte-stable (overwrite datasets
    don't diff every run);
  - rec.payload narrows to the correct concrete model for every dataset;
  - the to_record() helpers (which now pass a model instance, not a dict) match
    the dict path byte-for-byte (the construction that feeds insights/historical/
    evaluation partitions).
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

import pytest

from mimir.analysis.schema import Insight
from mimir.analysis.schema import to_record as insight_to_record
from mimir.core.errors import PayloadSchemaError
from mimir.core.source import Dataset, Market
from mimir.evaluation.schema import BucketStat
from mimir.evaluation.schema import to_record as bucket_to_record
from mimir.historical.schema import HistoricalInsight
from mimir.historical.schema import to_record as historical_to_record
from mimir.storage.schema import Record
from tests.core.test_payloads import (
    DART_PAYLOAD,
    ECOS_PAYLOAD,
    NEWS_PAYLOAD,
    PRICE_PAYLOAD,
    SEC_PAYLOAD,
    _evaluation_payload,
    _historical_payload,
    _insight_payload,
)

CAPTURED = datetime(2026, 5, 31, 12, tzinfo=UTC)

# (dataset, payload dict, expected concrete payload model) — all 8 adapters.
ENVELOPE_CASES = [
    (Dataset.PRICES, PRICE_PAYLOAD, "PricePayload"),
    (Dataset.MACRO, ECOS_PAYLOAD, "EcosMacroPayload"),
    (Dataset.NEWS, NEWS_PAYLOAD, "NewsPayload"),
    (Dataset.FILINGS, SEC_PAYLOAD, "SecFilingPayload"),
    (Dataset.FILINGS, DART_PAYLOAD, "DartFilingPayload"),
    (Dataset.INSIGHTS, _insight_payload(), "Insight"),
    (Dataset.HISTORICAL, _historical_payload(), "HistoricalInsight"),
    (Dataset.EVALUATION, _evaluation_payload(), "BucketStat"),
]


def _envelope(dataset: Dataset, payload: dict) -> Record:
    return Record(
        source="seed",
        dataset=dataset,
        market=Market.US,
        symbol="X",
        ts=datetime(2026, 5, 29, tzinfo=UTC),
        captured_at=CAPTURED,
        idempotency_key="k",
        payload=payload,
    )


def test_stored_fred_macro_record_is_rejected_before_analysis():
    line = json.dumps(
        {
            "schema_version": 1,
            "source": "fred",
            "dataset": "macro",
            "market": "US",
            "symbol": "DGS10",
            "ts": "2026-01-15T00:00:00Z",
            "captured_at": "2026-01-16T00:00:00Z",
            "idempotency_key": "fred:DGS10:2026-01-15",
            "payload": {
                "series_id": "DGS10",
                "value": 4.5,
                "period": "2026-01-15",
            },
        }
    )
    with pytest.raises(PayloadSchemaError):
        Record.model_validate_json(line)


@pytest.mark.parametrize("dataset, payload, model_name", ENVELOPE_CASES)
def test_envelope_payload_narrows_to_expected_model(dataset, payload, model_name):
    rec = _envelope(dataset, payload)
    assert type(rec.payload).__name__ == model_name


@pytest.mark.parametrize("dataset, payload, model_name", ENVELOPE_CASES)
def test_envelope_roundtrip_is_byte_stable(dataset, payload, model_name):
    """model_dump_json -> model_validate_json -> model_dump_json is byte-stable
    (overwrite datasets re-dump without producing a git diff)."""
    rec = _envelope(dataset, payload)
    line = rec.model_dump_json()
    again = Record.model_validate_json(line)
    assert again.model_dump_json() == line
    assert type(again.payload).__name__ == model_name


@pytest.mark.parametrize("dataset, payload, model_name", ENVELOPE_CASES)
def test_envelope_dump_embeds_payload_verbatim(dataset, payload, model_name):
    """The serialized envelope embeds exactly the source payload object — same
    keys, same order, same scalar formatting (the make-or-break invariant at the
    envelope level)."""
    rec = _envelope(dataset, payload)
    dumped = rec.model_dump(mode="json")["payload"]
    assert dumped == payload
    assert list(dumped.keys()) == list(payload.keys())


def _insight() -> Insight:
    return Insight.model_validate(_insight_payload())


def _historical() -> HistoricalInsight:
    return HistoricalInsight.model_validate(_historical_payload())


def _bucket() -> BucketStat:
    return BucketStat.model_validate(_evaluation_payload())


def test_insight_to_record_matches_dict_path_byte_for_byte():
    # to_record now passes the model; it must serialize identically to the dict path.
    via_model = insight_to_record(_insight(), captured_at=CAPTURED)
    via_dict = _envelope_for(Dataset.INSIGHTS, _insight_payload(), via_model)
    assert via_model.model_dump_json() == via_dict.model_dump_json()
    assert isinstance(via_model.payload, Insight)


def test_historical_to_record_matches_dict_path_byte_for_byte():
    via_model = historical_to_record(_historical(), captured_at=CAPTURED)
    via_dict = _envelope_for(Dataset.HISTORICAL, _historical_payload(), via_model)
    assert via_model.model_dump_json() == via_dict.model_dump_json()
    assert isinstance(via_model.payload, HistoricalInsight)


def test_evaluation_to_record_matches_dict_path_byte_for_byte():
    via_model = bucket_to_record(_bucket(), date(2026, 6, 13), captured_at=CAPTURED)
    via_dict = _envelope_for(Dataset.EVALUATION, _evaluation_payload(), via_model)
    assert via_model.model_dump_json() == via_dict.model_dump_json()
    assert isinstance(via_model.payload, BucketStat)


def _envelope_for(dataset: Dataset, payload: dict, like: Record) -> Record:
    """Build a dict-path Record sharing the model-path record's envelope fields,
    so only the payload-construction route differs."""
    return Record(
        source=like.source,
        dataset=dataset,
        market=like.market,
        symbol=like.symbol,
        ts=like.ts,
        captured_at=like.captured_at,
        idempotency_key=like.idempotency_key,
        payload=payload,
    )
