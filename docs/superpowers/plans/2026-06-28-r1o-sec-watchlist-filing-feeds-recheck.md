# R1o SEC Watchlist Filing Feeds Recheck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recheck the R1o SEC watchlist filing feeds Draft spec against current source contracts and either promote the smallest implementation slice or keep it Draft with evidence.

**Architecture:** Reuse the existing SEC-only RSS path. Do not add generic discovery, crawling, vendor URL inference, or a new provider abstraction.

**Tech Stack:** Python 3.14, pydantic config models, existing RSS resolver/source builder, pytest docs/source guards, ruff, mypy strict.

---

## File Map

- Modify: `PLAN.md` — mark the active loop as `R1O-SEC-WATCHLIST-FILING-FEEDS-RECHECK`.
- Inspect: `docs/decisions/tech-spec/sources/R1o-SEC-WATCHLIST-FILING-FEEDS_sec_watchlist_filing_feeds_tech_spec_2026_06_28.md`.
- Inspect/modify if promoted: `mimir/sources/config.py`, `mimir/core/builder.py`, `mimir/sources/rss_catalog.py`, and existing RSS/config tests.
- Modify: `tests/test_readme_docs.py`, `BACKLOG.md`, `DECISIONS.md`, `WORKLOG.md`, and README EN/KO/ZH counts if a guard is added.

## Task 1: Plan Commit

**Files:**
- Create: `docs/superpowers/plans/2026-06-28-r1o-sec-watchlist-filing-feeds-recheck.md`
- Modify: `PLAN.md`

- [ ] **Step 1: Update `PLAN.md`**

Expected current loop block:

```markdown
## Current Loop

`R1O-SEC-WATCHLIST-FILING-FEEDS-RECHECK`

- Plan: `docs/superpowers/plans/2026-06-28-r1o-sec-watchlist-filing-feeds-recheck.md`
- Backlog: `BACKLOG.md`
- Work log: `WORKLOG.md`
- Decisions: `DECISIONS.md`
```

- [ ] **Step 2: Run diff check**

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 3: Commit the plan**

```bash
git add PLAN.md docs/superpowers/plans/2026-06-28-r1o-sec-watchlist-filing-feeds-recheck.md
git commit -m "docs(sources): plan r1o watchlist filing feeds recheck"
```

## Task 2: Recheck Evidence

**Files:**
- Read: `mimir/sources/config.py`
- Read: `mimir/core/builder.py`
- Read: `mimir/sources/rss_catalog.py`
- Read: existing tests under `tests/sources/`, `tests/core/test_builder.py`, `tests/test_collect.py`, `tests/test_run.py`, and `tests/test_backfill.py`.

- [ ] **Step 1: Verify current contracts**

Current expected evidence:

- `SourcesConfig` has `rss_sec_company_filings`, `rss_sec_ticker_cik_map_path`, and `rss_sec_ticker_cik_map_refresh`.
- `_RssSecBlock` has `company_filings`, `ticker_cik_map_path`, and `ticker_cik_map_refresh`.
- There is no `watchlist_company_filings` field yet.
- `SecCompanyFilingFeed` and `resolve_sec_company_filing_feeds()` already validate ticker/CIK/form/count/owner and duplicate feed behavior.
- CLI source builders already load `watchlist.yaml` before building sources.

- [ ] **Step 2: Choose promote vs defer**

Promote only if the smallest slice is still:

- SEC-only.
- Default false.
- Uses `watchlist.us` only.
- Reuses `SecCompanyFilingFeed` and existing CIK mapping/refresh.
- Adds no live discovery, HTML crawling, or vendor URL inference.

If any of those are not true, keep R1o Draft and record why.

## Task 3: If Promoted, Add RED Tests First

**Files:**
- Test: `tests/sources/test_config.py`
- Test: `tests/core/test_builder.py`
- Test: CLI tests only if source build needs a new argument boundary.

- [ ] **Step 1: Add config parsing guard**

Assert default disabled and enabled form parses to a small config object.

- [ ] **Step 2: Add builder guard**

Assert enabled config plus `watchlist={"us": ["AAPL"], "kr": []}` produces a generated `SecCompanyFilingFeed(ticker="AAPL", symbol="AAPL")` through the existing RSS source path.

- [ ] **Step 3: Keep disabled path unchanged**

Assert default/disabled config generates zero watchlist-derived feeds.

## Task 4: If Deferred, Add Docs Guard

**Files:**
- Modify: `tests/test_readme_docs.py`

- [ ] **Step 1: Add a focused guard**

Guard that R1o remains Draft, current config source has no `watchlist_company_filings`, and docs keep generic discovery deferred.

## Task 5: Verify, Review, Commit

**Files:**
- All files touched by Task 3 or Task 4.

- [ ] **Step 1: Run focused tests**

Run only the new focused tests first.

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

Use spec and quality reviewers. Fix Critical/Important issues before committing.

- [ ] **Step 4: Commit exact files**

Use `git add <exact files>` and a scoped commit message. Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.
