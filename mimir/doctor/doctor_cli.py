from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from mimir.config import load_watchlist
from mimir.doctor.engine import run_doctor
from mimir.doctor.report import DoctorReport, Severity
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.paths import DEFAULT_ROOT


def _now() -> datetime:
    """Injection seam: only the CLI boundary reads the wall clock (§5)."""
    return datetime.now(UTC)


def _emit_text(report: DoctorReport) -> str:
    lines = [f"mimir doctor — {report.worst.value.upper()} ({report.data_root})"]
    ordered = sorted(
        report.findings,
        key=lambda f: {"critical": 0, "warn": 1, "ok": 2}[f.severity.value],
    )
    for f in ordered:
        scope = f" {f.scope}" if f.scope else ""
        lines.append(f"  [{f.severity.value}] {f.dataset.value}{scope}: {f.message}")
    if not report.findings:
        lines.append("  all clear")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.doctor")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--data-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument(
        "--strict", action="store_true",
        help="escalate WARN to a non-zero exit (default: only CRITICAL is non-zero)",
    )
    args = parser.parse_args(argv)

    watchlist = load_watchlist(Path(args.config_dir))
    store = JsonlStore(root=Path(args.data_root))
    report = run_doctor(store=store, watchlist=watchlist, now=_now())

    if args.format == "json":
        print(report.model_dump_json())
    else:
        print(_emit_text(report))

    code = report.exit_code
    if args.strict and report.worst is Severity.WARN:
        code = 1
    return code
