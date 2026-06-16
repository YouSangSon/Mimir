from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mimir.config import load_sources_config, load_watchlist, report_invalid_sources
from mimir.core.builder import build_sources
from mimir.core.errors import NormalizationError
from mimir.core.normalize import normalize
from mimir.core.source import FetchContext
from mimir.manifest.manifest import Manifest, SourceResult
from mimir.settings import Settings
from mimir.sources.config import parse_sources_config
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
    sources_config: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    settings = Settings.from_env(env)
    config = parse_sources_config(sources_config or {})
    sources = {s.meta.id: s for s in build_sources(settings, config)}
    if source_id not in sources:
        raise SystemExit(f"unknown or unavailable source: {source_id}")
    source = sources[source_id]
    store = JsonlStore(root=data_root)
    manifest = Manifest(root=data_root)

    ctx = FetchContext(watchlist=watchlist, now=now, backfill_since=since)
    records: list[Record] = []
    fetched = 0
    invalid = 0
    try:
        for raw in source.fetch(ctx):
            fetched += 1
            try:  # per-record isolation: one bad record must not abort the backfill
                records.append(normalize(raw, source.meta, captured_at=now))
            except NormalizationError:
                invalid += 1
        if invalid:
            logger.warning("backfill %s: skipped %d invalid record(s)", source_id, invalid)
        stored = store.append(records)
    except Exception as exc:
        try:
            manifest.write(
                now=now,
                cadence=source.meta.cadence,
                results=[
                    SourceResult(
                        source=source.meta.id,
                        ok=False,
                        fetched=fetched,
                        invalid=invalid,
                        error=str(exc),
                    )
                ],
            )
        except Exception:
            logger.warning(
                "backfill %s: failed to write failure manifest", source_id, exc_info=True
            )
        raise
    manifest.write(
        now=now,
        cadence=source.meta.cadence,
        results=[
            SourceResult(
                source=source.meta.id,
                ok=True,
                fetched=fetched,
                stored=stored,
                invalid=invalid,
            )
        ],
    )
    return stored


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.backfill")
    parser.add_argument("--source", required=True)
    parser.add_argument("--since", required=True, help="YYYY-MM-DD")
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args(argv)

    config_dir = Path(args.config_dir)
    sources_config = load_sources_config(config_dir)
    try:  # validate config upfront; keep the except narrow so a downstream
        parse_sources_config(sources_config)  # ValidationError isn't mislabeled
    except ValidationError as exc:
        return report_invalid_sources(exc)
    appended = run_backfill(
        source_id=args.source,
        since=date.fromisoformat(args.since),
        env=os.environ,
        watchlist=load_watchlist(config_dir),
        sources_config=sources_config,
    )
    print(f"[mimir] backfill {args.source}: appended {appended} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
