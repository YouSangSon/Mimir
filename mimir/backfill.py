from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path

from mimir.config import load_watchlist
from mimir.core.builder import build_sources
from mimir.core.errors import NormalizationError
from mimir.core.normalize import normalize
from mimir.core.source import FetchContext
from mimir.settings import Settings
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record

logger = logging.getLogger(__name__)
DEFAULT_DATA_ROOT = Path("data")


def run_backfill(
    *,
    source_id: str,
    since: date,
    env: Mapping[str, str],
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_DATA_ROOT,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    settings = Settings.from_env(env)
    sources = {s.meta.id: s for s in build_sources(settings)}
    if source_id not in sources:
        raise SystemExit(f"unknown or unavailable source: {source_id}")
    source = sources[source_id]
    store = JsonlStore(root=data_root)

    ctx = FetchContext(watchlist=watchlist, now=now, backfill_since=since)
    records: list[Record] = []
    invalid = 0
    for raw in source.fetch(ctx):
        try:  # per-record isolation: one bad record must not abort the backfill
            records.append(normalize(raw, source.meta, captured_at=now))
        except NormalizationError:
            invalid += 1
    if invalid:
        logger.warning("backfill %s: skipped %d invalid record(s)", source_id, invalid)
    return store.append(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.backfill")
    parser.add_argument("--source", required=True)
    parser.add_argument("--since", required=True, help="YYYY-MM-DD")
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args(argv)

    appended = run_backfill(
        source_id=args.source,
        since=date.fromisoformat(args.since),
        env=os.environ,
        watchlist=load_watchlist(Path(args.config_dir)),
    )
    print(f"[mimir] backfill {args.source}: appended {appended} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
