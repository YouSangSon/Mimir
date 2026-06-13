from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

DEFAULT_CONFIG_DIR = Path("config")


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_watchlist(config_dir: Path = DEFAULT_CONFIG_DIR) -> dict[str, list[str]]:
    wl = load_yaml(config_dir / "watchlist.yaml")
    return {"us": list(wl.get("us", [])), "kr": list(wl.get("kr", []))}


def load_sources_config(config_dir: Path = DEFAULT_CONFIG_DIR) -> dict[str, Any]:
    return load_yaml(config_dir / "sources.yaml")


def report_invalid_sources(exc: ValidationError) -> int:
    """Turn a malformed ``sources.yaml`` ``ValidationError`` into a friendly
    ``[mimir] invalid sources.yaml: <detail>`` message and exit code 1 (spec §5),
    instead of a raw pydantic traceback. Call from a CLI ``main``'s except clause."""
    print(f"[mimir] invalid sources.yaml: {exc}", file=sys.stderr)
    return 1
