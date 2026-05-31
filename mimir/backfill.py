from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Mapping

import yaml

from mimir.core.builder import build_sources
from mimir.core.normalize import normalize
from mimir.core.source import FetchContext
from mimir.settings import Settings
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record

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
    records: list[Record] = [
        normalize(raw, source.meta, captured_at=now) for raw in source.fetch(ctx)
    ]
    return store.append(records)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.backfill")
    parser.add_argument("--source", required=True)
    parser.add_argument("--since", required=True, help="YYYY-MM-DD")
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args(argv)

    watchlist = _load_yaml(Path(args.config_dir) / "watchlist.yaml") or {"us": [], "kr": []}
    appended = run_backfill(
        source_id=args.source,
        since=date.fromisoformat(args.since),
        env=os.environ,
        watchlist=watchlist,
    )
    print(f"[mimir] backfill {args.source}: appended {appended} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
