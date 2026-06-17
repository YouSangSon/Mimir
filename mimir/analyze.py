from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import ValidationError

from mimir.analysis.builder import build_signals
from mimir.analysis.engine import AnalysisEngine
from mimir.analysis.schema import Insight
from mimir.config import load_validated_sources_config, load_watchlist, report_invalid_sources
from mimir.settings import Settings
from mimir.sources.config import SourcesConfig
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader

DEFAULT_DATA_ROOT = Path("data")


def run_analyze(
    *,
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_DATA_ROOT,
    as_of: date | None = None,
    captured_at: datetime | None = None,
    config: SourcesConfig | None = None,
    settings: Settings | None = None,
) -> list[Insight]:
    as_of = as_of or datetime.now(UTC).date()
    store = JsonlStore(root=data_root)
    # config/settings default to None -> build_signals returns today's 4 signals.
    # The LLM signal only joins when sources.yaml enables it + a key is present.
    engine = AnalysisEngine(build_signals(config, settings), DataReader(store), store)
    return engine.run(watchlist, as_of, captured_at=captured_at)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.analyze")
    parser.add_argument("--date", help="YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    args = parser.parse_args(argv)

    config_dir = Path(args.config_dir)
    as_of = date.fromisoformat(args.date) if args.date else None
    try:
        _, sources_config = load_validated_sources_config(config_dir)
    except ValidationError as exc:
        return report_invalid_sources(exc)
    insights = run_analyze(
        watchlist=load_watchlist(config_dir),
        data_root=Path(args.data_root),
        as_of=as_of,
        config=sources_config,
        settings=Settings.from_env(),
    )
    for ins in insights:
        stars = "★" * ins.stars + "☆" * (5 - ins.stars)
        print(f"[mimir] {ins.symbol} {ins.direction.value} {stars} (conf {ins.confidence})")
    print(f"[mimir] analyze: {len(insights)} insight(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
