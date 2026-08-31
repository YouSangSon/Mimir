from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mimir.analysis.schema import Insight
from mimir.config import load_validated_sources_config, report_invalid_sources
from mimir.core.source import Cadence, Dataset
from mimir.evaluation.schema import BucketStat
from mimir.historical.schema import HistoricalInsight
from mimir.report.daily_report import (
    DEFAULT_REPORTS_ROOT,
    build_report_html,
    rebuild_index,
    save_report,
)
from mimir.report.digest import build_digest
from mimir.report.i18n import DEFAULT_LANG
from mimir.report.telegram import send_ping
from mimir.settings import Settings
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.paths import DEFAULT_ROOT
from mimir.storage.reader import DataReader


class DeliveryResult(dict[str, Any]):
    pass


def run_deliver(
    *,
    cadence: str,
    env: Mapping[str, str] | None = None,
    data_root: Path = DEFAULT_ROOT,
    reports_root: Path = DEFAULT_REPORTS_ROOT,
    as_of: date | None = None,
    lang: str = DEFAULT_LANG,
) -> DeliveryResult:
    as_of = as_of or datetime.now(UTC).date()
    reader = DataReader(JsonlStore(root=data_root))
    records = reader.read(Dataset.INSIGHTS, since=as_of, until=as_of)
    insights = [Insight.model_validate(r.payload) for r in records]
    hist_records = reader.read(Dataset.HISTORICAL, since=as_of, until=as_of)
    historical = [HistoricalInsight.model_validate(r.payload) for r in hist_records]
    eval_records = reader.read(Dataset.EVALUATION, since=as_of, until=as_of)
    evaluation = [BucketStat.model_validate(r.payload) for r in eval_records]

    html_doc = build_report_html(
        insights, as_of, cadence, historical=historical, evaluation=evaluation, lang=lang
    )
    report_path = save_report(html_doc, as_of, reports_root)
    rebuild_index(reports_root, lang)

    settings = Settings.from_env(env)
    digest = build_digest(insights, cadence, as_of, lang=lang)
    sent = send_ping(
        bot_token=settings.telegram_bot_token, chat_id=settings.telegram_chat_id, text=digest
    )
    return DeliveryResult(
        report=report_path,
        insights=len(insights),
        historical=len(historical),
        evaluation=len(evaluation),
        sent=sent,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.deliver")
    parser.add_argument("--cadence", default="daily", choices=[c.value for c in Cadence])
    parser.add_argument("--date", help="YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--data-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--reports-root", default=str(DEFAULT_REPORTS_ROOT))
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args(argv)

    try:
        _, runtime_config = load_validated_sources_config(Path(args.config_dir))
    except ValidationError as exc:
        return report_invalid_sources(exc)
    lang = runtime_config.lang
    as_of = date.fromisoformat(args.date) if args.date else None
    result = run_deliver(
        cadence=args.cadence,
        data_root=Path(args.data_root),
        reports_root=Path(args.reports_root),
        as_of=as_of,
        lang=lang,
    )
    print(
        f"[mimir] deliver {args.cadence}: {result['insights']} insight(s) -> "
        f"{result['report']} (telegram sent: {result['sent']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
