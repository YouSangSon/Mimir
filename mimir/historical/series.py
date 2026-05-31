from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import NamedTuple

from mimir.core.source import Dataset
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record


class Bar(NamedTuple):
    day: date
    close: float
    volume: float | None


def bars_from_records(records: Iterable[Record]) -> list[Bar]:
    """Build a chronologically ordered close/volume series from price records."""
    bars: list[Bar] = []
    for rec in sorted(records, key=lambda r: r.ts):
        close = rec.payload.get("close")
        if close is None:
            continue
        volume = rec.payload.get("volume")
        bars.append(Bar(rec.ts.date(), float(close), float(volume) if volume is not None else None))
    return bars


def price_series(reader: DataReader, symbol: str, until: date | None = None) -> list[Bar]:
    """Chronologically ordered bars for one symbol from stored prices.

    `until` bounds the series to bars on/before that date, so an event-study run
    with a past as_of cannot see future bars (no look-ahead on replay/backfill).
    """
    return bars_from_records(reader.read(Dataset.PRICES, symbol=symbol, until=until))
