from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

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
