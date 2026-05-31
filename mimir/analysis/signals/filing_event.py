from __future__ import annotations

from datetime import date, timedelta

from mimir.analysis.reader import DataReader
from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.source import Dataset, Market
from mimir.storage.schema import Record

LOOKBACK_DAYS = 3
IMPORTANT_US_FORMS = {"8-K", "8-K/A"}
KR_IMPORTANT_KEYWORD = "주요사항"
WEIGHT = 0.8


def _is_important(rec: Record) -> bool:
    form = rec.payload.get("form_type") or ""
    return form in IMPORTANT_US_FORMS or KR_IMPORTANT_KEYWORD in form


class FilingEventSignal:
    id = "filing_event"

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None:
        recs = reader.read(
            Dataset.FILINGS, symbol=symbol, since=as_of - timedelta(days=LOOKBACK_DAYS), until=as_of
        )
        if not recs:
            return None
        important = [r for r in recs if _is_important(r)]
        if important:
            forms = ", ".join(sorted({(r.payload.get("form_type") or "?") for r in important}))
            return SignalResult(
                signal=self.id,
                direction=SignalDirection.NEUTRAL,
                strength=min(len(important) / 3, 1.0),
                confidence=0.6,
                reason=f"{len(important)} material filing(s): {forms}",
                weight=WEIGHT,
            )
        return SignalResult(
            signal=self.id,
            direction=SignalDirection.NEUTRAL,
            strength=min(len(recs) / 10, 0.3),
            confidence=0.4,
            reason=f"{len(recs)} routine filing(s)",
            weight=WEIGHT,
        )
