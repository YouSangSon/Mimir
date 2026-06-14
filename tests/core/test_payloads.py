"""Phase 1: typed payload models, dispatch, and byte-identity golden tests.

The make-or-break invariant (spec §3.1) reduces to: the typed model's
serialization equals the source dict's serialization, byte-for-byte. Because
`Record.payload` is still `dict[str, Any]` in phases 1-3, the golden assertion
here is at the *payload* level (§8.1): the baseline is generated from the dict
path (observed, not hand-written), and the typed path must match it.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from mimir.analysis.schema import Insight
from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.errors import PayloadSchemaError
from mimir.core.payloads import (
    DartFilingPayload,
    EcosMacroPayload,
    FredMacroPayload,
    NewsPayload,
    PricePayload,
    SecFilingPayload,
    parse_payload,
)
from mimir.core.source import Dataset, Market
from mimir.evaluation.schema import BucketStat, HorizonEval
from mimir.historical.analog import HorizonStat
from mimir.historical.schema import HistoricalInsight

# --- Exact payload literals per adapter (insertion order matters) ---

PRICE_PAYLOAD = {
    "open": 195.0,
    "high": 197.5,
    "low": 194.1,
    "close": 196.3,
    "volume": 1234567.0,
    "currency": "USD",
    "interval": "1d",
}
FRED_PAYLOAD = {"series_id": "DGS10", "value": 4.5, "period": "2026-01-15"}
ECOS_PAYLOAD = {
    "stat_code": "722Y001",
    "item_code": "0101000",
    "item_name": None,  # ECOS legitimately yields null here -> key must survive
    "value": 3.5,
    "unit": None,
    "time": "202601",
}
NEWS_PAYLOAD = {
    "title": None,  # entry.get("title") can be None
    "url": "https://www.sec.gov/news/pr-1",
    "publisher": "SEC",
    "market": "US",
    "published_at": None,
    "summary": "",  # rss.py always inserts a string, never None
}
SEC_PAYLOAD = {
    "form_type": "8-K",
    "title": "8-K",
    "accession": "0000320193-26-000001",
    "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/d.htm",
    "filed_at": "2026-01-15",
}
DART_PAYLOAD = {
    "form_type": "주요사항보고서",
    "title": "주요사항보고서",
    "corp_name": "삼성전자",
    "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260115000001",
    "filed_at": "20260115",
    "flr_nm": "삼성전자",
}


def _insight_payload() -> dict[str, Any]:
    insight = Insight(
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
    return insight.model_dump(mode="json")


def _historical_payload() -> dict[str, Any]:
    hist = HistoricalInsight(
        symbol="AAPL",
        market=Market.US,
        as_of=date(2026, 5, 31),
        event_type="filing_8k",
        occurrences=12,
        triggered_today=True,
        horizons=[HorizonStat(horizon=5, n=12, median_return=0.01, pct_positive=0.58)],
        examples=["2024-03-01"],
    )
    return hist.model_dump(mode="json")


def _evaluation_payload() -> dict[str, Any]:
    stat = BucketStat(
        dimension="per_signal",
        key="momentum",
        market=Market.US,
        horizons=[
            HorizonEval(horizon=1, n=31, hit_rate=0.55, mean_fwd_return=0.003, neutral_n=4),
        ],
    )
    return stat.model_dump(mode="json")


# (dataset, payload dict, expected concrete model type)
GOLDEN_CASES = [
    (Dataset.PRICES, PRICE_PAYLOAD, PricePayload),
    (Dataset.MACRO, FRED_PAYLOAD, FredMacroPayload),
    (Dataset.MACRO, ECOS_PAYLOAD, EcosMacroPayload),
    (Dataset.NEWS, NEWS_PAYLOAD, NewsPayload),
    (Dataset.FILINGS, SEC_PAYLOAD, SecFilingPayload),
    (Dataset.FILINGS, DART_PAYLOAD, DartFilingPayload),
    (Dataset.INSIGHTS, _insight_payload(), Insight),
    (Dataset.HISTORICAL, _historical_payload(), HistoricalInsight),
    (Dataset.EVALUATION, _evaluation_payload(), BucketStat),
]


@pytest.mark.parametrize("dataset, payload, model_type", GOLDEN_CASES)
def test_parse_payload_returns_correct_model_type(dataset, payload, model_type):
    parsed = parse_payload(dataset, payload)
    assert isinstance(parsed, model_type)


@pytest.mark.parametrize("dataset, payload, model_type", GOLDEN_CASES)
def test_golden_roundtrip_is_byte_identical(dataset, payload, model_type):
    """Baseline from the dict path; typed path must match byte-for-byte."""
    parsed = parse_payload(dataset, payload)
    # condition 1+2: same keys, same order, same values
    assert parsed.model_dump(mode="json") == payload
    assert list(parsed.model_dump(mode="json").keys()) == list(payload.keys())
    # byte-identity: pydantic compact encoder == the dict's compact JSON
    baseline = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    assert parsed.model_dump_json() == baseline


# --- §8.2 drift blocking ---


def test_extra_key_raises():
    with pytest.raises(PayloadSchemaError):
        parse_payload(Dataset.MACRO, {**FRED_PAYLOAD, "extra": 1})


def test_missing_key_raises():
    bad = {k: v for k, v in FRED_PAYLOAD.items() if k != "value"}
    with pytest.raises(PayloadSchemaError):
        parse_payload(Dataset.MACRO, bad)


def test_wrong_type_raises():
    with pytest.raises(PayloadSchemaError):
        parse_payload(Dataset.MACRO, {**FRED_PAYLOAD, "value": "not-a-number"})


def test_date_looking_string_stays_str():
    parsed = parse_payload(Dataset.MACRO, FRED_PAYLOAD)
    assert isinstance(parsed, FredMacroPayload)
    assert isinstance(parsed.period, str)
    assert parsed.period == "2026-01-15"


def test_unknown_dataset_for_payload_raises():
    # a price dict cannot validate as any macro model
    with pytest.raises(PayloadSchemaError):
        parse_payload(Dataset.MACRO, PRICE_PAYLOAD)


# --- §8.3 source-branch resolution (structural via extra="forbid") ---


def test_fred_dict_resolves_to_fred_model():
    assert isinstance(parse_payload(Dataset.MACRO, FRED_PAYLOAD), FredMacroPayload)


def test_ecos_dict_resolves_to_ecos_model():
    assert isinstance(parse_payload(Dataset.MACRO, ECOS_PAYLOAD), EcosMacroPayload)


def test_sec_dict_resolves_to_sec_model():
    assert isinstance(parse_payload(Dataset.FILINGS, SEC_PAYLOAD), SecFilingPayload)


def test_dart_dict_resolves_to_dart_model():
    assert isinstance(parse_payload(Dataset.FILINGS, DART_PAYLOAD), DartFilingPayload)


def test_fred_dict_does_not_validate_as_ecos():
    # the cross model must reject (disjoint required keys + extra="forbid").
    # Direct model_validate raises pydantic ValidationError; only parse_payload
    # wraps mismatches as PayloadSchemaError.
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EcosMacroPayload.model_validate(FRED_PAYLOAD)
