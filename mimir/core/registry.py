from __future__ import annotations

from mimir.core.source import Cadence, LegalStatus, Source


class Registry:
    def __init__(
        self,
        sources: list[Source],
        *,
        gray_enabled: bool = True,
        disabled_ids: set[str] | None = None,
    ) -> None:
        self._sources = sources
        self._gray_enabled = gray_enabled
        self._disabled_ids = disabled_ids or set()

    def due(self, cadence: Cadence) -> list[Source]:
        selected: list[Source] = []
        for source in self._sources:
            meta = source.meta
            if meta.cadence != cadence:
                continue
            if meta.id in self._disabled_ids:
                continue
            if not self._gray_enabled and meta.legal_status is LegalStatus.GRAY:
                continue
            selected.append(source)
        return selected
