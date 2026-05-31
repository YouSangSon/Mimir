from __future__ import annotations

import re
from datetime import date, timedelta

from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.source import Dataset, Market
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

BASELINE_DAYS = 7
WEIGHT = 0.5


def _mentions(rec: Record, symbol: str) -> bool:
    # Word-boundary match (case-insensitive) so short tickers like "A"/"ON"/"ALL"
    # don't match "a"/"on"/"all" inside ordinary prose. Note: official feeds rarely
    # carry tickers, so this stays mostly inert until ticker-tagged feeds / an LLM
    # signal land (see docs/IMPROVEMENTS.md).
    text = (rec.payload.get("title") or "") + " " + (rec.payload.get("summary") or "")
    return re.search(rf"\b{re.escape(symbol)}\b", text, re.IGNORECASE) is not None


class NewsVolumeSignal:
    id = "news_volume"

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None:
        today = [
            r for r in reader.read(Dataset.NEWS, since=as_of, until=as_of) if _mentions(r, symbol)
        ]
        if not today:
            return None
        base_window = reader.read(
            Dataset.NEWS,
            since=as_of - timedelta(days=BASELINE_DAYS),
            until=as_of - timedelta(days=1),
        )
        base = [r for r in base_window if _mentions(r, symbol)]
        base_daily = len(base) / BASELINE_DAYS
        ratio = len(today) / (base_daily + 1.0)
        return SignalResult(
            signal=self.id,
            direction=SignalDirection.NEUTRAL,
            strength=min(ratio / 3.0, 1.0),
            confidence=0.5,
            reason=f"{len(today)} news mention(s) today vs ~{base_daily:.1f}/day baseline",
            weight=WEIGHT,
        )
