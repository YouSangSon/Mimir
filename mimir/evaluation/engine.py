from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime

from mimir.analysis.schema import Insight
from mimir.core.source import Dataset, Market
from mimir.evaluation.metrics import Obs, anchor_index, evaluate_bucket
from mimir.evaluation.schema import EvaluationReport, to_record
from mimir.historical.series import Bar, bars_from_records
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

BucketKey = tuple[str, str, Market]


class EvaluationEngine:
    def __init__(self, reader: DataReader, store: JsonlStore) -> None:
        self._reader = reader
        self._store = store

    def run(self, as_of: date, captured_at: datetime | None = None) -> EvaluationReport:
        captured_at = captured_at or datetime.now(UTC)
        insights = [
            Insight.model_validate(r.payload)
            for r in self._reader.read(Dataset.INSIGHTS, until=as_of)
        ]
        bars_by_symbol = self._load_bars(until=as_of)

        acc: dict[BucketKey, list[Obs]] = defaultdict(list)
        for ins in insights:
            series = bars_by_symbol.get(ins.symbol, [])
            anchor = anchor_index(series, ins.as_of)
            if anchor is None:
                continue  # too recent: no forward bar to score against
            self._accumulate(acc, ins, series, anchor)

        buckets = [
            stat
            for stat in (evaluate_bucket(key, obs) for key, obs in acc.items())
            if stat is not None
        ]
        report = EvaluationReport(
            as_of=as_of,
            insights_evaluated=len(insights),
            buckets=buckets,
            sufficient=bool(buckets),
        )
        self._store.append(
            [to_record(b, as_of, captured_at) for b in buckets], overwrite=True
        )
        return report

    def _load_bars(self, *, until: date) -> dict[str, list[Bar]]:
        """Read the whole price dataset once and bucket bars by symbol
        (mirrors HistoricalEngine's by_symbol load to avoid per-symbol scans)."""
        by_symbol: dict[str, list[Record]] = defaultdict(list)
        for rec in self._reader.read(Dataset.PRICES, until=until):
            if rec.symbol:
                by_symbol[rec.symbol].append(rec)
        return {sym: bars_from_records(recs) for sym, recs in by_symbol.items()}

    @staticmethod
    def _accumulate(
        acc: dict[BucketKey, list[Obs]], ins: Insight, series: list[Bar], anchor: int
    ) -> None:
        market = ins.market
        # per-direction / per-star: scored by the insight's aggregate direction
        acc[("per_direction", ins.direction.value, market)].append(
            Obs(series, anchor, ins.direction)
        )
        acc[("per_star", str(ins.stars), market)].append(Obs(series, anchor, ins.direction))
        # per-signal: each composing signal contributes with ITS OWN direction
        for sig in ins.signals:
            acc[("per_signal", sig.signal, market)].append(Obs(series, anchor, sig.direction))
