from __future__ import annotations

import time
from collections.abc import Callable


class Throttle:
    DEFAULT_MAX_PER_SECOND = 1.0

    def __init__(
        self,
        max_per_second: float | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        rate = max_per_second or self.DEFAULT_MAX_PER_SECOND
        self._min_interval = 1.0 / rate
        self._sleep = sleep
        self._monotonic = monotonic
        self._last: float | None = None

    def wait(self) -> None:
        now = self._monotonic()
        if self._last is not None:
            elapsed = now - self._last
            if elapsed < self._min_interval:
                self._sleep(self._min_interval - elapsed)
        self._last = self._monotonic()
