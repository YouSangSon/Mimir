from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from mimir.analysis.builder import build_signals
from mimir.analysis.engine import AnalysisEngine
from mimir.analysis.schema import Insight
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader

DEFAULT_DATA_ROOT = Path("data")


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_analyze(
    *,
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_DATA_ROOT,
    as_of: date | None = None,
    captured_at: datetime | None = None,
) -> list[Insight]:
    as_of = as_of or datetime.now(UTC).date()
    store = JsonlStore(root=data_root)
    engine = AnalysisEngine(build_signals(), DataReader(store), store)
    return engine.run(watchlist, as_of, captured_at=captured_at)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.analyze")
    parser.add_argument("--date", help="YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    args = parser.parse_args(argv)

    watchlist = _load_yaml(Path(args.config_dir) / "watchlist.yaml") or {"us": [], "kr": []}
    as_of = date.fromisoformat(args.date) if args.date else None
    insights = run_analyze(
        watchlist=watchlist, data_root=Path(args.data_root), as_of=as_of
    )
    for ins in insights:
        stars = "★" * ins.stars + "☆" * (5 - ins.stars)
        print(f"[mimir] {ins.symbol} {ins.direction.value} {stars} (conf {ins.confidence})")
    print(f"[mimir] analyze: {len(insights)} insight(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
