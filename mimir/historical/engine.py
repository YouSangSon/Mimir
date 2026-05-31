from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime

from mimir.core.source import Dataset, Market
from mimir.historical.analog import DEFAULT_HORIZONS, summarize
from mimir.historical.events import detect_sharp_drops, detect_volume_spikes
from mimir.historical.schema import HistoricalInsight, to_record
from mimir.historical.series import Bar, bars_from_records
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

MIN_OCCURRENCES = 3
MIN_HORIZON_N = 2  # drop a horizon's stat if it has fewer forward observations
EXAMPLE_HORIZON = 5
EXAMPLE_LIMIT = 3
MARKET_BY_KEY = {"us": Market.US, "kr": Market.KR}
EVENT_DETECTORS: dict[str, Callable[[list[Bar]], list[int]]] = {
    "sharp_drop": detect_sharp_drops,
    "volume_spike": detect_volume_spikes,
}


def _examples(series: list[Bar], idxs: list[int]) -> list[str]:
    out: list[str] = []
    for i in reversed(idxs):
        j = i + EXAMPLE_HORIZON
        if j >= len(series) or i == 0 or not series[i - 1].close or not series[i].close:
            continue
        day_ret = (series[i].close - series[i - 1].close) / series[i - 1].close
        fwd = (series[j].close - series[i].close) / series[i].close
        out.append(
            f"{series[i].day.isoformat()}: {day_ret * 100:+.1f}% then "
            f"{fwd * 100:+.1f}% ({EXAMPLE_HORIZON}d)"
        )
        if len(out) >= EXAMPLE_LIMIT:
            break
    return out


class HistoricalEngine:
    def __init__(self, reader: DataReader, store: JsonlStore) -> None:
        self._reader = reader
        self._store = store

    def run(
        self,
        watchlist: dict[str, list[str]],
        as_of: date,
        captured_at: datetime | None = None,
    ) -> list[HistoricalInsight]:
        captured_at = captured_at or datetime.now(UTC)
        insights: list[HistoricalInsight] = []
        records = []
        # Read the whole price dataset once and bucket by symbol, instead of
        # re-scanning per symbol (was O(M) full scans -> O(M^2 * N)).
        by_symbol: dict[str, list[Record]] = defaultdict(list)
        for rec in self._reader.read(Dataset.PRICES, until=as_of):
            if rec.symbol:
                by_symbol[rec.symbol].append(rec)
        for key, market in MARKET_BY_KEY.items():
            for symbol in watchlist.get(key, []):
                series = bars_from_records(by_symbol.get(symbol, []))
                if len(series) < 2:
                    continue
                for event_type, detector in EVENT_DETECTORS.items():
                    idxs = detector(series)
                    if len(idxs) < MIN_OCCURRENCES:
                        continue
                    stats = summarize(series, idxs, DEFAULT_HORIZONS, min_n=MIN_HORIZON_N)
                    if not stats:
                        continue
                    insight = HistoricalInsight(
                        symbol=symbol,
                        market=market,
                        as_of=as_of,
                        event_type=event_type,
                        occurrences=len(idxs),
                        triggered_today=(len(series) - 1) in idxs,
                        horizons=stats,
                        examples=_examples(series, idxs),
                    )
                    insights.append(insight)
                    records.append(to_record(insight, captured_at))
        # historical insights are regenerated each run -> last-write-wins
        self._store.append(records, overwrite=True)
        return insights
