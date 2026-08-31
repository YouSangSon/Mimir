# Entrypoint Cast Type Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove avoidable `typing.cast()` calls from source and analysis entry-point loaders while keeping plugin discovery behavior unchanged.

**Architecture:** Mimir requires Python `>=3.14`, and Python 3.14 `importlib.metadata.entry_points(group=...)` returns selectable `EntryPoints` directly. The old dictionary/`select()` fallback is compatibility code for unsupported Python versions, so the lazy fix is to delete it in both builder modules and keep the existing loader tests as behavior coverage.

**Tech Stack:** Python 3.14, `importlib.metadata`, pytest, ruff, mypy strict.

---

### Task 1: Guard Builder Entry-Point Loader Cast Removal

**Files:**
- Modify: `tests/core/test_builder.py`
- Modify: `tests/analysis/test_builder.py`

- [ ] **Step 1: Add the failing source-loader guard**

Add to `tests/core/test_builder.py`:

```python
from pathlib import Path
```

Add this test near the existing entry-point loader tests:

```python
def test_source_entry_point_loader_does_not_keep_legacy_cast() -> None:
    text = Path("mimir/core/builder.py").read_text(encoding="utf-8")
    loader = text.split("def _entry_points_for_group", 1)[1].split(
        "def _source_specs_from_entry_point", 1
    )[0]

    assert "cast(" not in loader
```

Add to `tests/analysis/test_builder.py`:

```python
def test_signal_entry_point_loader_does_not_keep_legacy_cast() -> None:
    text = Path("mimir/analysis/builder.py").read_text(encoding="utf-8")
    loader = text.split("def _entry_points_for_group", 1)[1].split(
        "def _signal_specs_from_entry_point", 1
    )[0]

    assert "cast(" not in loader
```

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/core/test_builder.py::test_source_entry_point_loader_does_not_keep_legacy_cast tests/analysis/test_builder.py::test_signal_entry_point_loader_does_not_keep_legacy_cast -q
```

Expected: both tests fail because the loaders still contain `cast(...)`.

### Task 2: Delete Unsupported Legacy Fallback

**Files:**
- Modify: `mimir/core/builder.py`
- Modify: `mimir/analysis/builder.py`

- [ ] **Step 1: Simplify source loader**

In `mimir/core/builder.py`, remove unused `Iterable`, `Mapping`, and `cast`
imports, then replace `_entry_points_for_group()` with:

```python
def _entry_points_for_group(group: str) -> tuple[importlib.metadata.EntryPoint, ...]:
    entry_points = importlib.metadata.entry_points(group=group)
    return tuple(sorted(entry_points, key=lambda entry_point: entry_point.name))
```

- [ ] **Step 2: Simplify analysis loader**

In `mimir/analysis/builder.py`, remove unused `Iterable`, `Mapping`, and `cast`
imports, then replace `_entry_points_for_group()` with:

```python
def _entry_points_for_group(group: str) -> tuple[importlib.metadata.EntryPoint, ...]:
    entry_points = importlib.metadata.entry_points(group=group)
    return tuple(sorted(entry_points, key=lambda entry_point: entry_point.name))
```

- [ ] **Step 3: Verify GREEN**

Run:

```bash
uv run pytest tests/core/test_builder.py::test_source_entry_point_loader_does_not_keep_legacy_cast tests/analysis/test_builder.py::test_signal_entry_point_loader_does_not_keep_legacy_cast -q
```

Expected: 2 passed.

- [ ] **Step 4: Run focused suites**

Run:

```bash
uv run pytest tests/core/test_builder.py tests/analysis/test_builder.py -q
uv run mypy mimir/core/builder.py mimir/analysis/builder.py
```

Expected: both commands pass.

### Task 3: Record Loop State And Verify

**Files:**
- Modify: `PLAN.md`
- Modify: `BACKLOG.md`
- Modify: `WORKLOG.md`
- Modify: `DECISIONS.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Update project state docs**

Set `PLAN.md` current loop to `ENTRYPOINT-CAST-TYPE-CLEANUP`.

Move the queue item to Done in `BACKLOG.md` with:

```markdown
- `ENTRYPOINT-CAST-TYPE-CLEANUP` — source and analysis plugin entry-point
  loaders now use the Python 3.14 `entry_points(group=...)` API directly
  instead of legacy mapping fallback casts.
```

Add `WORKLOG.md` and `DECISIONS.md` entries that record the Python 3.14
`entry_points(group=...)` rationale and verification.

Update README EN/KO/ZH test counts after collect-only reports the new total.

- [ ] **Step 2: Run controller gates**

Run:

```bash
uv run pytest tests/core/test_builder.py tests/analysis/test_builder.py -q
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q | tail -1
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
git status --short --branch
```

Expected: all pass, with only intended files modified plus existing untracked
local handoff files and `uv.lock`.

- [ ] **Step 3: Commit implementation**

Stage only the plan, code, tests, and tracked docs:

```bash
git add docs/superpowers/plans/2026-06-28-entrypoint-cast-type-cleanup.md PLAN.md BACKLOG.md WORKLOG.md DECISIONS.md README.md README.ko.md README.zh.md tests/core/test_builder.py tests/analysis/test_builder.py mimir/core/builder.py mimir/analysis/builder.py
git commit -m "test(core): remove entrypoint cast fallbacks"
```

Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.
