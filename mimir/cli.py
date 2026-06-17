from __future__ import annotations

import sys
from collections.abc import Callable

from mimir import analyze, backfill, collect, dashboard, deliver, evaluate, history, run
from mimir.doctor import doctor_cli

Command = Callable[[list[str] | None], int]

COMMANDS: dict[str, Command] = {
    "collect": collect.main,
    "backfill": backfill.main,
    "analyze": analyze.main,
    "deliver": deliver.main,
    "history": history.main,
    "doctor": doctor_cli.main,
    "evaluate": evaluate.main,
    "dashboard": dashboard.main,
    "run": run.main,
}


def _help_text() -> str:
    lines = [
        "Usage: mimir <command> [args...]",
        "",
        "Commands:",
    ]
    for name in sorted(COMMANDS):
        lines.append(f"  {name}")
    lines.extend(
        [
            "",
            "Examples:",
            "  mimir run --cadence daily",
            "  mimir collect --cadence daily",
            "  mimir dashboard --reports-root reports",
            "",
            "Each command also supports the legacy module path, e.g. "
            "python -m mimir.collect.",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(_help_text())
        return 0

    command, command_args = args[0], args[1:]
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"[mimir] unknown command: {command}", file=sys.stderr)
        print(_help_text(), file=sys.stderr)
        return 2

    return handler(command_args)


if __name__ == "__main__":
    sys.exit(main())
