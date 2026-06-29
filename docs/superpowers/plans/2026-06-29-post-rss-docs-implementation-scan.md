# Post-RSS Docs Implementation Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a fresh docs/implementation consistency scan after the generic RSS discovery boundary recheck and queue the next evidence-backed item.

**Architecture:** This is an audit and queueing loop. Search current-state docs and tests for stale claims, compare them against source and recent decisions, then record the strongest evidence-backed next item in `BACKLOG.md`. Historical plans, worklogs, handoffs, and old specs may mention past states; do not treat them as stale unless they present themselves as current truth.

**Tech Stack:** Markdown docs, `rg`, Python 3.14 source/tests, `tests/test_readme_docs.py` if a guard is needed, pytest, ruff, mypy strict.

---

## File Map

- Modify: `PLAN.md` — mark the active loop as `POST-RSS-DOCS-IMPLEMENTATION-SCAN`.
- Inspect: `README.md`, `README.ko.md`, `README.zh.md`.
- Inspect: `BACKLOG.md`, `DECISIONS.md`, `WORKLOG.md`.
- Inspect: `docs/IMPROVEMENTS.md`.
- Inspect: `docs/architecture/improvement-catalog.md`, `docs/architecture/roadmap.md`.
- Inspect: `docs/reference/cli.md`, `docs/reference/config/sources.md`, `docs/reference/config/watchlist.md`.
- Inspect: `pyproject.toml`, `.github/workflows/*.yml`, `mimir/`, and `tests/test_readme_docs.py`.
- Modify after the scan: `BACKLOG.md` and `WORKLOG.md`.
- Modify only if the scan makes a durable scope decision: `DECISIONS.md`.
- Do not fix implementation or feature docs in this loop; queue the next bounded item instead.

## Task 1: Plan Commit

**Files:**
- Create: `docs/superpowers/plans/2026-06-29-post-rss-docs-implementation-scan.md`
- Modify: `PLAN.md`

- [ ] **Step 1: Update `PLAN.md`**

Expected current loop block:

```markdown
## Current Loop

`POST-RSS-DOCS-IMPLEMENTATION-SCAN`

- Plan: `docs/superpowers/plans/2026-06-29-post-rss-docs-implementation-scan.md`
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
git add PLAN.md docs/superpowers/plans/2026-06-29-post-rss-docs-implementation-scan.md
git commit -m "docs(docs): plan post-rss docs scan"
```

Expected: a local plan commit. Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.

## Task 2: Run Current-State Scan

**Files:**
- Read: all files listed in File Map.

- [ ] **Step 1: Search current docs for stale implementation claims**

Run:

```bash
rg -n "not implemented|future|deferred|Draft|automatic/live|R1o Draft|production code|stale|TO""DO|TB""D" README.md README.ko.md README.zh.md BACKLOG.md DECISIONS.md docs/IMPROVEMENTS.md docs/architecture docs/reference tests/test_readme_docs.py
```

Expected: every hit is either true current-state wording, a historical decision with date context, or a candidate stale current-state claim.

- [ ] **Step 2: Search for stale test-count claims**

Run:

```bash
rg -n "665|667|668|passing|tests collected|coverage|ruff|mypy" README.md README.ko.md README.zh.md BACKLOG.md DECISIONS.md docs/IMPROVEMENTS.md docs/architecture docs/reference tests/test_readme_docs.py
```

Expected: current README count matches `uv run pytest --collect-only -q | tail -1`; old counts only appear in dated `WORKLOG.md` or historical plans/specs, not current-state docs.

- [ ] **Step 3: Compare CLI script metadata to source entry points**

Run:

```bash
uv run pytest tests/test_pyproject_scripts.py -q
```

Expected: 3 passed.

- [ ] **Step 4: Compare docs links to files**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_readme_links_all_reference_docs -q
```

Expected: 1 passed.

## Task 3: Queue the Smallest Evidence-Backed Action

**Files:**
- Modify: `BACKLOG.md`
- Modify: `WORKLOG.md`
- Modify only if a durable decision is made: `DECISIONS.md`

- [ ] **Step 1: Pick one next item from scan evidence**

If the scan finds a stale current-state claim, queue that exact doc-truth cleanup as the next item. Name the file and stale phrase in `BACKLOG.md`.

If the scan finds no stronger stale current-state claim, queue this item:

```markdown
1. Recheck whether any live improvement-catalog deferred item now has new
   measurement or policy evidence; if not, queue the next bounded docs-truth
   cleanup.
```

- [ ] **Step 2: Record scan evidence**

Update `WORKLOG.md` with:

- the scan commands from Task 2,
- whether each hit was current truth, historical context, or a queued candidate,
- the next queued item,
- verification commands and review status.

Add a `DECISIONS.md` entry only if the scan changes durable scope. If the scan only queues the next item, leave `DECISIONS.md` untouched.

## Task 4: Verify, Review, Commit

**Files:**
- `BACKLOG.md`
- `WORKLOG.md`
- `DECISIONS.md` only if changed by Task 3

- [ ] **Step 1: Run full gates**

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

- [ ] **Step 2: Run a touched-file secrets scan**

Run:

```bash
git diff --name-only | xargs rg -n "(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z]{20,}|ghp_[0-9A-Za-z]{20,}|github_pat_[0-9A-Za-z_]{20,}|xox[baprs]-[0-9A-Za-z-]+|-----BEGIN .*PRIVATE KEY|[A-Z0-9_]*(API_KEY|TOKEN|SECRET|USER_AGENT))" || true
```

Expected: no real secrets; any matches are documented placeholders, env var names, or CI secret names.

- [ ] **Step 3: Review**

Use spec and quality reviewers if the loop changes tests, durable docs, or behavior. Fix Critical and Important findings before committing.

- [ ] **Step 4: Commit exact files**

If only `BACKLOG.md` and `WORKLOG.md` changed, use:

```bash
git add BACKLOG.md WORKLOG.md
git commit -m "docs(docs): record post-rss docs scan"
```

If `DECISIONS.md` also changed, use:

```bash
git add BACKLOG.md WORKLOG.md DECISIONS.md
git commit -m "docs(docs): record post-rss docs scan"
```

Expected: local commit only. Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.

## Self-Review

- Spec coverage: the plan covers the queued post-RSS docs/implementation scan, current-state searches, CLI metadata comparison, link guard, no-op recording, verification, review, and exact commit.
- Placeholder scan: no bare placeholder marker and no unspecified implementation step remains.
- Type consistency: all commands use existing files and current pytest guard names visible in the repo.
