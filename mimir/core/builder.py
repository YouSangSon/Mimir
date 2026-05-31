from __future__ import annotations

import logging

from mimir.core.source import Source
from mimir.settings import Settings
from mimir.sources.dart import DartSource
from mimir.sources.sec_edgar import SecEdgarSource
from mimir.sources.stooq import StooqSource

logger = logging.getLogger(__name__)


def build_sources(settings: Settings) -> list[Source]:
    sources: list[Source] = [
        StooqSource(),
        SecEdgarSource(user_agent=settings.sec_user_agent),
    ]
    if settings.dart_api_key:
        sources.append(DartSource(api_key=settings.dart_api_key))
    else:
        logger.warning("skipping source 'dart': DART_API_KEY is not set")
    return sources
