# Captured Index Measurement Recheck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recheck whether current `DataReader._captured_date_index` measurement evidence proves `read_captured_window()` rebuild cost has crossed the persistent-index threshold.

**Architecture:** Prefer no production code unless measured evidence proves the in-memory captured-date index is now too expensive. The existing lazy solution is one in-memory index per `DataReader` revision plus `records/days/elapsed_ms` debug logging. If no current measurement crosses the threshold, keep persistent indexing deferred and queue the next bounded docs-truth or verification cleanup.

**Tech Stack:** Python 3.14, existing `mimir.storage.reader.DataReader`, pytest docs guards, `rg`, `find`, `wc`, ruff, mypy strict.

---

## File Map

- Modify: `PLAN.md` — mark the active loop as `CAPTURED-INDEX-MEASUREMENT-RECHECK`.
- Inspect: `mimir/storage/reader.py`.
- Inspect: `tests/analysis/test_reader.py`.
- Inspect: `tests/test_readme_docs.py`.
- Inspect: `docs/IMPROVEMENTS.md`.
- Inspect: `docs/architecture/improvement-catalog.md`.
- Inspect: `docs/architecture/extensibility/README.md`.
- Inspect: `DECISIONS.md`, `WORKLOG.md`, `BACKLOG.md`.
- Inspect: local `data/` JSONL scale if present.
- Modify if deferred: `tests/test_readme_docs.py`, `BACKLOG.md`, `DECISIONS.md`, `WORKLOG.md`, README EN/KO/ZH counts if a guard is added.
- Modify if measurement proves implementation is needed: stop at a Draft design or plan for the implementation slice; do not implement the persistent index in this loop.

## Task 1: Plan Commit

**Files:**
- Create: `docs/superpowers/plans/2026-06-29-captured-index-measurement-recheck.md`
- Modify: `PLAN.md`

- [ ] **Step 1: Update `PLAN.md`**

Expected current loop block:

```markdown
## Current Loop

`CAPTURED-INDEX-MEASUREMENT-RECHECK`

- Plan: `docs/superpowers/plans/2026-06-29-captured-index-measurement-recheck.md`
- Backlog: `BACKLOG.md`
- Work log: `WORKLOG.md`
- Decisions: `DECISIONS.md`
```

- [ ] **Step 2: Run diff check**

Run:

```bash
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 3: Commit the plan**

Run:

```bash
git add PLAN.md docs/superpowers/plans/2026-06-29-captured-index-measurement-recheck.md
git commit -m "docs(storage): plan captured index measurement recheck"
```

Expected: local plan commit only. Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.

## Task 2: Recheck Measurement Evidence

**Files:**
- Read: files listed in File Map.

- [ ] **Step 1: Verify current reader behavior**

Run:

```bash
rg -n "read_captured_window|_captured_date_index|captured-date index rebuilt|records/days/elapsed_ms" mimir/storage/reader.py tests/analysis/test_reader.py tests/test_readme_docs.py docs/IMPROVEMENTS.md docs/architecture/improvement-catalog.md DECISIONS.md WORKLOG.md
```

Expected: evidence shows in-memory index reuse, revision invalidation, and debug measurement logging already exist.

- [ ] **Step 2: Check local data scale**

Run:

```bash
find data -type f -name "*.jsonl" 2>/dev/null | wc -l | tr -d " "
find data -path "*/news/*.jsonl" -o -path "data/news/*.jsonl" 2>/dev/null | head -20
```

Expected: if there is no local data corpus, record that no local measurement can prove the threshold was crossed.

- [ ] **Step 3: Run existing focused guards**

Run:

```bash
uv run pytest tests/analysis/test_reader.py::test_captured_index_rebuild_logs_scan_scale tests/analysis/test_reader.py::test_read_captured_window_reuses_one_dataset_scan_for_multiple_windows tests/test_readme_docs.py::test_captured_date_persistent_index_recheck_keeps_measurement_based_deferral -q
```

Expected: 3 passed.

## Task 3: Record Decision and Queue Next Item

**Files:**
- Modify: `BACKLOG.md`
- Modify: `DECISIONS.md`
- Modify: `WORKLOG.md`
- Modify: `tests/test_readme_docs.py` and README EN/KO/ZH counts only if adding a new guard is the smallest durable check.

- [ ] **Step 1: If no measurement threshold is proven, keep deferral**

Add a `CAPTURED-INDEX-MEASUREMENT-RECHECK` entry to `DECISIONS.md` saying:

- in-memory captured-date index reuse still exists,
- `records/days/elapsed_ms` measurement logging still exists,
- local repo evidence does not prove rebuild cost crossed the persistent-index threshold,
- persistent on-disk index remains deferred.

- [ ] **Step 2: Update root state**

Move `CAPTURED-INDEX-MEASUREMENT-RECHECK` to `BACKLOG.md` Done and queue the next bounded evidence-backed item from the live catalog.

Expected next queue item if no stronger candidate appears:

```markdown
1. Recheck whether unified signal-weight tuning has current backtest evidence;
   if not, keep per-signal YAML weight knobs deferred and queue the next
   bounded docs-truth or verification cleanup.
```

- [ ] **Step 3: Update worklog**

Record:

- reader/code evidence,
- local data scale,
- focused guard results,
- full verification results,
- review results.

## Task 4: Verify, Review, Commit

**Files:**
- Files touched in Task 3.

- [ ] **Step 1: Run focused guards**

Run:

```bash
uv run pytest tests/analysis/test_reader.py::test_captured_index_rebuild_logs_scan_scale tests/analysis/test_reader.py::test_read_captured_window_reuses_one_dataset_scan_for_multiple_windows tests/test_readme_docs.py::test_captured_date_persistent_index_recheck_keeps_measurement_based_deferral -q
```

Expected: 3 passed.

- [ ] **Step 2: Run full gates**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q | tail -1
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: all commands pass.

- [ ] **Step 3: Run touched-file secrets scan**

Run:

```bash
git diff --name-only | xargs rg -n "(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z]{20,}|ghp_[0-9A-Za-z]{20,}|github_pat_[0-9A-Za-z_]{20,}|xox[baprs]-[0-9A-Za-z-]+|-----BEGIN .*PRIVATE KEY|[A-Z0-9_]*(API_KEY|TOKEN|SECRET|USER_AGENT))" || true
```

Expected: no real secrets; any matches are existing placeholders, env names, or CI secret names.

- [ ] **Step 4: Review**

Use spec and quality reviewers. Fix Critical and Important findings before committing.

- [ ] **Step 5: Commit exact files**

Run:

```bash
git add BACKLOG.md DECISIONS.md WORKLOG.md
git commit -m "docs(storage): keep captured index measurement-gated"
```

If a docs guard is added, include `tests/test_readme_docs.py` and README count files in exact staging. Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.

## Self-Review

- Spec coverage: the plan covers measurement evidence, local data scale, existing focused guards, deferred decision recording, root queue update, verification, review, and exact commit.
- Placeholder scan: no bare placeholder marker and no unspecified implementation step remains.
- Type consistency: commands reference existing files and currently visible pytest test names.
