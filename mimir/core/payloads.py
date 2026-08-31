"""Typed per-dataset payload models + external dispatch (spec INC2).

Replaces the untyped `payload: dict[str, Any]` with dataset-specific pydantic
models so upstream key/type drift fails loudly at the boundary instead of
silently yielding `None` downstream.

Byte-identity invariant (spec §3): each model's field set and declaration order
mirror the source adapter's payload dict exactly, and date-looking values stay
`str`. Therefore `model.model_dump_json()` is byte-identical to the original
dict's serialization, so on-disk JSONL never changes and `idempotency_key` is
never affected.

Dispatch is external (spec §4.2): the discriminator (`dataset`) lives on the
`Record` envelope, never inside the payload (a tag key would break bytes).
Source-specific filing branches (sec vs dart) are resolved structurally by
`extra="forbid"` + disjoint required keys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, ConfigDict, ValidationError

from mimir.analysis.schema import Insight
from mimir.core.errors import PayloadSchemaError
from mimir.core.source import Dataset
from mimir.evaluation.schema import BucketStat
from mimir.historical.schema import HistoricalInsight

if TYPE_CHECKING:
    # Annotation-only: the narrowing helpers below take a Record but only ever
    # isinstance-check its `.payload` against a concrete model, so Record is never
    # needed at runtime here. Importing it at module top would create a cycle in
    # phase 4 (storage.schema -> core.payloads -> ... -> storage.schema).
    from mimir.storage.schema import Record


class _Payload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --- PRICES (stooq + pykrx, single shape) ---
class PricePayload(_Payload):
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    currency: str  # "USD" | "KRW"
    interval: str  # "1d"


# --- MACRO ---
class EcosMacroPayload(_Payload):
    stat_code: str
    item_code: str
    item_name: str | None
    value: float
    unit: str | None
    time: str  # "YYYYMM" etc., ECOS raw string


MacroPayload = EcosMacroPayload


# --- NEWS (rss, single shape) ---
class NewsPayload(_Payload):
    title: str | None
    url: str
    publisher: str
    market: str  # "US" | "KR" | "GLOBAL" (distinct from envelope market)
    published_at: str | None
    summary: str  # may be "", never None (rss.py: `(... or "")[:SUMMARY_MAX]`)


# --- FILINGS (source-specific) ---
class SecFilingPayload(_Payload):
    form_type: str | None
    title: str | None
    accession: str
    url: str
    filed_at: str  # "YYYY-MM-DD"


class DartFilingPayload(_Payload):
    form_type: str | None
    title: str | None
    corp_name: str | None
    url: str
    filed_at: str | None  # dart.py: item.get("rcept_dt") — may be None
    flr_nm: str | None


FilingPayload = SecFilingPayload | DartFilingPayload


# insights/historical/evaluation reuse their existing models (no new model — a
# second source of truth would drift). Each was given extra="forbid" in its own
# module so drift in those payloads also fails loudly.
Payload = (
    PricePayload
    | MacroPayload
    | NewsPayload
    | FilingPayload
    | Insight
    | HistoricalInsight
    | BucketStat
)

# A dataset maps to one model or a tuple of source-specific candidates.
PAYLOAD_BY_DATASET: dict[Dataset, type[BaseModel] | tuple[type[BaseModel], ...]] = {
    Dataset.PRICES: PricePayload,
    Dataset.MACRO: EcosMacroPayload,
    Dataset.NEWS: NewsPayload,
    Dataset.FILINGS: (SecFilingPayload, DartFilingPayload),
    Dataset.INSIGHTS: Insight,
    Dataset.HISTORICAL: HistoricalInsight,
    Dataset.EVALUATION: BucketStat,
}


def parse_payload(dataset: Dataset, data: dict[str, Any]) -> Payload:
    """Validate `data` against the model(s) registered for `dataset`.

    For datasets with multiple source-specific candidates, try each: the first
    that validates wins (resolution is unambiguous because the candidates have
    disjoint required keys + extra="forbid"). If none match, raise
    `PayloadSchemaError` — never silently fall back (spec §5).
    """
    candidates = PAYLOAD_BY_DATASET.get(dataset)
    if candidates is None:
        raise PayloadSchemaError(f"no payload model registered for dataset {dataset!r}")
    models = candidates if isinstance(candidates, tuple) else (candidates,)
    errors: list[str] = []
    for model in models:
        try:
            return cast(Payload, model.model_validate(data))
        except ValidationError as exc:
            errors.append(f"{model.__name__}: {exc.error_count()} error(s)")
    raise PayloadSchemaError(
        f"payload for dataset {dataset.value!r} matched no model ({'; '.join(errors)})"
    )


# --- Narrowing helpers (spec §4.5) ---
# A monomorphic Record with a union payload does not auto-narrow under mypy
# strict. These give signals typed access; a type mismatch raises (never a silent
# None fallback). They accept the phase-1..3 dict payload too, parsing on demand,
# so they work before and after the phase-4 union switch.


def _narrow[M: BaseModel](rec: Record, dataset: Dataset, model: type[M]) -> M:
    payload = rec.payload
    parsed = payload if isinstance(payload, BaseModel) else parse_payload(dataset, payload)
    if not isinstance(parsed, model):
        raise PayloadSchemaError(
            f"expected {model.__name__} for dataset {rec.dataset.value!r}, "
            f"got {type(parsed).__name__}"
        )
    return parsed


def price_payload(rec: Record) -> PricePayload:
    return _narrow(rec, Dataset.PRICES, PricePayload)


def macro_payload(rec: Record) -> MacroPayload:
    return _narrow(rec, Dataset.MACRO, EcosMacroPayload)


def news_payload(rec: Record) -> NewsPayload:
    return _narrow(rec, Dataset.NEWS, NewsPayload)


def filing_payload(rec: Record) -> FilingPayload:
    payload = rec.payload
    parsed = payload if isinstance(payload, BaseModel) else parse_payload(Dataset.FILINGS, payload)
    if not isinstance(parsed, SecFilingPayload | DartFilingPayload):
        raise PayloadSchemaError(
            f"expected a filing payload for dataset {rec.dataset.value!r}, "
            f"got {type(parsed).__name__}"
        )
    return parsed
