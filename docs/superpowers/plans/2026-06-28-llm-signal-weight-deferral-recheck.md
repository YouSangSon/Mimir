# LLM Signal Weight Deferral Recheck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recheck the LLM signal weight YAML exposure deferral and keep it deferred unless current repo evidence supports a unified signal-weight tuning spec.

**Architecture:** This is a docs-truth loop, not a config feature. Built-in signal weights are currently code constants and the existing config surface only exposes specific behavior knobs; the lazy fix is to guard that `llm_sentiment` does not get a one-off YAML weight key.

**Tech Stack:** Markdown docs, `tests/test_readme_docs.py`, pytest, ruff, mypy strict.

---

## File Map

- Modify: `PLAN.md` — mark the active loop as `LLM-SIGNAL-WEIGHT-DEFERRAL-RECHECK`.
- Modify: `tests/test_readme_docs.py` — add one docs/current-state guard for the weight-deferral contract.
- Modify: `BACKLOG.md` — move this loop to Done and queue the next small docs-truth item.
- Modify: `DECISIONS.md` — record why one-off `llm_sentiment` weight YAML stays deferred.
- Modify: `WORKLOG.md` — record evidence, RED/GREEN, verification, and review.
- Modify: `README.md`, `README.ko.md`, `README.zh.md` — update test counts only if collect-only changes.

## Task 1: Plan Commit

**Files:**
- Create: `docs/superpowers/plans/2026-06-28-llm-signal-weight-deferral-recheck.md`
- Modify: `PLAN.md`

- [ ] **Step 1: Update `PLAN.md`**

Expected current loop block:

```markdown
## Current Loop

`LLM-SIGNAL-WEIGHT-DEFERRAL-RECHECK`

- Plan: `docs/superpowers/plans/2026-06-28-llm-signal-weight-deferral-recheck.md`
- Backlog: `BACKLOG.md`
- Work log: `WORKLOG.md`
- Decisions: `DECISIONS.md`
```

- [ ] **Step 2: Run diff check**

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 3: Commit the plan**

```bash
git add PLAN.md docs/superpowers/plans/2026-06-28-llm-signal-weight-deferral-recheck.md
git commit -m "docs(analysis): plan llm weight deferral recheck"
```

## Task 2: RED Docs Guard

**Files:**
- Modify: `tests/test_readme_docs.py`

- [ ] **Step 1: Add a failing guard**

Add a test named `test_llm_signal_weight_yaml_deferral_recheck_keeps_unified_weight_tuning_deferred`.

The test should assert:

- Built-in signals keep module-level `WEIGHT` constants for current weights.
- `build_signals()` does not pass a config-derived `weight=` to `LlmSentimentSignal`.
- `SourcesConfig` / `_TopLevelSourcesConfig` expose `llm_sentiment_enabled` and `llm_sentiment_max_headlines`, but not `llm_sentiment_weight`.
- Current scoring/config docs say weights are code constants, not user YAML.
- The catalog keeps `LLM signal weight YAML 노출` in deferred state and says any tuning should cover all signals.
- `BACKLOG.md`, `DECISIONS.md`, and `WORKLOG.md` record `LLM-SIGNAL-WEIGHT-DEFERRAL-RECHECK`.

- [ ] **Step 2: Run RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_llm_signal_weight_yaml_deferral_recheck_keeps_unified_weight_tuning_deferred -q
```

Expected: FAIL before the root docs record this loop.

## Task 3: GREEN Docs Update

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `BACKLOG.md`
- Modify: `DECISIONS.md`
- Modify: `WORKLOG.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Keep production config unchanged**

Do not add `llm_sentiment_weight`. Current evidence shows one-off LLM tuning would be inconsistent with other built-in signal weights.

- [ ] **Step 2: Update root state docs**

Move `LLM-SIGNAL-WEIGHT-DEFERRAL-RECHECK` to `BACKLOG.md` Done, record the decision in `DECISIONS.md`, and add work evidence to `WORKLOG.md`.

- [ ] **Step 3: Update README counts**

After collect-only shows the new count, update all three README badges and test table rows if the count changed.

## Task 4: Verify, Review, Commit

**Files:**
- All files touched in Tasks 2-3.

- [ ] **Step 1: Run focused guard**

```bash
uv run pytest tests/test_readme_docs.py::test_llm_signal_weight_yaml_deferral_recheck_keeps_unified_weight_tuning_deferred -q
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
git commit -m "docs(analysis): keep llm weight tuning unified"
```

Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.
