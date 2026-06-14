from __future__ import annotations

from datetime import datetime

from pydantic import ValidationError

from mimir.core.errors import NormalizationError, PayloadSchemaError
from mimir.core.payloads import parse_payload
from mimir.core.source import RawRecord, SourceMeta
from mimir.storage.schema import Record


def normalize(raw: RawRecord, meta: SourceMeta, *, captured_at: datetime) -> Record:
    try:
        # Validate the payload against its dataset schema: upstream key/type drift
        # fails here (loudly) instead of yielding None silently downstream.
        parse_payload(meta.dataset, raw.payload)
        return Record(
            source=meta.id,
            dataset=meta.dataset,
            market=meta.market,
            symbol=raw.symbol,
            ts=raw.ts,
            captured_at=captured_at,
            idempotency_key=raw.idempotency_key,
            payload=raw.payload,
        )
    except (ValidationError, PayloadSchemaError) as exc:
        raise NormalizationError(str(exc)) from exc
