from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from mimir.core.payloads import news_payload
from mimir.storage.schema import Record

LEFT_BOUNDARY = r"(?<![\w])"
RIGHT_BOUNDARY = r"(?![\w])"


class NewsMentionMatcher:
    def __init__(self, aliases: Mapping[str, Sequence[str]] | None = None) -> None:
        self._aliases = self._normalize_aliases(aliases or {})

    def _normalize_aliases(
        self, aliases: Mapping[str, Sequence[str]]
    ) -> dict[str, tuple[str, ...]]:
        normalized: dict[str, tuple[str, ...]] = {}
        for symbol, values in aliases.items():
            if isinstance(values, str):
                raise TypeError(
                    f"aliases for {symbol!r} must be a sequence of strings, not a string"
                )
            seen: set[str] = set()
            terms: list[str] = []
            for raw_term in values:
                term = raw_term.strip()
                if not term:
                    continue
                key = term.casefold()
                if key in seen:
                    continue
                seen.add(key)
                terms.append(term)
            normalized[symbol] = tuple(terms)
        return normalized

    def terms_for(self, symbol: str) -> tuple[str, ...]:
        seen: set[str] = set()
        terms: list[str] = []
        for raw_term in (symbol, *self._aliases.get(symbol, ())):
            term = raw_term.strip()
            if not term:
                continue
            key = term.casefold()
            if key in seen:
                continue
            seen.add(key)
            terms.append(term)
        return tuple(terms)

    def mentions(self, record: Record, symbol: str) -> bool:
        if record.symbol == symbol:
            return True
        payload = news_payload(record)
        text = f"{payload.title or ''} {payload.summary or ''}"
        return any(self._matches_term(text, term) for term in self.terms_for(symbol))

    def _matches_term(self, text: str, term: str) -> bool:
        pattern = f"{LEFT_BOUNDARY}{re.escape(term)}{RIGHT_BOUNDARY}"
        return re.search(pattern, text, re.IGNORECASE) is not None
