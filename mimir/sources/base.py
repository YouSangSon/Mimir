from __future__ import annotations

import time
from typing import Any, Callable

import requests

from mimir.core.errors import FetchError
from mimir.core.source import SourceMeta
from mimir.core.throttle import Throttle

DEFAULT_TIMEOUT = 15


def http_get(
    url: str,
    *,
    session: requests.Session,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = 2,
    backoff: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, headers=headers, params=params, timeout=timeout)
        except requests.RequestException as exc:
            last_exc = exc
        else:
            if resp.status_code < 400:
                return resp
            if 400 <= resp.status_code < 500:
                raise FetchError(f"{url} -> HTTP {resp.status_code}")
            last_exc = FetchError(f"{url} -> HTTP {resp.status_code}")
        if attempt < max_retries:
            sleep(backoff * (2**attempt))
    raise FetchError(f"GET failed after retries: {url}") from last_exc


class BaseSource:
    meta: SourceMeta

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        throttle: Throttle | None = None,
    ) -> None:
        self._session = session or requests.Session()
        self._throttle = throttle or Throttle(self.meta.rate_limit.max_per_second)

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        self._throttle.wait()
        return http_get(url, session=self._session, headers=headers, params=params)
