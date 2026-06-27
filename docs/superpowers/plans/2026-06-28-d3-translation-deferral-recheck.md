# D3 Translation Deferral Recheck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recheck the D3 internal spec/roadmap translation deferral against the current README/reference-doc language split.

**Architecture:** This is a docs-truth loop, not a translation project. Root README files already provide trilingual entry points; detailed `docs/` material remains Korean-first unless evidence justifies a bounded reference-doc translation slice.

**Tech Stack:** Markdown docs, `tests/test_readme_docs.py`, pytest, ruff, mypy strict.

---

## File Map

- Modify: `PLAN.md` — mark the active loop as `D3-TRANSLATION-DEFERRAL-RECHECK`.
- Modify: `tests/test_readme_docs.py` — add one docs/current-state guard for the language-scope contract.
- Modify: `docs/architecture/improvement-catalog.md` — keep the D3 deferral row precise about README x3 vs Korean-first detailed docs.
- Modify: `BACKLOG.md` — move this loop to Done and queue the next small consistency scan.
- Modify: `DECISIONS.md` — record why broad internal translation stays deferred.
- Modify: `WORKLOG.md` — record evidence, RED/GREEN, verification, and review.
- Modify: `README.md`, `README.ko.md`, `README.zh.md` — update test counts only if collect-only changes.

## Task 1: Plan Commit

**Files:**
- Create: `docs/superpowers/plans/2026-06-28-d3-translation-deferral-recheck.md`
- Modify: `PLAN.md`

- [ ] **Step 1: Update `PLAN.md`**

Expected current loop block:

```markdown
## Current Loop

`D3-TRANSLATION-DEFERRAL-RECHECK`

- Plan: `docs/superpowers/plans/2026-06-28-d3-translation-deferral-recheck.md`
- Backlog: `BACKLOG.md`
- Work log: `WORKLOG.md`
- Decisions: `DECISIONS.md`
```

- [ ] **Step 2: Run diff check**

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 3: Commit the plan**

```bash
git add PLAN.md docs/superpowers/plans/2026-06-28-d3-translation-deferral-recheck.md
git commit -m "docs(docs): plan d3 translation deferral recheck"
```

## Task 2: RED Docs Guard

**Files:**
- Modify: `tests/test_readme_docs.py`

- [ ] **Step 1: Add a failing guard**

Add a test named `test_d3_translation_deferral_recheck_keeps_readmes_trilingual_and_docs_korean_first`.

The test should assert:

- Root README files keep their English/Korean/Chinese language switchers.
- Each README links to the key reference docs.
- The D3 catalog row says broad internal docs stay Korean-first/KO-only and README x3 are trilingual.
- The existing runtime-config plan keeps the Korean-first policy for project docs under `docs/`.
- Sample detailed docs are Korean-first.
- No `docs/en`, `docs/zh`, `docs/reference/en`, or `docs/reference/zh` translation tree exists.
- `BACKLOG.md`, `DECISIONS.md`, and `WORKLOG.md` record `D3-TRANSLATION-DEFERRAL-RECHECK`.

- [ ] **Step 2: Run RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_d3_translation_deferral_recheck_keeps_readmes_trilingual_and_docs_korean_first -q
```

Expected: FAIL before the root docs record this loop.

## Task 3: GREEN Docs Update

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `BACKLOG.md`
- Modify: `DECISIONS.md`
- Modify: `WORKLOG.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Keep translation work deferred**

Do not translate the 112 internal spec/plan/tech-spec files. The current contract is trilingual root README navigation plus Korean-first detailed project docs.

- [ ] **Step 2: Update root state docs**

Move `D3-TRANSLATION-DEFERRAL-RECHECK` to `BACKLOG.md` Done, record the decision in `DECISIONS.md`, and add work evidence to `WORKLOG.md`.

- [ ] **Step 3: Queue the next loop**

If no deferred catalog item is clearly next, queue a fresh docs/implementation consistency scan after the deferral rechecks.

- [ ] **Step 4: Update README counts**

After collect-only shows the new count, update all three README badges and test table rows if the count changed.

## Task 4: Verify, Review, Commit

**Files:**
- All files touched in Tasks 2-3.

- [ ] **Step 1: Run focused guard**

```bash
uv run pytest tests/test_readme_docs.py::test_d3_translation_deferral_recheck_keeps_readmes_trilingual_and_docs_korean_first -q
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
git add tests/test_readme_docs.py docs/architecture/improvement-catalog.md BACKLOG.md DECISIONS.md WORKLOG.md README.md README.ko.md README.zh.md
git commit -m "docs(docs): keep d3 translation scope bounded"
```

Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.
