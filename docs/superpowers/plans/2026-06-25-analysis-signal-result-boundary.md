# Analysis Signal Result Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `AnalysisEngine` skip invalid non-`SignalResult` signal returns before scoring so a malformed plugin result cannot crash the whole analysis run.

**Architecture:** Keep AN4 exception isolation and add one runtime type boundary between `Signal.evaluate()` and `score()`. `None` still means no signal, `SignalResult` still enters scoring, and any other return type logs an error and is skipped for that signal/symbol. No scoring, storage, plugin discovery, config, retry, network, or LLM gate behavior changes.

**Tech Stack:** Python 3.14, pytest, pydantic `SignalResult`, existing `AnalysisEngine`, `JsonlStore.replace_partition`, `mimir.analysis.engine` logging.

## Global Constraints

- Do not touch, stage, remove, or rewrite the pre-existing untracked `uv.lock`.
- Runtime write scope is `mimir/analysis/engine.py`.
- Test write scope is `tests/analysis/test_engine.py`.
- Documentation write scope is `docs/decisions/tech-spec/analysis/AN6_analysis_signal_result_boundary_tech_spec_2026_06_25.md`, `docs/decisions/tech-spec/README.md`, `docs/reference/analysis/scoring.md`, `docs/architecture/improvement-catalog.md`, `tests/test_readme_docs.py`, `README.md`, `README.ko.md`, and `README.zh.md`.
- `Signal.evaluate()` returning `None` must keep existing "no signal" behavior.
- `Signal.evaluate()` returning `SignalResult` must keep existing scoring and persistence behavior.
- `Signal.evaluate()` returning any other non-`None` value must be logged and skipped before `score()` runs.
- The invalid-result log must include signal id, watchlist market key/symbol, and returned type name. It must not log the returned object repr.
- Preserve AN4 exception isolation: `Exception` from `evaluate()` is still logged with traceback and skipped; process-control exceptions are not caught.
- Preserve signal order, scorer formula, `Insight` payload shape, plugin discovery, plugin opt-in config, source collection, LLM enablement, retry policy, network behavior, and JSONL storage layout.
- Do not coerce dicts, objects, or strings into `SignalResult`.
- Do not add sandboxing, manifest datasets, or new dependencies.

---

### Task 1: Guard Invalid Signal Result Types

**Files:**
- Modify: `tests/analysis/test_engine.py`
- Modify: `mimir/analysis/engine.py`
- Modify: `docs/decisions/tech-spec/analysis/AN6_analysis_signal_result_boundary_tech_spec_2026_06_25.md`
- Modify: `docs/decisions/tech-spec/README.md`
- Modify: `docs/reference/analysis/scoring.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `tests/test_readme_docs.py`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

**Interfaces:**
- Consumes: `Signal.evaluate(symbol, market, as_of, reader) -> SignalResult | None`
- Produces: `AnalysisEngine.run(...)` skips non-`SignalResult` returns and still returns/stores only valid `Insight` objects.

- [ ] **Step 1: Add a malformed signal test helper**

Add this helper near `_AlwaysFailSignal` in `tests/analysis/test_engine.py`:

```python
class _MalformedResultSignal:
    id = "malformed_signal"

    def __init__(self, result):
        self._result = result

    def evaluate(self, symbol, market, as_of, reader):
        return self._result
```

- [ ] **Step 2: Write failing same-symbol continuation test**

Add this test in `tests/analysis/test_engine.py` after `test_engine_skips_failed_signal_and_scores_remaining_signal`:

```python
def test_engine_skips_malformed_signal_result_and_scores_remaining_signal(
    tmp_path: Path, caplog
):
    store = JsonlStore(root=tmp_path)
    engine = AnalysisEngine(
        [_MalformedResultSignal({"signal": "not-a-model"}), _BullishTestSignal()],
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
    assert "malformed_signal" in messages
    assert "dict" in messages
    assert "us/AAPL" in messages
    assert "not-a-model" not in messages
```

- [ ] **Step 3: Verify RED for same-symbol continuation**

Run:

```bash
uv run pytest tests/analysis/test_engine.py::test_engine_skips_malformed_signal_result_and_scores_remaining_signal -q
```

Expected: FAIL because the raw `dict` reaches `score()` and raises `AttributeError` for a missing `weight` attribute.

- [ ] **Step 4: Write failing stale-clearing test**

Add this test after `test_engine_clears_stale_insights_when_rerun_has_no_signals`:

```python
def test_engine_clears_stale_insights_when_only_malformed_results(tmp_path: Path, caplog):
    store = JsonlStore(root=tmp_path)
    stale = Insight(
        symbol="AAPL",
        market=Market.US,
        as_of=AS_OF,
        direction=SignalDirection.BULLISH,
        stars=4,
        confidence=0.8,
        signals=[],
        reasons=["stale"],
    )
    store.append([to_record(stale, datetime(2026, 5, 31, tzinfo=UTC))])
    engine = AnalysisEngine(
        [_MalformedResultSignal(object())],
        DataReader(store),
        store,
    )

    with caplog.at_level(logging.ERROR, logger="mimir.analysis.engine"):
        insights = engine.run({"us": ["AAPL"], "kr": []}, AS_OF)

    assert insights == []
    assert list(store.read_all(Dataset.INSIGHTS)) == []
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "malformed_signal" in messages
    assert "object" in messages
    assert "us/AAPL" in messages
```

- [ ] **Step 5: Verify RED for stale clearing**

Run:

```bash
uv run pytest tests/analysis/test_engine.py::test_engine_clears_stale_insights_when_only_malformed_results -q
```

Expected: FAIL because the raw `object()` reaches `score()` and raises `AttributeError` for a missing `weight` attribute before `replace_partition()` can clear stale records.

- [ ] **Step 6: Implement minimal engine guard**

Modify the import in `mimir/analysis/engine.py`:

```python
from mimir.analysis.signals.base import Signal, SignalResult
```

Replace the post-evaluate append block:

```python
                    if result is not None:
                        results.append(result)
```

with:

```python
                    if result is None:
                        continue
                    if not isinstance(result, SignalResult):
                        logger.error(
                            "analysis signal '%s' returned invalid result type %s for %s/%s; skipping",
                            _signal_id(sig),
                            type(result).__name__,
                            key,
                            symbol,
                        )
                        continue
                    results.append(result)
```

- [ ] **Step 7: Verify GREEN for engine tests**

Run:

```bash
uv run pytest tests/analysis/test_engine.py -q
```

Expected: all engine tests pass.

- [ ] **Step 8: Update tech spec status and docs**

Update `docs/decisions/tech-spec/analysis/AN6_analysis_signal_result_boundary_tech_spec_2026_06_25.md` status from `Draft` to `Implemented`.

Update `docs/decisions/tech-spec/README.md` analysis table with:

```markdown
| [AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY](analysis/AN6_analysis_signal_result_boundary_tech_spec_2026_06_25.md) | `Signal.evaluate()`가 잘못된 반환 타입을 내도 scoring 전에 log+skip |
```

Update `docs/reference/analysis/scoring.md` section 1 to state:

```markdown
Signal 평가가 `None`도 `SignalResult`도 아닌 값을 반환하면 `AnalysisEngine`은 signal id, market/symbol, 반환 타입을 error log에 남기고 해당 signal 결과만 생략한다. 반환값을 coercion하지 않으며, 같은 symbol의 다른 signal과 다음 symbol 평가는 계속된다.
```

Update `docs/architecture/improvement-catalog.md`:

- Add `AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY` to the status line.
- Add an implemented row after AN5 in the summary table.
- Add a subsection after AN5 explaining the invalid result boundary.
- Add AN6 to the sequencing list and conclusion.

Update `tests/test_readme_docs.py`:

```python
LATEST_COMPLETED_IDS = (
    "AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY",
    "AN5-ANALYSIS-SIGNAL-SPECS-INJECTION",
    ...
)
```

```python
    "AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY": Path(
        "docs/decisions/tech-spec/analysis/"
        "AN6_analysis_signal_result_boundary_tech_spec_2026_06_25.md"
    ),
```

After the full suite count is known, update README test counts in `README.md`, `README.ko.md`, and `README.zh.md`. If only the two AN6 tests were added, the expected count is `628`, but use the actual full-suite result.

- [ ] **Step 9: Run targeted verification**

Run:

```bash
uv run pytest tests/analysis/test_engine.py tests/test_readme_docs.py -q
```

Expected: all selected tests pass.

- [ ] **Step 10: Run full gates**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: full suite passes, ruff passes, mypy passes, diff check passes.
