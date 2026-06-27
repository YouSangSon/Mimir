# Docs Implementation Consistency Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a fresh docs/implementation consistency scan after the deferred-item rechecks and queue or fix the next evidence-backed cleanup.

**Architecture:** This is an audit loop. Use the existing docs health patterns and targeted `rg` scans first; only edit docs/tests if current repo evidence proves a stale current-state claim.

**Tech Stack:** Markdown docs, `tests/test_readme_docs.py` if a guard is needed, pytest, ruff, mypy strict.

---

## File Map

- Modify: `PLAN.md` — mark the active loop as `DOCS-IMPLEMENTATION-CONSISTENCY-SCAN`.
- Modify if evidence requires it: `BACKLOG.md`, `DECISIONS.md`, `WORKLOG.md`, and the stale docs/tests found by the scan.
- Avoid touching implementation unless a doc claim exposes a real behavior bug.

## Task 1: Plan Commit

**Files:**
- Create: `docs/superpowers/plans/2026-06-28-docs-implementation-consistency-scan.md`
- Modify: `PLAN.md`

- [ ] **Step 1: Update `PLAN.md`**

Expected current loop block:

```markdown
## Current Loop

`DOCS-IMPLEMENTATION-CONSISTENCY-SCAN`

- Plan: `docs/superpowers/plans/2026-06-28-docs-implementation-consistency-scan.md`
- Backlog: `BACKLOG.md`
- Work log: `WORKLOG.md`
- Decisions: `DECISIONS.md`
```

- [ ] **Step 2: Run diff check**

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 3: Commit the plan**

```bash
git add PLAN.md docs/superpowers/plans/2026-06-28-docs-implementation-consistency-scan.md
git commit -m "docs(docs): plan docs implementation consistency scan"
```

## Task 2: Scan

**Files:**
- Read-only unless evidence finds a stale claim.

- [ ] **Step 1: Run targeted stale-current-state searches**

Use `rg` to inspect:

- Old test-count claims outside historical worklog evidence.
- Deferred catalog items whose implementation or recheck state changed.
- README/Further Reading links and reference-doc language-boundary claims.
- Config/CLI names mentioned in README/reference docs against `pyproject.toml` and source.
- "future/not implemented" phrases in current docs for features that are now implemented.

- [ ] **Step 2: Decide the next smallest action**

If one stale current-state claim is found, make that the loop target. If the scan finds no stronger evidence, record the no-op scan in `WORKLOG.md` and queue the next evidence-backed candidate in `BACKLOG.md`.

## Task 3: Fix or Record Evidence

**Files:**
- Modify only the files justified by Task 2.

- [ ] **Step 1: Add a RED guard if the cleanup should remain fixed**

Use the smallest docs guard that fails on the stale claim and passes after the doc update.

- [ ] **Step 2: Update docs and root state**

Update `BACKLOG.md`, `DECISIONS.md` if a durable decision was made, and `WORKLOG.md` with scan evidence.

## Task 4: Verify, Review, Commit

**Files:**
- All files touched by Task 3.

- [ ] **Step 1: Run focused guard if added**

Expected: PASS.

- [ ] **Step 2: Run full gates**

```bash
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

- [ ] **Step 3: Review**

Use reviewers if changes touch tests, durable docs, or behavior. Fix Critical/Important findings before committing.

- [ ] **Step 4: Commit exact files**

Use `git add <exact files>` and a scoped commit message. Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.
