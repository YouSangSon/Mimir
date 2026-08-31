# Analysis Engine Signal Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `AnalysisEngine` isolate one signal evaluation failure so the rest of the analysis run can continue.

**Architecture:** Add a narrow `try/except Exception` boundary around `Signal.evaluate()` inside `AnalysisEngine.run()`. Failed signals are logged with signal id, market, and symbol, then skipped exactly like a `None` result. Scoring, persisted insight schema, plugin discovery, and LLM enablement stay unchanged.

**Tech Stack:** Python 3.14, pytest, pydantic `SignalResult`, `JsonlStore`, existing analysis signal protocol.

## Global Constraints

- Do not touch, stage, remove, or rewrite the pre-existing untracked `uv.lock`.
- Runtime write scope is `mimir/analysis/engine.py` and `tests/analysis/test_engine.py`.
- Documentation write scope is `docs/decisions/tech-spec/analysis/AN4_analysis_engine_signal_isolation_tech_spec_2026_06_25.md`, `docs/decisions/tech-spec/README.md`, `docs/reference/analysis/scoring.md`, `docs/architecture/improvement-catalog.md`, `README.md`, `README.ko.md`, `README.zh.md`, and `tests/test_readme_docs.py`.
- Catch `Exception` only. Do not catch `BaseException`, `KeyboardInterrupt`, or `SystemExit`.
- A failed signal must not create a placeholder `SignalResult`.
- If another signal returns a valid result for the same symbol, the symbol still gets an insight.
- If no signal result remains for a symbol, existing skip behavior remains.
- `replace_partition(Dataset.INSIGHTS, as_of, records)` must still run once per `run()` call.
- Do not change `Signal`, `SignalResult`, `Insight`, scorer math, JSONL layout, source collection, plugin discovery, LLM enablement, retry policy, or network behavior.

---

### Task 1: Engine Signal Evaluation Isolation

**Files:**
- Modify: `tests/analysis/test_engine.py`
- Modify: `mimir/analysis/engine.py`
- Modify: `docs/decisions/tech-spec/analysis/AN4_analysis_engine_signal_isolation_tech_spec_2026_06_25.md`
- Modify: `docs/decisions/tech-spec/README.md`
- Modify: `docs/reference/analysis/scoring.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `tests/test_readme_docs.py`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

**Interfaces:**
- Consumes: `Signal.evaluate(symbol, market, as_of, reader) -> SignalResult | None`
- Produces: `AnalysisEngine.run(...)` continues after `Exception` from one signal evaluation and logs with logger name `mimir.analysis.engine`.

- [ ] **Step 1: Add test helpers**

Add these imports and helpers to `tests/analysis/test_engine.py`:

```python
import logging

from mimir.analysis.signals.base import SignalResult
```

```python
class _BullishTestSignal:
    id = "bullish_test"

    def evaluate(self, symbol, market, as_of, reader):
        return SignalResult(
            signal=self.id,
            direction=SignalDirection.BULLISH,
            strength=0.75,
            confidence=0.8,
            reason=f"{symbol} passed",
        )


class _AlwaysFailSignal:
    id = "broken_signal"

    def evaluate(self, symbol, market, as_of, reader):
        raise RuntimeError(f"{symbol} boom")


class _FailOnlyAaplSignal:
    id = "fail_only_aapl"

    def evaluate(self, symbol, market, as_of, reader):
        if symbol == "AAPL":
            raise RuntimeError("AAPL boom")
        return SignalResult(
            signal=self.id,
            direction=SignalDirection.BULLISH,
            strength=0.6,
            confidence=0.7,
            reason=f"{symbol} survived",
        )
```

- [ ] **Step 2: Write failing same-symbol isolation test**

Add this test to `tests/analysis/test_engine.py`:

```python
def test_engine_skips_failed_signal_and_scores_remaining_signal(tmp_path: Path, caplog):
    store = JsonlStore(root=tmp_path)
    engine = AnalysisEngine(
        [_AlwaysFailSignal(), _BullishTestSignal()],
        DataReader(store),
        store,
    )

    with caplog.at_level(logging.ERROR, logger="mimir.analysis.engine"):
        insights = engine.run({"us": ["AAPL"], "kr": []}, AS_OF)

    assert len(insights) == 1
    assert insights[0].symbol == "AAPL"
    assert [result.signal for result in insights[0].signals] == ["bullish_test"]
    assert list(store.read_all(Dataset.INSIGHTS))[0].symbol == "AAPL"
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "broken_signal" in messages
    assert "us/AAPL" in messages
```

- [ ] **Step 3: Verify RED for same-symbol isolation**

Run:

```bash
uv run pytest tests/analysis/test_engine.py::test_engine_skips_failed_signal_and_scores_remaining_signal -q
```

Expected: FAIL with `RuntimeError: AAPL boom`.

- [ ] **Step 4: Write failing next-symbol continuation test**

Add this test to `tests/analysis/test_engine.py`:

```python
def test_engine_continues_to_next_symbol_after_signal_failure(tmp_path: Path, caplog):
    store = JsonlStore(root=tmp_path)
    engine = AnalysisEngine([_FailOnlyAaplSignal()], DataReader(store), store)

    with caplog.at_level(logging.ERROR, logger="mimir.analysis.engine"):
        insights = engine.run({"us": ["AAPL", "MSFT"], "kr": []}, AS_OF)

    assert [insight.symbol for insight in insights] == ["MSFT"]
    assert [record.symbol for record in store.read_all(Dataset.INSIGHTS)] == ["MSFT"]
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "fail_only_aapl" in messages
    assert "us/AAPL" in messages
```

- [ ] **Step 5: Verify RED for next-symbol continuation**

Run:

```bash
uv run pytest tests/analysis/test_engine.py::test_engine_continues_to_next_symbol_after_signal_failure -q
```

Expected: FAIL with `RuntimeError: AAPL boom`.

- [ ] **Step 6: Implement minimal engine isolation**

Modify `mimir/analysis/engine.py`:

```python
import logging
```

```python
logger = logging.getLogger(__name__)
```

```python
def _signal_id(signal: Signal) -> str:
    return getattr(signal, "id", signal.__class__.__name__)
```

Change the signal loop to:

```python
for sig in self._signals:
    try:
        result = sig.evaluate(symbol, market, as_of, self._reader)
    except Exception:
        logger.exception(
            "analysis signal '%s' failed for %s/%s; skipping",
            _signal_id(sig),
            market.value,
            symbol,
        )
        continue
    if result is not None:
        results.append(result)
```

- [ ] **Step 7: Verify GREEN for engine tests**

Run:

```bash
uv run pytest tests/analysis/test_engine.py -q
```

Expected: all engine tests pass.

- [ ] **Step 8: Update docs and docs guards**

Update `docs/decisions/tech-spec/analysis/AN4_analysis_engine_signal_isolation_tech_spec_2026_06_25.md` status from `Draft` to `Implemented`.

Update `docs/decisions/tech-spec/README.md` analysis table with:

```markdown
| [AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION](analysis/AN4_analysis_engine_signal_isolation_tech_spec_2026_06_25.md) | Signal 평가 예외를 해당 signal/symbol에서만 skip하고 analysis run을 계속 진행 |
```

Update `tests/test_readme_docs.py`:

```python
LATEST_COMPLETED_IDS = (
    "AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION",
    "AN3-ANALYSIS-PLUGIN-BUILTIN-GUARD",
    ...
)
```

```python
    "AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION": Path(
        "docs/decisions/tech-spec/analysis/"
        "AN4_analysis_engine_signal_isolation_tech_spec_2026_06_25.md"
    ),
```

Update `docs/reference/analysis/scoring.md` final update date to `2026-06-25` and add a short operational note near the signal overview:

```markdown
Signal 평가 중 `Exception`이 발생하면 `AnalysisEngine`은 signal id, market/symbol과 traceback을 log에 남기고 해당 signal 결과만 생략한다. 같은 symbol의 다른 signal과 다음 symbol 평가는 계속된다. 모든 signal이 실패하거나 `None`이면 기존처럼 그 symbol의 insight는 생성하지 않는다.
```

Update `docs/architecture/improvement-catalog.md`:

- Add `AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION` to the status line.
- Add a row after AN3 in the summary table.
- Add a subsection after AN3 explaining the failure-isolation behavior.
- Add AN4 to the sequencing list and conclusion.

Update README test counts from `618` to the new collected count after adding two engine tests. Expected new count: `620`. Update all three README files' badge and test table rows.

- [ ] **Step 9: Run targeted verification**

Run:

```bash
uv run pytest tests/analysis/test_engine.py tests/test_readme_docs.py -q
uv run ruff check mimir/analysis/engine.py tests/analysis/test_engine.py tests/test_readme_docs.py
git diff --check
```

Expected: tests pass, ruff passes, diff check has no output.

- [ ] **Step 10: Run full verification**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: full pytest count matches README badges, ruff passes, mypy passes, diff check has no output.

- [ ] **Step 11: Commit**

Stage only intentional files:

```bash
git add \
  mimir/analysis/engine.py \
  tests/analysis/test_engine.py \
  docs/decisions/tech-spec/analysis/AN4_analysis_engine_signal_isolation_tech_spec_2026_06_25.md \
  docs/decisions/tech-spec/README.md \
  docs/reference/analysis/scoring.md \
  docs/architecture/improvement-catalog.md \
  tests/test_readme_docs.py \
  README.md README.ko.md README.zh.md
git commit -m "fix(analysis): isolate signal evaluation failures"
```
