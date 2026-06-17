from __future__ import annotations

import sys
from copy import deepcopy
from os import PathLike
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from mimir.sources.config import SourcesConfig, parse_sources_config

DEFAULT_CONFIG_DIR = Path("config")


class SourcesConfigError(ValueError):
    """A valid-looking ``sources.yaml`` failed while constructing sources."""


class SecTickerCikMapConfigError(SourcesConfigError):
    """The configured SEC ticker CIK mapping file could not be used."""


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_watchlist(config_dir: Path = DEFAULT_CONFIG_DIR) -> dict[str, list[str]]:
    wl = load_yaml(config_dir / "watchlist.yaml")
    return {"us": list(wl.get("us", [])), "kr": list(wl.get("kr", []))}


def load_sources_config(config_dir: Path = DEFAULT_CONFIG_DIR) -> dict[str, Any]:
    return load_yaml(config_dir / "sources.yaml")


def load_validated_sources_config(
    config_dir: Path = DEFAULT_CONFIG_DIR,
) -> tuple[dict[str, Any], SourcesConfig]:
    raw = _resolve_sources_config_paths(load_sources_config(config_dir), config_dir)
    return raw, parse_sources_config(raw)


def _resolve_sources_config_paths(raw: dict[str, Any], config_dir: Path) -> dict[str, Any]:
    resolved = deepcopy(raw)
    sources_block = resolved.get("sources")
    if not isinstance(sources_block, dict):
        return resolved
    rss_block = sources_block.get("rss")
    if not isinstance(rss_block, dict):
        return resolved
    sec_block = rss_block.get("sec")
    if not isinstance(sec_block, dict):
        return resolved
    path_value = sec_block.get("ticker_cik_map_path")
    if path_value is None:
        return resolved
    if not isinstance(path_value, str | PathLike):
        return resolved
    path = Path(path_value)
    if not path.is_absolute():
        sec_block["ticker_cik_map_path"] = str(config_dir / path)
    return resolved


def report_invalid_sources(exc: ValidationError | SourcesConfigError) -> int:
    """Turn a malformed ``sources.yaml`` ``ValidationError`` into a friendly
    ``[mimir] invalid sources.yaml: <detail>`` message and exit code 1 (spec §5),
    instead of a raw pydantic traceback. Call from a CLI ``main``'s except clause."""
    print(f"[mimir] invalid sources.yaml: {exc}", file=sys.stderr)
    return 1
