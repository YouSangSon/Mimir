from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import requests

from mimir.core.errors import FetchError
from mimir.sources.base import http_get
from mimir.sources.config import TickerCikMapRefresh
from mimir.sources.rss_catalog import load_sec_ticker_cik_map

logger = logging.getLogger(__name__)

SECONDS_PER_HOUR = 3600


def refresh_sec_ticker_cik_map(
    path: Path,
    refresh: TickerCikMapRefresh,
    *,
    user_agent: str,
    session: requests.Session | None = None,
    now: datetime | None = None,
    http_get_fn: Callable[..., requests.Response] = http_get,
) -> None:
    """Best-effort, off-by-default refresh of the local SEC ``company_tickers.json``.

    Runs as a build-time preparation step (NOT inside the RSS resolver, which keeps
    its "no network" invariant). Behavior:

    - Disabled (default) -> returns immediately; the pipeline makes zero network calls.
    - Local file still within ``max_age_hours`` -> returns without a request (TTL gate).
    - Otherwise a conditional GET (ETag / ``If-None-Match``) with a fair-access
      User-Agent; ``304`` keeps the file, ``200`` adopts it only if it is a JSON object.
    - Any failure (network, non-JSON, non-object) keeps the existing file and logs a
      warning, so a refresh problem never breaks collection.

    See docs/superpowers/specs/2026-06-19-sec-ticker-cik-map-cache-design.md.
    """
    if not refresh.enabled:
        return
    now = now or datetime.now(UTC)
    if path.exists():
        age_hours = (now.timestamp() - path.stat().st_mtime) / SECONDS_PER_HOUR
        if age_hours < refresh.max_age_hours:
            return
    etag_path = path.with_name(path.name + ".etag")
    headers = {"User-Agent": user_agent}
    if etag_path.exists():
        headers["If-None-Match"] = etag_path.read_text(encoding="utf-8").strip()
    session = session or requests.Session()
    try:
        resp = http_get_fn(refresh.url, session=session, headers=headers)
    except FetchError as exc:
        logger.warning("SEC ticker CIK map refresh failed (%s); keeping existing file", exc)
        return
    if resp.status_code == 304:
        return
    # Adopt the download only if it passes the SAME validation the loader applies at
    # build time (JSON object + per-entry ticker/cik_str + no ambiguity), so a broken
    # download never overwrites a good cache. Validate a temp sibling, then replace
    # atomically.
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(resp.text, encoding="utf-8")
    try:
        load_sec_ticker_cik_map(tmp_path)
    except ValueError as exc:
        logger.warning(
            "SEC ticker CIK map refresh downloaded an invalid map (%s); keeping existing file",
            exc,
        )
        tmp_path.unlink(missing_ok=True)
        return
    os.replace(tmp_path, path)
    etag = resp.headers.get("ETag")
    if etag:
        etag_path.write_text(etag, encoding="utf-8")
