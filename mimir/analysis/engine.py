from __future__ import annotations

from datetime import UTC, date, datetime

from mimir.analysis.schema import Insight, to_record
from mimir.analysis.scorer import score
from mimir.analysis.signals.base import Signal
from mimir.core.source import Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader

MARKET_BY_KEY = {"us": Market.US, "kr": Market.KR}


class AnalysisEngine:
    def __init__(self, signals: list[Signal], reader: DataReader, store: JsonlStore) -> None:
        self._signals = signals
        self._reader = reader
        self._store = store

    def run(
        self,
        watchlist: dict[str, list[str]],
        as_of: date,
        captured_at: datetime | None = None,
    ) -> list[Insight]:
        captured_at = captured_at or datetime.now(UTC)
        insights: list[Insight] = []
        records = []
        for key, market in MARKET_BY_KEY.items():
            for symbol in watchlist.get(key, []):
                results = []
                for sig in self._signals:
                    result = sig.evaluate(symbol, market, as_of, self._reader)
                    if result is not None:
                        results.append(result)
                if not results:
                    continue
                sc = score(results)
                insight = Insight(
                    symbol=symbol,
                    market=market,
                    as_of=as_of,
                    direction=sc.direction,
                    stars=sc.stars,
                    confidence=sc.confidence,
                    attention=sc.attention,
                    signals=results,
                    reasons=sc.reasons,
                )
                insights.append(insight)
                records.append(to_record(insight, captured_at))
        self._store.append(records)
        return insights
