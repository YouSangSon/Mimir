# Captured News Window Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make repeated captured-news window reads during one analysis run reuse a cached in-memory index instead of rescanning all NEWS partitions for every symbol and signal.

**Status:** Completed in implementation commit `0d92e158ab518fcc82cc2943e292342c37d0e654`; this plan is archived with the C2a documentation follow-up.

**Architecture:** Keep the canonical git-as-DB layout unchanged: `NEWS` records remain partitioned by published timestamp (`ts.date()`). `DataReader` builds a rebuildable in-memory index from stored records grouped by `captured_at.date()` on first captured-window access for a dataset. The cache is tied to the `JsonlStore` write revision so normal store writes invalidate stale reader cache entries.

**Tech Stack:** Python 3.14, `pathlib`, `datetime.date`, pytest, current `JsonlStore` and `DataReader` APIs.

## Global Constraints

- Do not change on-disk JSONL layout, idempotency keys, or record serialization.
- Do not add persistent index files or migration steps.
- Preserve late-captured article semantics: a record with old `ts.date()` and current `captured_at.date()` must still be returned by captured-window reads.
- Preserve `read_captured_window(dataset, symbol=..., since=..., until=...)` inclusive bounds and symbol filtering.
- Keep LLM sentiment off-by-default and do not add network calls.
- Keep provider RSS discovery, SEC mapping file download/cache, and watchlist-driven feed generation out of scope.
- Use TDD: write at least one failing pytest that proves repeated captured-window reads no longer rescan the full dataset.

---

### Task 1: In-Memory Captured-Window Index

**Files:**
- Modify: `mimir/storage/jsonl_store.py`
- Modify: `mimir/storage/reader.py`
- Modify: `tests/analysis/test_reader.py`

**Interfaces:**
- Consumes: `JsonlStore.read_all(dataset)` and `Record.captured_at`
- Produces: `DataReader.read_captured_window()` with the same public behavior, plus per-reader cached captured-date buckets invalidated when `JsonlStore.revision` changes.

- [x] **Step 1: Write the failing repeated-window scan test**

Add a small counting store to `tests/analysis/test_reader.py`:

```python
class CountingStore(JsonlStore):
    def __init__(self, root: Path) -> None:
        super().__init__(root=root)
        self.read_all_calls = 0

    def read_all(self, dataset: Dataset):
        self.read_all_calls += 1
        yield from super().read_all(dataset)
```

Then add:

```python
def test_read_captured_window_reuses_one_dataset_scan_for_multiple_windows(tmp_path: Path):
    store = CountingStore(root=tmp_path)
    store.append(
        [
            _rec("AAPL", 20, Dataset.NEWS, captured_day=24),
            _rec("AAPL", 30, Dataset.NEWS, captured_day=31),
            _rec("MSFT", 30, Dataset.NEWS, captured_day=31),
        ]
    )
    reader = DataReader(store)

    today = reader.read_captured_window(
        Dataset.NEWS, since=date(2026, 5, 31), until=date(2026, 5, 31)
    )
    baseline = reader.read_captured_window(
        Dataset.NEWS, since=date(2026, 5, 24), until=date(2026, 5, 30)
    )
    msft_today = reader.read_captured_window(
        Dataset.NEWS,
        symbol="MSFT",
        since=date(2026, 5, 31),
        until=date(2026, 5, 31),
    )

    assert {r.idempotency_key for r in today} == {
        "news:AAPL:30:31",
        "news:MSFT:30:31",
    }
    assert {r.idempotency_key for r in baseline} == {"news:AAPL:20:24"}
    assert {r.symbol for r in msft_today} == {"MSFT"}
    assert store.read_all_calls == 1
```

- [x] **Step 2: Run the red test**

Run:

```bash
uv run pytest tests/analysis/test_reader.py::test_read_captured_window_reuses_one_dataset_scan_for_multiple_windows -q
```

Expected: FAIL because current `DataReader.read_captured_window()` calls `JsonlStore.read_all()` once per captured-window request.

- [x] **Step 3: Add cache-invalidation regression coverage**

Add:

```python
def test_read_captured_window_cache_invalidates_after_store_append(tmp_path: Path):
    store = CountingStore(root=tmp_path)
    reader = DataReader(store)

    assert reader.read_captured_window(
        Dataset.NEWS, since=date(2026, 5, 31), until=date(2026, 5, 31)
    ) == []
    store.append([_rec("AAPL", 30, Dataset.NEWS, captured_day=31)])

    recs = reader.read_captured_window(
        Dataset.NEWS, since=date(2026, 5, 31), until=date(2026, 5, 31)
    )

    assert {r.idempotency_key for r in recs} == {"news:AAPL:30:31"}
    assert store.read_all_calls == 2
```

This is a preservation test for current freshness semantics. It may pass before the cache implementation; it must still pass after the cache is added.

- [x] **Step 4: Implement `JsonlStore.revision`**

Add a private integer revision to `JsonlStore`:

```python
self._revision = 0
```

Expose it with:

```python
@property
def revision(self) -> int:
    return self._revision
```

Increment the revision whenever `append()` or `replace_partition()` changes the stored data. Do not increment on no-op writes.

- [x] **Step 5: Implement the captured-date cache**

In `mimir/storage/reader.py`, keep a private cache keyed by dataset:

```python
_captured_index: dict[Dataset, tuple[int, dict[date, tuple[Record, ...]]]]
```

Build it by scanning `self._store.read_all(dataset)` once and grouping records by `rec.captured_at.date()`. On each `read_captured_window()` call, reuse the index when `store.revision` matches. Otherwise rebuild it.

Filtering rules:
- If `symbol` is provided, filter records by `rec.symbol`.
- If `since` is provided, skip captured dates before it.
- If `until` is provided, skip captured dates after it.
- Return results in chronological captured-date order, preserving partition/read order inside each captured date.

- [x] **Step 6: Run the targeted reader tests**

Run:

```bash
uv run pytest tests/analysis/test_reader.py -q
```

Expected: all reader tests pass.

- [x] **Step 7: Commit implementation**

```bash
git add mimir/storage/jsonl_store.py mimir/storage/reader.py tests/analysis/test_reader.py
git commit -m "perf(analysis): cache captured news windows per reader"
```

Implementation commit: `0d92e158ab518fcc82cc2943e292342c37d0e654`.

- [x] **Step 8: Add post-review `replace_partition()` invalidation regression**

Add a reader test proving a cache built from one NEWS partition is rebuilt after
`JsonlStore.replace_partition()` changes that partition. This closes the direct
coverage gap for the documented revision-invalidation contract.
