# Captured Index Deferral Recheck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recheck the captured-date persistent index deferral and keep it deferred unless current repo evidence proves the rebuild scan has become a bottleneck.

**Architecture:** This is a docs-truth loop, not a storage implementation. Mimir already has a per-reader in-memory captured-date index plus DEBUG measurement fields; the lazy fix is to guard that measured deferral instead of adding an on-disk index with no bottleneck evidence.

**Tech Stack:** Markdown docs, `tests/test_readme_docs.py`, pytest, ruff, mypy strict.

---

## File Map

- Modify: `PLAN.md` — mark the active loop as `CAPTURED-INDEX-DEFERRAL-RECHECK`.
- Modify: `tests/test_readme_docs.py` — add one docs guard for the measurement-based deferral contract.
- Modify: `BACKLOG.md` — move this loop to Done and queue the next small docs-truth item.
- Modify: `DECISIONS.md` — record why the persistent index remains deferred.
- Modify: `WORKLOG.md` — record evidence, RED/GREEN, verification, and review.
- Modify: `README.md`, `README.ko.md`, `README.zh.md` — update test counts only if collect-only changes.

## Task 1: Plan Commit

**Files:**
- Create: `docs/superpowers/plans/2026-06-28-captured-index-deferral-recheck.md`
- Modify: `PLAN.md`

- [ ] **Step 1: Update `PLAN.md`**

Expected current loop block:

```markdown
## Current Loop

`CAPTURED-INDEX-DEFERRAL-RECHECK`

- Plan: `docs/superpowers/plans/2026-06-28-captured-index-deferral-recheck.md`
- Backlog: `BACKLOG.md`
- Work log: `WORKLOG.md`
- Decisions: `DECISIONS.md`
```

- [ ] **Step 2: Run diff check**

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 3: Commit the plan**

```bash
git add PLAN.md docs/superpowers/plans/2026-06-28-captured-index-deferral-recheck.md
git commit -m "docs(storage): plan captured index deferral recheck"
```

## Task 2: RED Docs Guard

**Files:**
- Modify: `tests/test_readme_docs.py`

- [ ] **Step 1: Add a failing guard**

Add a test named `test_captured_date_persistent_index_recheck_keeps_measurement_based_deferral`.

The test should assert:

- `docs/superpowers/specs/2026-06-19-captured-date-persistent-index-design.md` says the persistent index is design-only/unimplemented/deferred.
- The design doc keeps `_captured_date_index`, `records`, `days`, `elapsed_ms`, and `먼저 측정하라`.
- `mimir/storage/reader.py` keeps the DEBUG log format with `records=%d`, `days=%d`, and `elapsed_ms=%.1f`.
- `tests/analysis/test_reader.py` keeps `test_captured_index_rebuild_logs_scan_scale`.
- Current architecture and improvements docs keep the measurement-based deferral stance.
- Current docs do not claim the on-disk persistent index is implemented.

- [ ] **Step 2: Run RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_captured_date_persistent_index_recheck_keeps_measurement_based_deferral -q
```

Expected: FAIL before the supporting constant/doc wording exists.

## Task 3: GREEN Docs Update

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `BACKLOG.md`
- Modify: `DECISIONS.md`
- Modify: `WORKLOG.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Keep production code unchanged**

Do not add an on-disk captured-date index. Current evidence shows measurement hooks exist, but no repo evidence proves the scan has crossed the bottleneck threshold.

- [ ] **Step 2: Update root state docs**

Move `CAPTURED-INDEX-DEFERRAL-RECHECK` to `BACKLOG.md` Done, record the deferral decision in `DECISIONS.md`, and add work evidence to `WORKLOG.md`.

- [ ] **Step 3: Update README counts**

After collect-only shows the new count, update all three README badges and test table rows if the count changed.

## Task 4: Verify, Review, Commit

**Files:**
- All files touched in Tasks 2-3.

- [ ] **Step 1: Run focused guard**

```bash
uv run pytest tests/test_readme_docs.py::test_captured_date_persistent_index_recheck_keeps_measurement_based_deferral -q
```

Expected: PASS.

- [ ] **Step 2: Run docs suite**

```bash
uv run pytest tests/test_readme_docs.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full gates**

```bash
uv run pytest --collect-only -q
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Request reviews**

Dispatch a spec reviewer and quality reviewer with the intended file list and gate output. Fix Critical/Important issues before committing.

- [ ] **Step 5: Commit exact files**

```bash
git add tests/test_readme_docs.py BACKLOG.md DECISIONS.md WORKLOG.md README.md README.ko.md README.zh.md
git commit -m "docs(storage): keep captured index deferral measured"
```

Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.
