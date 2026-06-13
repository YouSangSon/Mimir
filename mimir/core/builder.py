from __future__ import annotations

import importlib.util
import logging

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


def build_sources(settings: Settings, config: SourcesConfig | None = None) -> list[Source]:
    # Keyless (no signup): SEC EDGAR (UA only) and RSS (official feeds).
    if "@" not in settings.sec_user_agent:
        logger.warning(
            "MIMIR_SEC_USER_AGENT has no contact email; SEC EDGAR may return 403. "
            "Set it to e.g. 'Your Name you@example.com'."
        )
    cfg = config or SourcesConfig()
    sources: list[Source] = [
        SecEdgarSource(user_agent=settings.sec_user_agent),
        RssSource(feeds=cfg.rss_feeds),
    ]
    if settings.stooq_api_key:
        sources.append(StooqSource(api_key=settings.stooq_api_key))
    else:
        logger.warning("skipping source 'stooq': STOOQ_API_KEY is not set")
    if settings.dart_api_key:
        sources.append(DartSource(api_key=settings.dart_api_key))
    else:
        logger.warning("skipping source 'dart': DART_API_KEY is not set")
    if settings.fred_api_key:
        sources.append(FredSource(api_key=settings.fred_api_key, series=cfg.fred_series))
    else:
        logger.warning("skipping source 'fred': FRED_API_KEY is not set")
    if settings.ecos_api_key:
        sources.append(EcosSource(api_key=settings.ecos_api_key, series=cfg.ecos_series))
    else:
        logger.warning("skipping source 'ecos': ECOS_API_KEY is not set")
    # pykrx is GRAY and optional (heavy deps). Registry's gray_enabled also gates it.
    if importlib.util.find_spec("pykrx") is not None:
        sources.append(PykrxSource())
    else:
        logger.warning("skipping source 'pykrx': package not installed (pip install -e '.[kr]')")
    return sources
