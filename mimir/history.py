from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from mimir.analysis.reader import DataReader
from mimir.historical.engine import HistoricalEngine
from mimir.historical.schema import HistoricalInsight
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.paths import DEFAULT_ROOT


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_history(
    *,
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_ROOT,
    as_of: date | None = None,
    captured_at: datetime | None = None,
) -> list[HistoricalInsight]:
    as_of = as_of or datetime.now(UTC).date()
    store = JsonlStore(root=data_root)
    engine = HistoricalEngine(DataReader(store), store)
    return engine.run(watchlist, as_of, captured_at=captured_at)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.history")
    parser.add_argument("--symbol", help="analyze a single symbol (default: full watchlist)")
    parser.add_argument("--date", help="YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--data-root", default=str(DEFAULT_ROOT))
    args = parser.parse_args(argv)

    if args.symbol:
        watchlist = {"us": [args.symbol], "kr": [args.symbol]}
    else:
        watchlist = _load_yaml(Path(args.config_dir) / "watchlist.yaml") or {"us": [], "kr": []}

    as_of = date.fromisoformat(args.date) if args.date else None
    insights = run_history(watchlist=watchlist, data_root=Path(args.data_root), as_of=as_of)
    for ins in insights:
        trig = " (TRIGGERED today)" if ins.triggered_today else ""
        h5 = next((h for h in ins.horizons if h.horizon == 5), None)
        tail = f" 5d median {h5.median_return:+.2%} (n={h5.n})" if h5 else ""
        print(f"[mimir] {ins.symbol} {ins.event_type} x{ins.occurrences}{trig}:{tail}")
    print(f"[mimir] history: {len(insights)} historical insight(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
