from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

from mimir import cli

EXPECTED_SCRIPTS = {
    "mimir": "mimir.cli:main",
    "mimir.collect": "mimir.collect:main",
    "mimir.backfill": "mimir.backfill:main",
    "mimir.analyze": "mimir.analyze:main",
    "mimir.deliver": "mimir.deliver:main",
    "mimir.history": "mimir.history:main",
    "mimir.doctor": "mimir.doctor.doctor_cli:main",
    "mimir.evaluate": "mimir.evaluate:main",
    "mimir.dashboard": "mimir.dashboard:main",
    "mimir.run": "mimir.run:main",
}


def _pyproject() -> dict[str, object]:
    return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))


def test_pyproject_declares_cli_scripts() -> None:
    scripts = _pyproject()["project"]["scripts"]

    for name, target in EXPECTED_SCRIPTS.items():
        assert scripts[name] == target


def test_cli_script_targets_are_importable_callables() -> None:
    for target in EXPECTED_SCRIPTS.values():
        module_name, function_name = target.split(":", maxsplit=1)
        module = importlib.import_module(module_name)

        assert callable(getattr(module, function_name))


def test_unified_cli_and_dotted_aliases_stay_in_sync() -> None:
    scripts = _pyproject()["project"]["scripts"]
    dotted_aliases = {
        name.removeprefix("mimir."): target
        for name, target in scripts.items()
        if name.startswith("mimir.")
    }

    assert set(dotted_aliases) == set(cli.COMMANDS)
    for command, handler in cli.COMMANDS.items():
        assert dotted_aliases[command] == f"{handler.__module__}:{handler.__name__}"
