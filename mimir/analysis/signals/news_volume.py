from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta

from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.analysis.signals.news_matching import NewsMentionMatcher
from mimir.core.source import Dataset, Market
from mimir.storage.reader import DataReader

BASELINE_DAYS = 7
WEIGHT = 0.5


class NewsVolumeSignal:
    id = "news_volume"

    def __init__(self, aliases: Mapping[str, Sequence[str]] | None = None) -> None:
        self._matcher = NewsMentionMatcher(aliases)

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None:
        today = [
            r
            for r in reader.read_captured_window(Dataset.NEWS, since=as_of, until=as_of)
            if self._matcher.mentions(r, symbol)
        ]
        if not today:
            return None
        base_window = reader.read_captured_window(
            Dataset.NEWS,
            since=as_of - timedelta(days=BASELINE_DAYS),
            until=as_of - timedelta(days=1),
        )
        base = [r for r in base_window if self._matcher.mentions(r, symbol)]
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
