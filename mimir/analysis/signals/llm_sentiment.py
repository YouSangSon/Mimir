"""LLM news-sentiment signal — off-by-default seam (spec INC5).

A paid signal that classifies the *tone* of stored headlines (bullish/bearish/
neutral) and aggregates them into one directional ``SignalResult``. It augments
``NewsVolumeSignal`` (which only measures activity, always NEUTRAL).

OFF BY DEFAULT. ``build_signals()`` only constructs this when the config flag,
``ANTHROPIC_API_KEY``, and the ``anthropic`` package are all present (the package
check is skipped when a fake classifier is injected). The default pipeline makes
ZERO LLM calls and never imports ``anthropic``.

Copyright/ToS boundary (spec §8): only the already-stored ``title`` + ``summary``
(rss caps summary at 500 chars) are sent to the LLM — never full article text.

The classifier is injected (mirrors ``RssSource(parse_fn=...)``): a callable
``classify(list[str]) -> list[HeadlineVerdict]``. Tests inject a fake, so they
run with NO network, NO key, and NO real ``anthropic`` import.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Protocol

from pydantic import BaseModel, Field

from mimir.analysis.signals.base import DIRECTION_SIGN, SignalDirection, SignalResult
from mimir.core.payloads import news_payload
from mimir.core.source import Dataset, Market
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

logger = logging.getLogger(__name__)

WEIGHT = 0.8  # higher than news_volume (0.5): directional info, not mere activity
DIRECTION_EPS = 0.02  # mirror scorer.DIRECTION_EPS for the BULLISH/BEARISH cutoff
FULL_CONFIDENCE_VOLUME = 3  # headlines needed before confidence is un-downweighted


class HeadlineVerdict(BaseModel):
    """Structured per-headline classification (tool-use / parse() output)."""

    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class HeadlineClassifier(Protocol):
    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]: ...


def _mentions(rec: Record, symbol: str) -> bool:
    # Reuse news_volume's word-boundary convention so a symbol like "A"/"ON"
    # doesn't match ordinary prose. No ticker in the text -> no LLM call (the
    # free-principle / cost-guardrail intersection).
    import re

    p = news_payload(rec)
    text = (p.title or "") + " " + (p.summary or "")
    return re.search(rf"\b{re.escape(symbol)}\b", text, re.IGNORECASE) is not None


def _headline_text(rec: Record) -> str:
    # Only stored title + summary cross the wire (spec §8). join with newline.
    p = news_payload(rec)
    return f"{p.title or ''}\n{p.summary or ''}".strip()


class LlmSentimentSignal:
    """Signal-protocol-conformant LLM sentiment aggregator."""

    id = "llm_sentiment"

    def __init__(
        self,
        *,
        classifier: HeadlineClassifier,
        max_headlines: int,
        weight: float = WEIGHT,
    ) -> None:
        self._classifier = classifier
        self._max_headlines = max_headlines
        self._weight = weight

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None:
        mentions = [
            r for r in reader.read(Dataset.NEWS, since=as_of, until=as_of) if _mentions(r, symbol)
        ]
        if not mentions:
            return None

        capped = mentions[: self._max_headlines]
        unclassified = len(mentions) - len(capped)
        if unclassified:
            logger.warning(
                "signal 'llm_sentiment' for %s: capped at %d headlines; %d unclassified",
                symbol,
                self._max_headlines,
                unclassified,
            )

        texts = [_headline_text(r) for r in capped]
        try:
            verdicts = self._classifier.classify(texts)
        except Exception:
            # One bad LLM call must not crash the pipeline (source-isolation
            # spirit). Surface it loudly, then skip this symbol.
            logger.exception("signal 'llm_sentiment' classifier failed for %s; skipping", symbol)
            return None

        return self._aggregate(verdicts, unclassified)

    def _aggregate(self, verdicts: list[HeadlineVerdict], unclassified: int) -> SignalResult | None:
        if not verdicts:
            return None
        signed = [DIRECTION_SIGN[v.direction] * v.confidence for v in verdicts]
        mean_signed = sum(signed) / len(signed)

        if mean_signed > DIRECTION_EPS:
            direction = SignalDirection.BULLISH
        elif mean_signed < -DIRECTION_EPS:
            direction = SignalDirection.BEARISH
        else:
            direction = SignalDirection.NEUTRAL

        n_bull = sum(1 for v in verdicts if v.direction is SignalDirection.BULLISH)
        n_bear = sum(1 for v in verdicts if v.direction is SignalDirection.BEARISH)
        n_neutral = len(verdicts) - n_bull - n_bear

        volume_factor = min(len(verdicts) / FULL_CONFIDENCE_VOLUME, 1.0)
        confidence = (sum(v.confidence for v in verdicts) / len(verdicts)) * volume_factor

        reason = (
            f"{len(verdicts)} headlines: {n_bull} bull / {n_bear} bear / "
            f"{n_neutral} neutral; mean={mean_signed:+.2f}"
        )
        if unclassified:
            reason += f"; capped, {unclassified} unclassified"

        return SignalResult(
            signal=self.id,
            direction=direction,
            strength=min(abs(mean_signed), 1.0),
            confidence=confidence,
            reason=reason,
            weight=self._weight,
        )


class _VerdictBatch(BaseModel):
    """Structured-output wrapper: one verdict per input headline, in order."""

    verdicts: list[HeadlineVerdict]


class AnthropicHeadlineClassifier:
    """Default classifier: lazily imports ``anthropic`` and calls Haiku 4.5.

    The import is local so merely loading this module never pulls ``anthropic``
    (it is the optional ``[llm]`` extra). Constructing this without the package
    installed fails loud with an actionable message.

    Many headlines go in one call (batching reduces round-trips, not cost — the
    cost driver is headline count, capped by ``max_headlines``). ``temperature=0``
    for determinism (Haiku 4.5 supports sampling params; it does not support the
    ``effort`` parameter, so it is omitted).
    """

    MODEL = "claude-haiku-4-5"

    def __init__(self, api_key: str | None) -> None:
        try:
            import anthropic
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "llm_sentiment requires the 'anthropic' package; "
                "install it with: pip install -e '.[llm]'"
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)

    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]:  # pragma: no cover
        # Real network path — exercised only when the user opts in with a key.
        # Untested by construction (no network/key in CI); tests inject a fake
        # classifier instead (spec §7.3, AC7). mypy is blind here: anthropic is
        # not installed and ignore_missing_imports makes the client `Any`.
        prompt = (
            "Classify the market sentiment of each headline below as bullish, "
            "bearish, or neutral, with a 0..1 confidence and a one-line rationale. "
            "Return one verdict per headline, in the same order.\n\n"
            + "\n".join(f"{i + 1}. {h}" for i, h in enumerate(headlines))
        )
        response = self._client.messages.parse(
            model=self.MODEL,
            max_tokens=1024,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
            output_format=_VerdictBatch,
        )
        return list(response.parsed_output.verdicts)
