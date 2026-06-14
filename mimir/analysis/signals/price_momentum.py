from __future__ import annotations

from datetime import date, timedelta

from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core.payloads import price_payload
from mimir.core.source import Dataset, Market
from mimir.storage.reader import DataReader

WINDOW_DAYS = 14  # calendar buffer covering ~10 trading sessions
UP_THRESHOLD = 0.02  # ±2% defines a direction
FULL_MOVE = 0.10  # a 10% move -> full strength
VOLUME_SURGE_RATIO = 1.5
WEIGHT = 1.0


class PriceMomentumSignal:
    id = "price_momentum"

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None:
        window = reader.read(
            Dataset.PRICES, symbol=symbol, since=as_of - timedelta(days=WINDOW_DAYS), until=as_of
        )
        recs = sorted(window, key=lambda r: r.ts)
        payloads = [price_payload(r) for r in recs]
        closes = [(p.close, p.volume) for p in payloads if p.close is not None]
        if len(closes) < 2:
            return None

        first, last = closes[0][0], closes[-1][0]
        ret = (last - first) / first if first else 0.0
        if ret > UP_THRESHOLD:
            direction = SignalDirection.BULLISH
        elif ret < -UP_THRESHOLD:
            direction = SignalDirection.BEARISH
        else:
            direction = SignalDirection.NEUTRAL

        confidence, surge = 0.6, False
        vols = [v for _, v in closes if v]
        if len(vols) >= 2:
            prior_avg = sum(vols[:-1]) / (len(vols) - 1)
            if prior_avg and vols[-1] > VOLUME_SURGE_RATIO * prior_avg:
                confidence, surge = 0.85, True

        reason = f"{ret * 100:+.1f}% over {len(closes)} sessions" + (
            " with volume surge" if surge else ""
        )
        return SignalResult(
            signal=self.id,
            direction=direction,
            strength=min(abs(ret) / FULL_MOVE, 1.0),
            confidence=confidence,
            reason=reason,
            weight=WEIGHT,
        )
