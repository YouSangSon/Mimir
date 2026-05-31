from __future__ import annotations


class MimirError(Exception):
    """Base class for all Mimir domain errors."""


class FetchError(MimirError):
    """A source failed to fetch data from its upstream."""


class NormalizationError(MimirError):
    """A raw record could not be normalized into a valid Record."""
