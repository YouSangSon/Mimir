from __future__ import annotations

import importlib.util
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

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


def _build_sources_from_specs(
    settings: Settings,
    config: SourcesConfig,
    specs: Sequence[SourceSpec],
) -> list[Source]:
    _validate_unique_source_ids(specs)
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


def build_sources(settings: Settings, config: SourcesConfig | None = None) -> list[Source]:
    if "@" not in settings.sec_user_agent:
        logger.warning(
            "MIMIR_SEC_USER_AGENT has no contact email; SEC EDGAR may return 403. "
            "Set it to e.g. 'Your Name you@example.com'."
        )
    cfg = config or SourcesConfig()
    return _build_sources_from_specs(settings, cfg, BUILTIN_SOURCE_SPECS)
