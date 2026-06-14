from __future__ import annotations

from datetime import datetime

from pydantic import ValidationError

from mimir.core.errors import NormalizationError, PayloadSchemaError
from mimir.core.source import RawRecord, SourceMeta
from mimir.storage.schema import Record


def normalize(raw: RawRecord, meta: SourceMeta, *, captured_at: datetime) -> Record:
    try:
        # Record construction validates the payload against its dataset schema via
        # the model_validator: upstream key/type drift fails here (loudly,
        # PayloadSchemaError) instead of yielding None silently downstream.
        return Record(
            source=meta.id,
            dataset=meta.dataset,
            market=meta.market,
            symbol=raw.symbol,
            ts=raw.ts,
            captured_at=captured_at,
            idempotency_key=raw.idempotency_key,
            payload=raw.payload,  # type: ignore[arg-type]  # before-validator parses dict->Payload
        )
    except (ValidationError, PayloadSchemaError) as exc:
        raise NormalizationError(str(exc)) from exc
