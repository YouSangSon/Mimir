from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from mimir.evaluation.engine import EvaluationEngine
from mimir.evaluation.schema import EvaluationReport
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.paths import DEFAULT_ROOT
from mimir.storage.reader import DataReader

EXAMPLE_HORIZON = 5


def run_evaluate(
    *,
    data_root: Path = DEFAULT_ROOT,
    as_of: date | None = None,
    captured_at: datetime | None = None,
) -> EvaluationReport:
    as_of = as_of or datetime.now(UTC).date()
    store = JsonlStore(root=data_root)
    engine = EvaluationEngine(DataReader(store), store)
    return engine.run(as_of, captured_at=captured_at)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.evaluate")
    parser.add_argument("--date", help="YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--data-root", default=str(DEFAULT_ROOT))
    args = parser.parse_args(argv)

    as_of = date.fromisoformat(args.date) if args.date else None
    report = run_evaluate(data_root=Path(args.data_root), as_of=as_of)

    if not report.sufficient:
        print(
            f"[mimir] evaluate: insufficient sample "
            f"({report.insights_evaluated} insight(s) read, no bucket met MIN_EVAL_N)"
        )
        return 0

    for b in report.buckets:
        h5 = next((h for h in b.horizons if h.horizon == EXAMPLE_HORIZON), None)
        tail = (
            f" {EXAMPLE_HORIZON}d hit {h5.hit_rate:.0%} edge {h5.mean_fwd_return:+.2%} (n={h5.n})"
            if h5
            else ""
        )
        print(f"[mimir] {b.market.value} {b.dimension} {b.key}:{tail}")
    print(
        f"[mimir] evaluate: {len(report.buckets)} bucket(s) "
        f"over {report.insights_evaluated} insight(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
