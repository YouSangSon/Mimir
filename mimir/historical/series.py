from __future__ import annotations

from datetime import date
from typing import NamedTuple

from mimir.analysis.reader import DataReader
from mimir.core.source import Dataset


class Bar(NamedTuple):
    day: date
    close: float
    volume: float | None


def price_series(reader: DataReader, symbol: str, until: date | None = None) -> list[Bar]:
    """Chronologically ordered close/volume bars for a symbol from stored prices.

    `until` bounds the series to bars on/before that date, so an event-study run
    with a past as_of cannot see future bars (no look-ahead on replay/backfill).
    """
    bars: list[Bar] = []
    for rec in sorted(reader.read(Dataset.PRICES, symbol=symbol, until=until), key=lambda r: r.ts):
        close = rec.payload.get("close")
        if close is None:
            continue
        volume = rec.payload.get("volume")
        bars.append(Bar(rec.ts.date(), float(close), float(volume) if volume is not None else None))
    return bars
