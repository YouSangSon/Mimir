from __future__ import annotations

from datetime import date, timedelta

from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.payloads import macro_payload
from mimir.core.source import Dataset, Market
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

WINDOW_DAYS = 60
# Policy/benchmark rate series: FRED FEDFUNDS/DGS10, ECOS base rate (stat.item).
RATE_SERIES = {"FEDFUNDS", "DGS10", "722Y001.0101000"}
FULL_DELTA = 1.0  # a 1.0 percentage-point change -> full (mild) strength
WEIGHT = 0.3


class MacroRegimeSignal:
    """Market-wide lean: rising policy rate -> risk-off (bearish); falling -> risk-on (bullish)."""

    id = "macro_regime"

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None:
        recs = [
            r
            for r in reader.read(
                Dataset.MACRO, since=as_of - timedelta(days=WINDOW_DAYS), until=as_of
            )
            if r.market == market and r.symbol in RATE_SERIES
        ]
        if len(recs) < 2:
            return None

        by_series: dict[str, list[Record]] = {}
        for r in recs:
            by_series.setdefault(r.symbol or "", []).append(r)
        best = max(by_series.values(), key=lambda recs: len(recs))
        if len(best) < 2:
            return None
        series = sorted(best, key=lambda r: r.ts)

        first, last = macro_payload(series[0]).value, macro_payload(series[-1]).value
        delta = last - first
        if delta > 1e-9:
            direction = SignalDirection.BEARISH
        elif delta < -1e-9:
            direction = SignalDirection.BULLISH
        else:
            direction = SignalDirection.NEUTRAL
        trend = "rising" if delta > 0 else "falling" if delta < 0 else "flat"
        return SignalResult(
            signal=self.id,
            direction=direction,
            strength=min(abs(delta) / FULL_DELTA, 1.0),
            confidence=0.4,
            reason=f"{series[0].symbol} {first}->{last} ({trend})",
            weight=WEIGHT,
        )
