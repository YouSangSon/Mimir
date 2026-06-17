from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mimir.analyze import run_analyze
from mimir.collect import run_collect
from mimir.config import load_validated_sources_config, load_watchlist, report_invalid_sources
from mimir.core.source import Cadence
from mimir.deliver import run_deliver
from mimir.evaluate import run_evaluate
from mimir.history import run_history
from mimir.report.daily_report import DEFAULT_REPORTS_ROOT
from mimir.report.i18n import DEFAULT_LANG
from mimir.settings import Settings
from mimir.sources.config import parse_sources_config
from mimir.storage.paths import DEFAULT_ROOT


def run_pipeline(
    *,
    cadence: str,
    env: Mapping[str, str] | None = None,
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_ROOT,
    reports_root: Path = DEFAULT_REPORTS_ROOT,
    sources_config: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run the full cadence pipeline in one process.

    Flow: collect → analyze → history → evaluate → deliver.
    """
    now = now or datetime.now(UTC)
    as_of: date = now.date()
    lang = (sources_config or {}).get("lang", DEFAULT_LANG)

    collect_summary = run_collect(
        cadence=cadence,
        env=env,
        watchlist=watchlist,
        data_root=data_root,
        status_path=reports_root / "status.html",
        sources_config=sources_config,
        now=now,
    )
    insights = run_analyze(
        watchlist=watchlist,
        data_root=data_root,
        as_of=as_of,
        captured_at=now,
        config=parse_sources_config(sources_config or {}),
        settings=Settings.from_env(env),
    )
    historical = run_history(watchlist=watchlist, data_root=data_root, as_of=as_of, captured_at=now)
    evaluation = run_evaluate(data_root=data_root, as_of=as_of, captured_at=now)
    delivery = run_deliver(
        cadence=cadence,
        env=env,
        data_root=data_root,
        reports_root=reports_root,
        as_of=as_of,
        lang=lang,
    )
    return {
        "collect_failures": collect_summary.had_failures,
        "insights": len(insights),
        "historical": len(historical),
        "evaluation": len(evaluation.buckets),
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
    try:  # validate config upfront; keep the except narrow so a downstream
        sources_config, _ = load_validated_sources_config(config_dir)
    except ValidationError as exc:
        return report_invalid_sources(exc)
    result = run_pipeline(
        cadence=args.cadence,
        watchlist=load_watchlist(config_dir),
        data_root=Path(args.data_root),
        reports_root=Path(args.reports_root),
        sources_config=sources_config,
    )
    print(
        f"[mimir] {args.cadence}: insights={result['insights']} "
        f"historical={result['historical']} evaluation={result['evaluation']} "
        f"report={result['report']} "
        f"telegram_sent={result['telegram_sent']}"
    )
    return 1 if result["collect_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
