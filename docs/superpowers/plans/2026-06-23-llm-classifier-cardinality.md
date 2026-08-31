# LLM Classifier Cardinality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make opt-in `llm_sentiment` skip malformed classifier batches whose verdict count does not match the headline count.

**Architecture:** `LlmSentimentSignal.evaluate()` already isolates classifier exceptions by returning `None`. This plan adds the same fail-closed behavior for non-exception structured-output drift, before `_aggregate()` can turn a mismatched batch into a score.

**Tech Stack:** Python 3.14, pytest, pydantic, Mimir `SignalResult` contract, fake classifier tests with no network and no real `anthropic` import.

## Global Constraints

- Preserve `llm_sentiment_enabled: false` as the default.
- Do not import `anthropic` on the default path.
- Do not add network calls, retries, storage schema, or a cache.
- Only the already-stored title and summary may be sent to the classifier.
- A malformed LLM batch must skip only the current `llm_sentiment` result; it must not crash the pipeline.
- `uv.lock` is a pre-existing untracked file and must not be edited, staged, or removed.

---

## File Structure

- Modify `tests/analysis/signals/test_llm_sentiment.py`: add fake classifiers/tests for too few and too many verdicts.
- Modify `mimir/analysis/signals/llm_sentiment.py`: add the length check after `classify()` and before `_aggregate()`.
- Modify `docs/reference/analysis/scoring.md`: document malformed batch skip behavior.
- Modify `docs/architecture/improvement-catalog.md`: record AN2 under analysis depth and the roadmap map.
- Modify `docs/decisions/tech-spec/README.md`: add the AN2 spec to the analysis index.
- Update `.git/sdd/progress.md` after verification because this goal uses the SDD local ledger.

## Task 1: LLM Classifier Cardinality Guard

**Files:**
- Modify: `tests/analysis/signals/test_llm_sentiment.py`
- Modify: `mimir/analysis/signals/llm_sentiment.py`
- Modify: `docs/reference/analysis/scoring.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/decisions/tech-spec/README.md`

**Interfaces:**
- Consumes: `HeadlineClassifier.classify(self, headlines: list[str]) -> list[HeadlineVerdict]`
- Consumes: `LlmSentimentSignal.evaluate(symbol, market, as_of, reader) -> SignalResult | None`
- Produces: warning + `None` when `len(verdicts) != len(headlines)`

- [ ] **Step 1: Add a fake classifier that returns the wrong number of verdicts**

Add this test helper near `BoomClassifier` in `tests/analysis/signals/test_llm_sentiment.py`:

```python
class CardinalityMismatchClassifier:
    """Returns a scripted batch length to simulate malformed structured output."""

    def __init__(self, verdicts: list[HeadlineVerdict]) -> None:
        self._verdicts = verdicts
        self.calls: list[list[str]] = []

    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]:
        self.calls.append(list(headlines))
        return list(self._verdicts)
```

- [ ] **Step 2: Add the too-few RED test**

Add this test after `test_cap_logs_and_marks_partial`:

```python
def test_classifier_too_few_verdicts_returns_none(tmp_path: Path, caplog):
    recs = [
        _rec(None, 31, _news("AAPL item 1", "")),
        _rec(None, 31, _news("AAPL item 2", "")),
    ]
    classifier = CardinalityMismatchClassifier(
        [_verdict(SignalDirection.BULLISH, 0.8)]
    )
    sig = LlmSentimentSignal(classifier=classifier, max_headlines=50)

    with caplog.at_level(logging.WARNING):
        r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is None
    assert classifier.calls == [["AAPL item 1", "AAPL item 2"]]
    assert any(
        "returned 1 verdicts for 2 headlines" in message
        for message in caplog.messages
    )
```

- [ ] **Step 3: Add the too-many RED test**

Add this test next to the too-few test:

```python
def test_classifier_too_many_verdicts_returns_none(tmp_path: Path, caplog):
    recs = [_rec(None, 31, _news("AAPL item 1", ""))]
    classifier = CardinalityMismatchClassifier(
        [
            _verdict(SignalDirection.BULLISH, 0.8),
            _verdict(SignalDirection.BEARISH, 0.4),
        ]
    )
    sig = LlmSentimentSignal(classifier=classifier, max_headlines=50)

    with caplog.at_level(logging.WARNING):
        r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is None
    assert classifier.calls == [["AAPL item 1"]]
    assert any(
        "returned 2 verdicts for 1 headlines" in message
        for message in caplog.messages
    )
```

- [ ] **Step 4: Run RED**

Run:

```bash
uv run pytest \
  tests/analysis/signals/test_llm_sentiment.py::test_classifier_too_few_verdicts_returns_none \
  tests/analysis/signals/test_llm_sentiment.py::test_classifier_too_many_verdicts_returns_none \
  -q
```

Expected: FAIL because `evaluate()` currently aggregates mismatched verdict lists instead of returning `None`.

- [ ] **Step 5: Implement the cardinality guard**

In `mimir/analysis/signals/llm_sentiment.py`, add this block inside the existing `try`, immediately after `verdicts = self._classifier.classify(texts)` and before `_aggregate()` is called:

```python
        if len(verdicts) != len(texts):
            logger.warning(
                "signal 'llm_sentiment' classifier returned %d verdicts for %d headlines for %s; skipping",
                len(verdicts),
                len(texts),
                symbol,
            )
            return None
```

- [ ] **Step 6: Run GREEN**

Run:

```bash
uv run pytest tests/analysis/signals/test_llm_sentiment.py -q
```

Expected: PASS.

- [ ] **Step 7: Update docs**

In `docs/reference/analysis/scoring.md`, add one bullet under `llm_sentiment`:

```markdown
- classifier가 입력 headline 수와 다른 개수의 verdict를 반환하면 warning 후 해당 symbol의 `llm_sentiment` 결과를 생략한다. 잘못된 batch를 부분 평균내지 않는다.
```

In `docs/architecture/improvement-catalog.md`, add an AN2 entry after AN1 and add `AN2-LLM-CLASSIFIER-CARDINALITY` to the roadmap map.

In `docs/decisions/tech-spec/README.md`, add AN2 under `analysis`.

- [ ] **Step 8: Run verification gates**

Run:

```bash
uv run pytest tests/analysis/signals/test_llm_sentiment.py -q
uv run pytest tests/analysis -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: all pass.

- [ ] **Step 9: Commit and update progress**

Append to `.git/sdd/progress.md`:

```text
AN2-LLM-CLASSIFIER-CARDINALITY: complete (commit <hash>, RED/GREEN cardinality tests, analysis gates/ruff/mypy/diff check)
```

Commit only intended files. Do not stage `uv.lock`.

```bash
git add \
  mimir/analysis/signals/llm_sentiment.py \
  tests/analysis/signals/test_llm_sentiment.py \
  docs/reference/analysis/scoring.md \
  docs/architecture/improvement-catalog.md \
  docs/decisions/tech-spec/README.md \
  docs/decisions/tech-spec/analysis/AN2_LLM_classifier_cardinality_tech_spec_2026_06_23.md \
  docs/superpowers/plans/2026-06-23-llm-classifier-cardinality.md
git commit -m "fix(analysis): guard llm sentiment classifier cardinality"
```

## Self-Review

- Spec coverage: AN2 goals map to Task 1 steps 1-9.
- Placeholder scan: no unresolved placeholder markers or generic test-writing instructions.
- Type consistency: tests and implementation use `HeadlineClassifier`, `HeadlineVerdict`, and `SignalResult | None` exactly as implemented.
