from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

import yaml

from mimir.core.builder import build_sources
from mimir.core.orchestrator import Orchestrator, RunSummary
from mimir.core.registry import Registry
from mimir.core.source import Cadence, FetchContext
from mimir.manifest.manifest import Manifest, RunRecord
from mimir.report.status_html import render_status_html
from mimir.report.telegram import send_ping
from mimir.settings import Settings
from mimir.storage.jsonl_store import JsonlStore

DEFAULT_DATA_ROOT = Path("data")
DEFAULT_STATUS_PATH = Path("reports/status.html")


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_collect(
    *,
    cadence: str,
    env: Mapping[str, str],
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_DATA_ROOT,
    status_path: Path = DEFAULT_STATUS_PATH,
    sources_config: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> RunSummary:
    now = now or datetime.now(UTC)
    settings = Settings.from_env(env)
    cfg = sources_config or {}
    registry = Registry(
        build_sources(settings),
        gray_enabled=cfg.get("gray_enabled", True),
        disabled_ids=set(cfg.get("disabled_ids", [])),
    )
    store = JsonlStore(root=data_root)
    manifest = Manifest(root=data_root)
    orchestrator = Orchestrator(registry, store, manifest)

    ctx = FetchContext(watchlist=watchlist, now=now)
    summary = orchestrator.run(Cadence(cadence), ctx)

    render_status_html(
        RunRecord(ran_at=now, cadence=Cadence(cadence), results=summary.results), status_path
    )

    ok = sum(1 for r in summary.results if r.ok)
    send_ping(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        text=f"Mimir {cadence}: {ok}/{len(summary.results)} sources OK"
        + ("" if not summary.had_failures else " (failures present)"),
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.collect")
    parser.add_argument("--cadence", required=True, choices=[c.value for c in Cadence])
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args(argv)

    config_dir = Path(args.config_dir)
    watchlist = _load_yaml(config_dir / "watchlist.yaml") or {"us": [], "kr": []}
    sources_config = _load_yaml(config_dir / "sources.yaml")

    summary = run_collect(
        cadence=args.cadence,
        env=os.environ,
        watchlist=watchlist,
        sources_config=sources_config,
    )
    print(f"[mimir] {args.cadence}: {[r.model_dump() for r in summary.results]}")
    return 1 if summary.had_failures else 0


if __name__ == "__main__":
    sys.exit(main())
