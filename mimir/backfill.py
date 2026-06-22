from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mimir.config import (
    SourcesConfigError,
    WatchlistConfigError,
    load_validated_sources_config,
    load_watchlist,
    report_invalid_sources,
    report_invalid_watchlist,
)
from mimir.core.builder import SourceSpec, build_sources, load_source_specs
from mimir.core.errors import NormalizationError
from mimir.core.normalize import normalize
from mimir.core.source import Cadence, FetchContext
from mimir.manifest.manifest import Manifest, SourceResult
from mimir.settings import Settings
from mimir.sources.config import RuntimeSourcesConfig, parse_runtime_sources_config
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.policy import append_overwrite_enabled
from mimir.storage.schema import Record

logger = logging.getLogger(__name__)
DEFAULT_DATA_ROOT = Path("data")


def _source_spec_for_id(specs: Sequence[SourceSpec], source_id: str) -> SourceSpec | None:
    for spec in specs:
        if spec.id == source_id:
            return spec
    return None


def _preflight_unavailable_error(spec: SourceSpec, settings: Settings, source_id: str) -> str:
    if spec.required_secret_attr and not getattr(settings, spec.required_secret_attr):
        return f"{spec.required_secret_name or spec.required_secret_attr} is not set"
    if spec.required_module:
        return (
            spec.missing_module_hint
            or f"required module {spec.required_module} is not installed"
        )
    return f"unknown or unavailable source: {source_id}"


def _write_failure_manifest(
    manifest: Manifest,
    *,
    now: datetime,
    cadence: Cadence,
    source_id: str,
    fetched: int,
    invalid: int,
    error: str,
) -> None:
    manifest.write(
        now=now,
        cadence=cadence,
        results=[
            SourceResult(
                source=source_id,
                ok=False,
                fetched=fetched,
                invalid=invalid,
                error=error,
            )
        ],
    )


def run_backfill(
    *,
    source_id: str,
    since: date,
    env: Mapping[str, str] | None = None,
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_DATA_ROOT,
    sources_config: dict[str, Any] | RuntimeSourcesConfig | None = None,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    settings = Settings.from_env(env)
    runtime = (
        sources_config
        if isinstance(sources_config, RuntimeSourcesConfig)
        else parse_runtime_sources_config(sources_config or {})
    )
    manifest = Manifest(root=data_root)
    specs = load_source_specs()
    built_sources = build_sources(settings, runtime.source_config, specs=specs)
    sources = {s.meta.id: s for s in built_sources}
    if source_id not in sources:
        if (spec := _source_spec_for_id(specs, source_id)) and spec.meta is not None:
            manifest_error = _preflight_unavailable_error(spec, settings, source_id)
            try:
                _write_failure_manifest(
                    manifest,
                    now=now,
                    cadence=spec.meta.cadence,
                    source_id=spec.meta.id,
                    fetched=0,
                    invalid=0,
                    error=manifest_error,
                )
            except Exception:
                logger.warning(
                    "backfill %s: failed to write preflight failure manifest",
                    source_id,
                    exc_info=True,
                )
        raise SystemExit(f"unknown or unavailable source: {source_id}")
    source = sources[source_id]
    store = JsonlStore(root=data_root)

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
        stored = store.append(records, overwrite=append_overwrite_enabled(source.meta.dataset))
    except Exception as exc:
        try:
            _write_failure_manifest(
                manifest,
                now=now,
                cadence=source.meta.cadence,
                source_id=source.meta.id,
                fetched=fetched,
                invalid=invalid,
                error=str(exc),
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
    try:  # validate config upfront; keep the except narrow so a downstream
        _, runtime_config = load_validated_sources_config(config_dir)
    except ValidationError as exc:
        return report_invalid_sources(exc)
    try:
        watchlist = load_watchlist(config_dir)
    except WatchlistConfigError as exc:
        return report_invalid_watchlist(exc)
    try:
        appended = run_backfill(
            source_id=args.source,
            since=date.fromisoformat(args.since),
            watchlist=watchlist,
            sources_config=runtime_config,
        )
    except SourcesConfigError as exc:
        return report_invalid_sources(exc)
    print(f"[mimir] backfill {args.source}: appended {appended} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
