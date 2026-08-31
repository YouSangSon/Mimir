from __future__ import annotations

import sys
from copy import deepcopy
from os import PathLike
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError, field_validator

from mimir.sources.config import RuntimeSourcesConfig, parse_runtime_sources_config

DEFAULT_CONFIG_DIR = Path("config")


class SourcesConfigError(ValueError):
    """A valid-looking ``sources.yaml`` failed while constructing sources."""


class SecTickerCikMapConfigError(SourcesConfigError):
    """The configured SEC ticker CIK mapping file could not be used."""


class WatchlistConfigError(ValueError):
    """The configured watchlist.yaml could not be used."""


class _WatchlistConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    us: list[StrictStr] = Field(default_factory=list)
    kr: list[StrictStr] = Field(default_factory=list)

    @field_validator("us", "kr")
    @classmethod
    def _normalize_symbols(cls, value: list[str]) -> list[str]:
        symbols = [symbol.strip() for symbol in value]
        if any(not symbol for symbol in symbols):
            raise ValueError("watchlist symbols must not be blank")
        return symbols


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_watchlist(config_dir: Path = DEFAULT_CONFIG_DIR) -> dict[str, list[str]]:
    path = config_dir / "watchlist.yaml"
    try:
        cfg = _WatchlistConfig.model_validate(load_yaml(path))
    except ValidationError as exc:
        raise WatchlistConfigError(f"{path}: {exc}") from exc
    return cfg.model_dump()


def load_sources_config(config_dir: Path = DEFAULT_CONFIG_DIR) -> Any:
    path = config_dir / "sources.yaml"
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {} if loaded is None else loaded


def load_validated_sources_config(
    config_dir: Path = DEFAULT_CONFIG_DIR,
) -> tuple[dict[str, Any], RuntimeSourcesConfig]:
    raw = _resolve_sources_config_paths(load_sources_config(config_dir), config_dir)
    return raw, parse_runtime_sources_config(raw)


def _resolve_sources_config_paths(raw: Any, config_dir: Path) -> Any:
    if not isinstance(raw, dict):
        return raw
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


def report_invalid_watchlist(exc: WatchlistConfigError) -> int:
    print(f"[mimir] invalid watchlist.yaml: {exc}", file=sys.stderr)
    return 1
