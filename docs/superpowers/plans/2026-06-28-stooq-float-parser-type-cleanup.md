# Stooq Float Parser Type Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the local `type: ignore[arg-type]` from the Stooq numeric parser while preserving `N/D` handling for optional numeric CSV fields.

**Architecture:** Reuse the existing Stooq source parser and tests. Add one parser regression test for optional `N/D` numeric fields, then narrow the value before `float()` with the smallest code change.

**Tech Stack:** Python 3.14, pytest, mypy.

---

## Global Constraints

- Do not touch, stage, remove, or commit the unrelated untracked `uv.lock`.
- Do not stage or commit `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` scratch files.
- Keep this loop to one objective: Stooq parser type cleanup.
- Do not add dependencies.

### Task 1: Stooq Optional Numeric Parser Coverage

**Files:**
- Modify: `tests/sources/test_stooq.py`
- Modify: `mimir/sources/stooq.py`
- Modify: `PLAN.md`
- Modify: `BACKLOG.md`
- Modify: `WORKLOG.md`
- Modify: `DECISIONS.md`

**Interfaces:**
- Consumes: `StooqSource.fetch()`.
- Produces: no public API change.

- [ ] **Step 1: Write the failing parser coverage**

Add `Path` import:

```python
from pathlib import Path
```

Add these tests to `tests/sources/test_stooq.py`:

```python
def test_stooq_parser_does_not_need_arg_type_ignore():
    assert "type: ignore[arg-type]" not in Path("mimir/sources/stooq.py").read_text(
        encoding="utf-8"
    )


@responses.activate
def test_stooq_optional_numeric_nd_values_parse_as_none():
    responses.add(
        responses.GET,
        "https://stooq.com/q/d/l/",
        body="Date,Open,High,Low,Close,Volume\n2026-05-28,N/D,,0.5,1.5,N/D\n",
        status=200,
    )
    src = StooqSource(session=requests.Session())

    rec = next(iter(src.fetch(_ctx(["AAPL"]))))

    assert rec.payload["open"] is None
    assert rec.payload["high"] is None
    assert rec.payload["low"] == 0.5
    assert rec.payload["close"] == 1.5
    assert rec.payload["volume"] is None
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
uv run pytest tests/sources/test_stooq.py::test_stooq_optional_numeric_nd_values_parse_as_none -q
```

Expected: `test_stooq_parser_does_not_need_arg_type_ignore` fails because `_f()` still has `# type: ignore[arg-type]`. The `N/D` behavior test may already pass; it is characterization coverage for the parser contract.

- [ ] **Step 3: Remove the type ignore**

Change `_f()` in `mimir/sources/stooq.py` to:

```python
def _f(value: str | None) -> float | None:
    if value is None or value in ("", "N/D"):
        return None
    return float(value)
```

- [ ] **Step 4: Verify**

Run:

```bash
uv run pytest tests/sources/test_stooq.py::test_stooq_optional_numeric_nd_values_parse_as_none -q
uv run pytest tests/sources/test_stooq.py::test_stooq_parser_does_not_need_arg_type_ignore -q
uv run pytest tests/sources/test_stooq.py -q
uv run pytest --collect-only -q | tail -1
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add tests/sources/test_stooq.py mimir/sources/stooq.py PLAN.md BACKLOG.md WORKLOG.md DECISIONS.md README.md README.ko.md README.zh.md docs/superpowers/plans/2026-06-28-stooq-float-parser-type-cleanup.md
git commit -m "test(sources): cover stooq optional numerics"
```
