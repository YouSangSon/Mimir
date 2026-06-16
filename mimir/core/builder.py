from __future__ import annotations

import importlib.metadata
import importlib.util
import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from mimir.core.source import Source
from mimir.settings import Settings
from mimir.sources.config import SourcesConfig
from mimir.sources.dart import DartSource
from mimir.sources.ecos import EcosSource
from mimir.sources.fred import FredSource
from mimir.sources.pykrx_source import PykrxSource
from mimir.sources.rss import RssSource
from mimir.sources.sec_edgar import SecEdgarSource
from mimir.sources.stooq import StooqSource

logger = logging.getLogger(__name__)
SOURCE_ENTRY_POINT_GROUP = "mimir.sources"


@dataclass(frozen=True)
class SourceSpec:
    id: str
    factory: Callable[[Settings, SourcesConfig], Source]
    required_secret_attr: str | None = None
    required_secret_name: str | None = None
    required_module: str | None = None
    missing_module_hint: str | None = None


def _required_secret(value: str | None, name: str) -> str:
    if not value:
        raise ValueError(f"required secret {name} is not set")
    return value


BUILTIN_SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec(
        "sec_edgar",
        lambda settings, cfg: SecEdgarSource(user_agent=settings.sec_user_agent),
    ),
    SourceSpec("rss", lambda settings, cfg: RssSource(feeds=cfg.rss_feeds)),
    SourceSpec(
        "stooq",
        lambda settings, cfg: StooqSource(
            api_key=_required_secret(settings.stooq_api_key, "STOOQ_API_KEY")
        ),
        required_secret_attr="stooq_api_key",
        required_secret_name="STOOQ_API_KEY",
    ),
    SourceSpec(
        "dart",
        lambda settings, cfg: DartSource(
            api_key=_required_secret(settings.dart_api_key, "DART_API_KEY")
        ),
        required_secret_attr="dart_api_key",
        required_secret_name="DART_API_KEY",
    ),
    SourceSpec(
        "fred",
        lambda settings, cfg: FredSource(
            api_key=_required_secret(settings.fred_api_key, "FRED_API_KEY"),
            series=cfg.fred_series,
        ),
        required_secret_attr="fred_api_key",
        required_secret_name="FRED_API_KEY",
    ),
    SourceSpec(
        "ecos",
        lambda settings, cfg: EcosSource(
            api_key=_required_secret(settings.ecos_api_key, "ECOS_API_KEY"),
            series=cfg.ecos_series,
        ),
        required_secret_attr="ecos_api_key",
        required_secret_name="ECOS_API_KEY",
    ),
    SourceSpec(
        "pykrx",
        lambda settings, cfg: PykrxSource(),
        required_module="pykrx",
        missing_module_hint="package not installed (pip install -e '.[kr]')",
    ),
)

CONFIGURABLE_BUILTIN_SOURCE_IDS = frozenset({"ecos", "fred", "rss"})


def _validate_unique_source_ids(specs: Sequence[SourceSpec]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for spec in specs:
        if spec.id in seen:
            duplicates.add(spec.id)
        seen.add(spec.id)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate source id(s): {joined}")


def _entry_points_for_group(group: str) -> tuple[importlib.metadata.EntryPoint, ...]:
    entry_points: Iterable[importlib.metadata.EntryPoint]
    try:
        entry_points = importlib.metadata.entry_points(group=group)
    except TypeError:
        all_entry_points = importlib.metadata.entry_points()
        if hasattr(all_entry_points, "select"):
            entry_points = all_entry_points.select(group=group)
        elif isinstance(all_entry_points, Mapping):
            entry_points = cast(
                Iterable[importlib.metadata.EntryPoint],
                all_entry_points.get(group, ()),
            )
        else:
            entry_points = ()
    return tuple(sorted(entry_points, key=lambda entry_point: entry_point.name))


def _source_specs_from_entry_point(name: str, loaded: object) -> tuple[SourceSpec, ...]:
    if isinstance(loaded, SourceSpec):
        if loaded.id != name:
            raise ValueError(f"entry point {name!r} loaded source spec {loaded.id!r}")
        return (loaded,)
    if isinstance(loaded, Sequence) and not isinstance(loaded, str | bytes):
        specs = tuple(loaded)
        for spec in specs:
            if not isinstance(spec, SourceSpec):
                raise ValueError(f"entry point {name!r} must load SourceSpec objects")
        return specs
    raise ValueError(f"entry point {name!r} must load SourceSpec objects")


def _load_entry_point_source_specs(
    group: str = SOURCE_ENTRY_POINT_GROUP,
) -> tuple[SourceSpec, ...]:
    specs: list[SourceSpec] = []
    for entry_point in _entry_points_for_group(group):
        try:
            loaded = entry_point.load()
        except Exception as exc:
            logger.warning(
                "skipping source plugin '%s': failed to load entry point: %s",
                entry_point.name,
                exc,
            )
            continue
        specs.extend(_source_specs_from_entry_point(entry_point.name, loaded))
    return tuple(specs)


def _build_sources_from_specs(
    settings: Settings,
    config: SourcesConfig,
    specs: Sequence[SourceSpec],
) -> list[Source]:
    _validate_unique_source_ids(specs)
    _warn_for_unmatched_plugin_settings(config, specs)
    sources: list[Source] = []
    for spec in specs:
        if spec.required_secret_attr and not getattr(settings, spec.required_secret_attr):
            logger.warning(
                "skipping source '%s': %s is not set",
                spec.id,
                spec.required_secret_name or spec.required_secret_attr,
            )
            continue
        if spec.required_module and importlib.util.find_spec(spec.required_module) is None:
            logger.warning("skipping source '%s': %s", spec.id, spec.missing_module_hint)
            continue
        source = spec.factory(settings, config)
        if source.meta.id != spec.id:
            raise ValueError(f"source spec id {spec.id!r} built source id {source.meta.id!r}")
        sources.append(source)
    return sources


def _warn_for_unmatched_plugin_settings(
    config: SourcesConfig, specs: Sequence[SourceSpec]
) -> None:
    source_ids = {spec.id for spec in specs}
    builtin_ids = {spec.id for spec in BUILTIN_SOURCE_SPECS}
    for source_id in sorted(config.plugin_settings):
        if source_id in builtin_ids:
            if source_id in CONFIGURABLE_BUILTIN_SOURCE_IDS:
                logger.warning(
                    "source plugin config '%s' targets built-in source '%s'; "
                    "use sources.%s instead",
                    source_id,
                    source_id,
                    source_id,
                )
            else:
                logger.warning(
                    "source plugin config '%s' targets built-in source '%s'; "
                    "built-in sources do not read sources.plugins",
                    source_id,
                    source_id,
                )
        elif source_id not in source_ids:
            logger.warning(
                "source plugin config '%s' has no matching source spec",
                source_id,
            )


def build_sources(settings: Settings, config: SourcesConfig | None = None) -> list[Source]:
    if "@" not in settings.sec_user_agent:
        logger.warning(
            "MIMIR_SEC_USER_AGENT has no contact email; SEC EDGAR may return 403. "
            "Set it to e.g. 'Your Name you@example.com'."
    )
    cfg = config or SourcesConfig()
    specs = (*BUILTIN_SOURCE_SPECS, *_load_entry_point_source_specs())
    return _build_sources_from_specs(settings, cfg, specs)
