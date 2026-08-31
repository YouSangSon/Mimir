from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import ValidationError

from mimir.analysis.schema import Insight
from mimir.config import (
    WatchlistConfigError,
    load_validated_sources_config,
    load_watchlist,
    report_invalid_sources,
    report_invalid_watchlist,
)
from mimir.core.payloads import Payload
from mimir.core.source import Dataset
from mimir.doctor.engine import run_doctor
from mimir.evaluation.schema import BucketStat
from mimir.historical.schema import HistoricalInsight
from mimir.manifest.manifest import Manifest
from mimir.report.daily_report import DEFAULT_REPORTS_ROOT
from mimir.report.dashboard import build_dashboard_html
from mimir.report.i18n import DEFAULT_LANG
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.paths import DEFAULT_ROOT
from mimir.storage.reader import DataReader

DASHBOARD_FILENAME = "dashboard.html"


def _latest_date(store: JsonlStore, dataset: Dataset, upper: date | None) -> date | None:
    """Newest partition date for a dataset, bounded above by `upper` if given."""
    dates = store.partition_dates(dataset)
    if upper is not None:
        dates = [d for d in dates if d <= upper]
    return dates[-1] if dates else None


def _load_latest(
    reader: DataReader, store: JsonlStore, dataset: Dataset, upper: date | None
) -> list[Payload]:
    latest = _latest_date(store, dataset, upper)
    if latest is None:
        return []
    return [rec.payload for rec in reader.read(dataset, since=latest, until=latest)]


def run_dashboard(
    *,
    config_dir: Path = Path("config"),
    watchlist: dict[str, list[str]] | None = None,
    data_root: Path = DEFAULT_ROOT,
    reports_root: Path = DEFAULT_REPORTS_ROOT,
    as_of: date | None,
    lang: str = DEFAULT_LANG,
    now: datetime,
) -> Path:
    """Load the latest data products, run the doctor, render and write the page.

    Read-only except for the single write of `reports/dashboard.html`. Each
    dataset picks its own latest partition (bounded above by `as_of` if given),
    so a lagging dataset degrades gracefully instead of blanking the page.
    """
    store = JsonlStore(root=data_root)
    reader = DataReader(store)

    insights = [
        Insight.model_validate(p)
        for p in _load_latest(reader, store, Dataset.INSIGHTS, as_of)
    ]
    historical = [
        HistoricalInsight.model_validate(p)
        for p in _load_latest(reader, store, Dataset.HISTORICAL, as_of)
    ]
    buckets = [
        BucketStat.model_validate(p)
        for p in _load_latest(reader, store, Dataset.EVALUATION, as_of)
    ]

    watchlist = watchlist if watchlist is not None else load_watchlist(config_dir)
    doctor_report = run_doctor(store=store, watchlist=watchlist, now=now)
    run = Manifest(root=data_root).latest_run()

    html_doc = build_dashboard_html(
        doctor_report=doctor_report,
        insights=insights,
        buckets=buckets,
        historical=historical,
        run=run,
        lang=lang,
        now=now,
    )

    out_path = reports_root / DASHBOARD_FILENAME
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.dashboard")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--data-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--reports-root", default=str(DEFAULT_REPORTS_ROOT))
    parser.add_argument("--date", help="YYYY-MM-DD upper bound (default: latest available)")
    parser.add_argument("--lang", choices=["en", "ko", "zh"], help="override sources.yaml lang")
    args = parser.parse_args(argv)

    config_dir = Path(args.config_dir)
    try:
        _, runtime_config = load_validated_sources_config(config_dir)
    except ValidationError as exc:
        return report_invalid_sources(exc)
    try:
        watchlist = load_watchlist(config_dir)
    except WatchlistConfigError as exc:
        return report_invalid_watchlist(exc)
    lang = args.lang or runtime_config.lang
    as_of = date.fromisoformat(args.date) if args.date else None
    out_path = run_dashboard(
        config_dir=config_dir,
        watchlist=watchlist,
        data_root=Path(args.data_root),
        reports_root=Path(args.reports_root),
        as_of=as_of,
        lang=lang,
        now=datetime.now(UTC),
    )
    print(f"[mimir] dashboard -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
