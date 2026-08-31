# Normalize Payload Type Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining payload-boundary `type: ignore` comments where a small behavior-preserving typing fix exists.

**Architecture:** Keep `parse_payload()` as the single payload-dispatch API. Parse `RawRecord.payload` before constructing `Record`, and use `typing.cast()` only where mypy cannot express the validated `Payload` union returned by pydantic.

**Tech Stack:** Python 3.14, pydantic, pytest, mypy.

---

## Global Constraints

- Do not touch, stage, remove, or commit the unrelated untracked `uv.lock`.
- Do not stage or commit `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` scratch files.
- Keep this loop to one objective: payload-boundary type-ignore cleanup.
- Do not add dependencies or new abstractions.

### Task 1: Normalize Payload Boundary Typing

**Files:**
- Modify: `tests/core/test_normalize.py`
- Modify: `mimir/core/normalize.py`
- Modify: `mimir/core/payloads.py`
- Modify: `PLAN.md`
- Modify: `BACKLOG.md`
- Modify: `WORKLOG.md`
- Modify: `DECISIONS.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

**Interfaces:**
- Consumes: `parse_payload(dataset, data)`.
- Produces: no public API or storage layout change.

- [ ] **Step 1: Write the failing type-ignore guard**

Update `tests/core/test_normalize.py` imports:

```python
from pathlib import Path
from typing import cast

from mimir.core.payloads import PricePayload
```

Add this test:

```python
def test_payload_boundary_does_not_need_type_ignore_comments():
    for path in (
        Path("mimir/core/normalize.py"),
        Path("mimir/core/payloads.py"),
        Path("tests/core/test_normalize.py"),
    ):
        assert "type: " "ignore" not in path.read_text(encoding="utf-8")
```

Extend `test_normalize_builds_record_from_meta()`:

```python
assert isinstance(rec.payload, PricePayload)
```

Change the bad object call to use `cast(RawRecord, Bad())` instead of a `type: ignore` comment.

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
uv run pytest tests/core/test_normalize.py::test_payload_boundary_does_not_need_type_ignore_comments -q
```

Expected: FAIL because `normalize.py`, `payloads.py`, and `test_normalize.py` still contain `type: ignore` comments.

- [ ] **Step 3: Remove the ignores**

In `mimir/core/normalize.py`, import `parse_payload` and pass a typed payload into `Record`:

```python
from mimir.core.payloads import parse_payload
...
payload=parse_payload(meta.dataset, raw.payload),
```

In `mimir/core/payloads.py`, import `cast` and return:

```python
return cast(Payload, model.model_validate(data))
```

In `tests/core/test_normalize.py`, use:

```python
bad = cast(RawRecord, Bad())
normalize(bad, META, captured_at=CAPTURED)
```

- [ ] **Step 4: Verify**

Run:

```bash
uv run pytest tests/core/test_normalize.py::test_payload_boundary_does_not_need_type_ignore_comments -q
uv run pytest tests/core/test_normalize.py -q
uv run pytest tests/core/test_payloads.py -q
uv run pytest --collect-only -q | tail -1
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add tests/core/test_normalize.py mimir/core/normalize.py mimir/core/payloads.py PLAN.md BACKLOG.md WORKLOG.md DECISIONS.md README.md README.ko.md README.zh.md docs/superpowers/plans/2026-06-28-normalize-payload-type-cleanup.md
git commit -m "test(core): cover normalize payload typing"
```
