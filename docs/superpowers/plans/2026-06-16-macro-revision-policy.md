# Macro Revision Storage Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FRED/ECOS 같은 macro source의 공식 개정값은 최신 값으로 저장하고, prices/filings/news는 기존 first-write-wins 의미를 유지한다.

**Architecture:** source dataset별 append policy를 `mimir/storage/policy.py`에 모은다. orchestrator와 backfill은 같은 helper를 사용해 `Dataset.MACRO`만 `JsonlStore.append(..., overwrite=True)`로 저장한다.

**Tech Stack:** Python 3.14, pydantic records, pytest, responses, ruff, mypy.

---

### Task 1: Storage Policy And Overwrite Count

**Files:**
- Create: `mimir/storage/policy.py`
- Create: `tests/storage/test_policy.py`
- Modify: `mimir/storage/jsonl_store.py`
- Modify: `tests/storage/test_jsonl_store.py`

- [x] **Step 1: Write failing policy helper test**

Add `tests/storage/test_policy.py`:

```python
from mimir.core.source import Dataset
from mimir.storage.policy import append_overwrite_enabled


def test_append_overwrite_enabled_only_for_macro_sources():
    assert append_overwrite_enabled(Dataset.MACRO) is True
    assert append_overwrite_enabled(Dataset.PRICES) is False
    assert append_overwrite_enabled(Dataset.FILINGS) is False
    assert append_overwrite_enabled(Dataset.NEWS) is False
```

Run:

```bash
uv run pytest tests/storage/test_policy.py -q
```

Expected: FAIL because `mimir.storage.policy` does not exist.

- [x] **Step 2: Write failing overwrite count test**

Add to `tests/storage/test_jsonl_store.py`:

```python
def test_append_overwrite_counts_replaced_records(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k1", 29, close=1.0)])

    changed = store.append([_rec("k1", 29, close=99.0)], overwrite=True)

    assert changed == 1
```

Run:

```bash
uv run pytest tests/storage/test_jsonl_store.py::test_append_overwrite_counts_replaced_records -q
```

Expected: FAIL because `_append_overwrite()` currently returns only new key count.

- [x] **Step 2b: Write repeated-key overwrite count test**

Add to `tests/storage/test_jsonl_store.py`:

```python
def test_append_overwrite_counts_repeated_batch_key_once(tmp_path: Path):
    ...
```

Run:

```bash
uv run pytest tests/storage/test_jsonl_store.py::test_append_overwrite_counts_repeated_batch_key_once -q
```

Expected: FAIL because `_append_overwrite()` counts each repeated incoming change, even though only one final record is stored.

- [x] **Step 2c: Write no-op overwrite write-avoidance test**

Add to `tests/storage/test_jsonl_store.py`:

```python
def test_append_overwrite_noop_does_not_rewrite_partition(tmp_path: Path, monkeypatch):
    ...
```

Run:

```bash
uv run pytest tests/storage/test_jsonl_store.py::test_append_overwrite_noop_does_not_rewrite_partition -q
```

Expected: FAIL because `_append_overwrite()` still opens the partition in write mode when the final incoming records do not change stored content.

- [x] **Step 3: Implement minimal policy helper and overwrite count**

Create `mimir/storage/policy.py`:

```python
from __future__ import annotations

from mimir.core.source import Dataset

OVERWRITE_ON_APPEND_DATASETS = frozenset({Dataset.MACRO})


def append_overwrite_enabled(dataset: Dataset) -> bool:
    return dataset in OVERWRITE_ON_APPEND_DATASETS
```

Update `_append_overwrite()` so it first keeps the last incoming record per key, increments the returned count when the final incoming key is new or differs from the stored record, and returns before opening the partition for write when no final key changed.

- [x] **Step 4: Run storage tests**

```bash
uv run pytest tests/storage/test_policy.py tests/storage/test_jsonl_store.py -q
```

Expected: PASS.

### Task 2: Orchestrator Source Policy

**Files:**
- Modify: `mimir/core/orchestrator.py`
- Modify: `tests/core/test_orchestrator.py`

- [x] **Step 1: Write failing macro overwrite test**

Add a fake macro source that emits the same FRED-style key with different values across two orchestrator runs. Assert that one macro record remains and the latest value wins.

Run:

```bash
uv run pytest tests/core/test_orchestrator.py::test_macro_sources_overwrite_existing_observations -q
```

Expected: FAIL because orchestrator still calls `append(records)` without overwrite.

- [x] **Step 2: Write non-macro invariant test**

Add a fake price source that emits the same key with a changed close across two orchestrator runs. Assert that the first close remains and the second run stores zero records.

Run:

```bash
uv run pytest tests/core/test_orchestrator.py::test_non_macro_sources_keep_first_write_wins -q
```

Expected: PASS before and after the implementation. This protects against accidentally enabling overwrite for all datasets.

- [x] **Step 3: Wire orchestrator to storage policy**

Import `append_overwrite_enabled` and call:

```python
stored = self._store.append(
    records,
    overwrite=append_overwrite_enabled(source.meta.dataset),
)
```

- [x] **Step 4: Run orchestrator tests**

```bash
uv run pytest tests/core/test_orchestrator.py -q
```

Expected: PASS.

### Task 3: Backfill Source Policy

**Files:**
- Modify: `mimir/backfill.py`
- Modify: `tests/test_backfill.py`

- [x] **Step 1: Write failing FRED backfill revision test**

Run FRED backfill twice with the same `fred:DGS10:2024-01-02` key and different payload values. Assert that the partition contains one record with the second value.

Run:

```bash
uv run pytest tests/test_backfill.py::test_backfill_fred_revisions_overwrite_existing_observation -q
```

Expected: FAIL because backfill still uses first-write-wins.

- [x] **Step 2: Write Stooq first-write invariant test**

Run Stooq backfill twice with the same dates and changed close values. Assert that the second run stores zero records and the first close remains.

Run:

```bash
uv run pytest tests/test_backfill.py::test_backfill_stooq_keeps_first_write_wins_for_prices -q
```

Expected: PASS before and after the implementation.

- [x] **Step 3: Wire backfill to storage policy**

Import `append_overwrite_enabled` and call:

```python
stored = store.append(
    records,
    overwrite=append_overwrite_enabled(source.meta.dataset),
)
```

- [x] **Step 4: Run backfill tests**

```bash
uv run pytest tests/test_backfill.py -q
```

Expected: PASS.

### Task 4: Documentation And Verification

**Files:**
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md`
- Modify: `docs/superpowers/plans/2026-06-16-macro-revision-policy.md`

- [x] **Step 1: Update storage policy docs**

Document that `macro` source records are last-write-wins by key, while `prices`, `filings`, and `news` remain first-write-wins.

- [x] **Step 2: Mark acceptance checkboxes**

After tests pass, update the spec and plan status from "구현 중" to "구현 완료" and mark checked items.

- [x] **Step 3: Run full verification**

```bash
uv run ruff check .
uv run mypy mimir
uv run coverage run -m pytest
uv run coverage report --fail-under=80
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 4: Request independent code review**

Dispatch spec compliance review first, then code quality review. Fix Critical and Important issues before committing.

- [x] **Step 5: Commit**

```bash
git add mimir tests docs README.md README.ko.md README.zh.md
git commit -m "feat: add macro revision storage policy"
```
