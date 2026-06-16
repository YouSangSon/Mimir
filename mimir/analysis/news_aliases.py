from __future__ import annotations

from collections.abc import Iterable, Mapping

DEFAULT_NEWS_ALIASES: dict[str, tuple[str, ...]] = {
    "AAPL": ("Apple", "Apple Inc."),
    "MSFT": ("Microsoft", "Microsoft Corp."),
    "NVDA": ("NVIDIA", "Nvidia Corporation"),
    "005930": ("Samsung Electronics", "삼성전자"),
}


def merge_news_aliases(
    configured: Mapping[str, Iterable[str]] | None,
    *,
    include_defaults: bool = True,
) -> dict[str, tuple[str, ...]]:
    aliases: dict[str, tuple[str, ...]] = {}
    if include_defaults:
        aliases.update(DEFAULT_NEWS_ALIASES)
    if not configured:
        return aliases

    for symbol, terms in configured.items():
        if isinstance(terms, str):
            raise TypeError(
                f"aliases for {symbol!r} must be an iterable of strings, not a string"
            )
        existing = aliases.get(symbol, ())
        aliases[symbol] = _dedupe_terms((*existing, *terms))
    return aliases


def _dedupe_terms(terms: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    merged: list[str] = []
    for raw in terms:
        term = raw.strip()
        if not term:
            continue
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        merged.append(term)
    return tuple(merged)
