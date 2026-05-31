from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from mimir.analyze import run_analyze
from mimir.collect import run_collect
from mimir.config import load_sources_config, load_watchlist
from mimir.core.source import Cadence
from mimir.deliver import run_deliver
from mimir.history import run_history
from mimir.report.daily_report import DEFAULT_REPORTS_ROOT
from mimir.storage.paths import DEFAULT_ROOT


def run_pipeline(
    *,
    cadence: str,
    env: Mapping[str, str],
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_ROOT,
    reports_root: Path = DEFAULT_REPORTS_ROOT,
    sources_config: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run the full cadence pipeline in one process: collect → analyze → history → deliver."""
    now = now or datetime.now(UTC)
    as_of: date = now.date()

    collect_summary = run_collect(
        cadence=cadence,
        env=env,
        watchlist=watchlist,
        data_root=data_root,
        status_path=reports_root / "status.html",
        sources_config=sources_config,
        now=now,
    )
    insights = run_analyze(watchlist=watchlist, data_root=data_root, as_of=as_of, captured_at=now)
    historical = run_history(watchlist=watchlist, data_root=data_root, as_of=as_of, captured_at=now)
    delivery = run_deliver(
        cadence=cadence, env=env, data_root=data_root, reports_root=reports_root, as_of=as_of
    )
    return {
        "collect_failures": collect_summary.had_failures,
        "insights": len(insights),
        "historical": len(historical),
        "report": delivery["report"],
        "telegram_sent": delivery["sent"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.run")
    parser.add_argument("--cadence", required=True, choices=[c.value for c in Cadence])
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--data-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--reports-root", default=str(DEFAULT_REPORTS_ROOT))
    args = parser.parse_args(argv)

    config_dir = Path(args.config_dir)
    result = run_pipeline(
        cadence=args.cadence,
        env=os.environ,
        watchlist=load_watchlist(config_dir),
        data_root=Path(args.data_root),
        reports_root=Path(args.reports_root),
        sources_config=load_sources_config(config_dir),
    )
    print(
        f"[mimir] {args.cadence}: insights={result['insights']} "
        f"historical={result['historical']} report={result['report']} "
        f"telegram_sent={result['telegram_sent']}"
    )
    return 1 if result["collect_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
