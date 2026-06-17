from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mimir.config import load_sources_config, load_watchlist, report_invalid_sources
from mimir.core.builder import build_sources
from mimir.core.orchestrator import Orchestrator, RunSummary
from mimir.core.registry import Registry
from mimir.core.source import Cadence, FetchContext
from mimir.manifest.manifest import Manifest, RunRecord
from mimir.report.i18n import DEFAULT_LANG
from mimir.report.status_html import render_status_html
from mimir.report.telegram import send_ping
from mimir.settings import Settings
from mimir.sources.config import parse_sources_config
from mimir.storage.jsonl_store import JsonlStore

DEFAULT_DATA_ROOT = Path("data")
DEFAULT_STATUS_PATH = Path("reports/status.html")


def run_collect(
    *,
    cadence: str,
    env: Mapping[str, str] | None = None,
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_DATA_ROOT,
    status_path: Path = DEFAULT_STATUS_PATH,
    sources_config: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> RunSummary:
    now = now or datetime.now(UTC)
    settings = Settings.from_env(env)
    cfg = sources_config or {}
    lang = cfg.get("lang", DEFAULT_LANG)
    registry = Registry(
        build_sources(settings, parse_sources_config(cfg)),
        gray_enabled=cfg.get("gray_enabled", True),
        disabled_ids=set(cfg.get("disabled_ids", [])),
    )
    store = JsonlStore(root=data_root)
    manifest = Manifest(root=data_root)
    orchestrator = Orchestrator(registry, store, manifest)

    ctx = FetchContext(watchlist=watchlist, now=now)
    summary = orchestrator.run(Cadence(cadence), ctx)

    render_status_html(
        RunRecord(ran_at=now, cadence=Cadence(cadence), results=summary.results), status_path, lang
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
    sources_config = load_sources_config(config_dir)
    try:  # validate config upfront; keep the except narrow so a downstream
        parse_sources_config(sources_config)  # ValidationError isn't mislabeled
    except ValidationError as exc:
        return report_invalid_sources(exc)
    summary = run_collect(
        cadence=args.cadence,
        watchlist=load_watchlist(config_dir),
        sources_config=sources_config,
    )
    print(f"[mimir] {args.cadence}: {[r.model_dump() for r in summary.results]}")
    return 1 if summary.had_failures else 0


if __name__ == "__main__":
    sys.exit(main())
