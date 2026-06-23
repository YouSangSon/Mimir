from __future__ import annotations

import importlib.metadata
import importlib.util
import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mimir.analysis.news_aliases import merge_news_aliases
from mimir.analysis.signals.base import Signal
from mimir.analysis.signals.filing_event import FilingEventSignal
from mimir.analysis.signals.macro_regime import MacroRegimeSignal
from mimir.analysis.signals.news_volume import NewsVolumeSignal
from mimir.analysis.signals.price_momentum import PriceMomentumSignal
from mimir.settings import Settings
from mimir.sources.config import SourcesConfig

if TYPE_CHECKING:
    # Annotation-only: the classifier type lives in llm_sentiment, which lazily
    # imports `anthropic`. A runtime import here would defeat the off-by-default
    # invariant (loading the builder must never pull anthropic).
    from mimir.analysis.signals.llm_sentiment import HeadlineClassifier

logger = logging.getLogger(__name__)
SIGNAL_ENTRY_POINT_GROUP = "mimir.analysis_signals"


@dataclass(frozen=True)
class SignalSpec:
    id: str
    factory: Callable[[Settings, SourcesConfig], Signal]
    required_secret_attr: str | None = None
    required_secret_name: str | None = None
    required_module: str | None = None
    missing_module_hint: str | None = None


def _news_aliases(cfg: SourcesConfig) -> dict[str, tuple[str, ...]]:
    return merge_news_aliases(
        cfg.news_aliases,
        include_defaults=cfg.use_default_news_aliases,
    )


BUILTIN_SIGNAL_SPECS: tuple[SignalSpec, ...] = (
    SignalSpec("filing_event", lambda settings, cfg: FilingEventSignal()),
    SignalSpec("news_volume", lambda settings, cfg: NewsVolumeSignal(aliases=_news_aliases(cfg))),
    SignalSpec("price_momentum", lambda settings, cfg: PriceMomentumSignal()),
    SignalSpec(
        "macro_regime",
        lambda settings, cfg: MacroRegimeSignal(rate_series=cfg.macro_regime_rate_series),
    ),
)


def _validate_unique_signal_ids(specs: Sequence[SignalSpec]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for spec in specs:
        if spec.id in seen:
            duplicates.add(spec.id)
        seen.add(spec.id)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate signal id(s): {joined}")


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


def _signal_specs_from_entry_point(name: str, loaded: object) -> tuple[SignalSpec, ...]:
    if isinstance(loaded, SignalSpec):
        if loaded.id != name:
            raise ValueError(f"entry point {name!r} loaded signal spec {loaded.id!r}")
        return (loaded,)
    if isinstance(loaded, Sequence) and not isinstance(loaded, str | bytes):
        specs = tuple(loaded)
        for spec in specs:
            if not isinstance(spec, SignalSpec):
                raise ValueError(f"entry point {name!r} must load SignalSpec objects")
        return specs
    raise ValueError(f"entry point {name!r} must load SignalSpec objects")


def _load_entry_point_signal_specs(
    group: str = SIGNAL_ENTRY_POINT_GROUP,
) -> tuple[SignalSpec, ...]:
    specs: list[SignalSpec] = []
    for entry_point in _entry_points_for_group(group):
        try:
            loaded = entry_point.load()
        except Exception as exc:
            logger.warning(
                "skipping analysis signal plugin '%s': failed to load entry point: %s",
                entry_point.name,
                exc,
            )
            continue
        specs.extend(_signal_specs_from_entry_point(entry_point.name, loaded))
    _validate_unique_signal_ids(specs)
    return tuple(specs)


def load_signal_specs(
    group: str = SIGNAL_ENTRY_POINT_GROUP,
) -> tuple[SignalSpec, ...]:
    specs = (*BUILTIN_SIGNAL_SPECS, *_load_entry_point_signal_specs(group))
    _validate_unique_signal_ids(specs)
    return specs


def _warn_for_unmatched_analysis_plugin_settings(
    config: SourcesConfig, specs: Sequence[SignalSpec]
) -> None:
    signal_ids = {spec.id for spec in specs}
    for signal_id in sorted(config.analysis_plugin_settings):
        if signal_id not in signal_ids:
            logger.warning(
                "analysis plugin config '%s' has no matching signal spec",
                signal_id,
            )


def _build_signals_from_specs(
    settings: Settings,
    config: SourcesConfig,
    specs: Sequence[SignalSpec],
    *,
    build_unconfigured: bool = False,
    warn_unmatched: bool = True,
) -> list[Signal]:
    _validate_unique_signal_ids(specs)
    if warn_unmatched:
        _warn_for_unmatched_analysis_plugin_settings(config, specs)
    signals: list[Signal] = []
    for spec in specs:
        if not build_unconfigured and spec.id not in config.analysis_plugin_settings:
            continue
        if spec.required_secret_attr and not getattr(settings, spec.required_secret_attr):
            logger.warning(
                "skipping analysis signal '%s': %s is not set",
                spec.id,
                spec.required_secret_name or spec.required_secret_attr,
            )
            continue
        if spec.required_module:
            try:
                module_spec = importlib.util.find_spec(spec.required_module)
            except ModuleNotFoundError:
                module_spec = None
            if module_spec is None:
                logger.warning(
                    "skipping analysis signal '%s': %s",
                    spec.id,
                    spec.missing_module_hint,
                )
                continue
        signal = spec.factory(settings, config)
        if signal.id != spec.id:
            raise ValueError(f"signal spec id {spec.id!r} built signal id {signal.id!r}")
        signals.append(signal)
    return signals


def build_signals(
    config: SourcesConfig | None = None,
    settings: Settings | None = None,
    *,
    classifier: HeadlineClassifier | None = None,
) -> list[Signal]:
    """Build the analysis signal set.

    Off-by-default (INC5): the paid LLM news-sentiment signal is appended ONLY
    when config enables it AND a key is present AND `anthropic` is installed (the
    package check is bypassed when a fake `classifier` is injected for tests).
    With no args, returns exactly today's four signals and never imports
    `anthropic`.
    """
    cfg = config or SourcesConfig()
    settings = settings or Settings()
    signals = _build_signals_from_specs(
        settings,
        cfg,
        BUILTIN_SIGNAL_SPECS,
        build_unconfigured=True,
        warn_unmatched=False,
    )
    if cfg.analysis_plugin_settings:
        plugin_specs = _load_entry_point_signal_specs()
        _validate_unique_signal_ids((*BUILTIN_SIGNAL_SPECS, *plugin_specs))
        signals.extend(_build_signals_from_specs(settings, cfg, plugin_specs))
    if _llm_sentiment_enabled(cfg, settings, classifier):
        # Local import — the default path never enters this branch, so loading
        # this module never pulls `anthropic` (off-by-default invariant).
        from mimir.analysis.signals.llm_sentiment import (
            AnthropicHeadlineClassifier,
            LlmSentimentSignal,
        )

        signals.append(
            LlmSentimentSignal(
                classifier=classifier or AnthropicHeadlineClassifier(settings.anthropic_api_key),
                max_headlines=cfg.llm_sentiment_max_headlines,
                aliases=_news_aliases(cfg),
            )
        )
    return signals


def _llm_sentiment_enabled(
    cfg: SourcesConfig, settings: Settings, classifier: HeadlineClassifier | None
) -> bool:
    if not cfg.llm_sentiment_enabled:
        return False
    if not settings.anthropic_api_key:
        logger.warning(
            "llm_sentiment_enabled=true but ANTHROPIC_API_KEY is not set; signal disabled"
        )
        return False
    # A fake classifier (tests) needs no SDK; only the real path requires the package.
    if classifier is None and importlib.util.find_spec("anthropic") is None:
        logger.warning(
            "llm_sentiment_enabled=true but 'anthropic' is not installed "
            "(pip install -e '.[llm]'); signal disabled"
        )
        return False
    return True
