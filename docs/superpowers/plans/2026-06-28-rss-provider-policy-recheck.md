# RSS Provider Policy Recheck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recheck the deferred RSS discovery/provider-policy backlog item and promote only the SEC official-source watchlist slice to a draft tech spec while keeping generic provider discovery deferred.

**Architecture:** This is a docs-truth/spec loop, not production code. The repo already has SEC company filing RSS URL expansion, ticker input, local CIK lookup, and opt-in CIK map refresh; this loop records the narrow next product decision without adding new source behavior.

**Tech Stack:** Markdown docs, `tests/test_readme_docs.py`, pytest, ruff, mypy.

---

## File Map

- Modify: `PLAN.md` — mark the active loop as `RSS-PROVIDER-POLICY-RECHECK`.
- Modify: `tests/test_readme_docs.py` — add one docs guard for the new draft spec and deferred generic discovery boundary.
- Create: `docs/decisions/tech-spec/sources/R1o-SEC-WATCHLIST-FILING-FEEDS_sec_watchlist_filing_feeds_tech_spec_2026_06_28.md` — draft tech spec for an opt-in SEC-only watchlist feed generation slice.
- Modify: `docs/decisions/tech-spec/README.md` — link the new draft spec.
- Modify: `docs/architecture/improvement-catalog.md` — add R1o as a draft spec and keep generic provider discovery deferred.
- Modify: `docs/IMPROVEMENTS.md` — record that generic discovery remains deferred and R1o is the promoted SEC-only slice.
- Modify: `BACKLOG.md` — move this loop to Done and queue the next small recheck item.
- Modify: `DECISIONS.md` — record the provider-policy decision with official SEC source links.
- Modify: `WORKLOG.md` — record research, RED/GREEN evidence, gates, and review.
- Modify: `README.md`, `README.ko.md`, `README.zh.md` — update test count if collect-only changes.

## Task 1: Plan Commit

**Files:**
- Create: `docs/superpowers/plans/2026-06-28-rss-provider-policy-recheck.md`
- Modify: `PLAN.md`

- [ ] **Step 1: Update `PLAN.md`**

Expected current loop block:

```markdown
## Current Loop

`RSS-PROVIDER-POLICY-RECHECK`

- Plan: `docs/superpowers/plans/2026-06-28-rss-provider-policy-recheck.md`
- Backlog: `BACKLOG.md`
- Work log: `WORKLOG.md`
- Decisions: `DECISIONS.md`
```

- [ ] **Step 2: Run diff check**

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 3: Commit the plan**

```bash
git add PLAN.md docs/superpowers/plans/2026-06-28-rss-provider-policy-recheck.md
git commit -m "docs(sources): plan rss provider policy recheck"
```

## Task 2: RED Docs Guard

**Files:**
- Modify: `tests/test_readme_docs.py`

- [ ] **Step 1: Add a failing guard**

Add a test named `test_rss_provider_policy_recheck_promotes_only_sec_watchlist_spec`.

The test should assert:

- `docs/decisions/tech-spec/sources/R1o-SEC-WATCHLIST-FILING-FEEDS_sec_watchlist_filing_feeds_tech_spec_2026_06_28.md` exists.
- The spec status is `Draft`.
- The spec contains `sources.rss.sec.watchlist_company_filings`.
- The spec contains `default false`.
- The spec contains `MIMIR_SEC_USER_AGENT`.
- The spec contains `company_tickers.json`.
- The spec contains `no HTML RSS link crawling`.
- The spec contains `no vendor URL pattern inference`.
- `docs/decisions/tech-spec/README.md` links the new spec.
- `docs/architecture/improvement-catalog.md` mentions `R1o-SEC-WATCHLIST-FILING-FEEDS`.
- The catalog's deferred RSS item still mentions `generic live discovery`, `SEC 외 provider discovery`, `HTML RSS link crawling`, and `vendor URL pattern inference`.
- The catalog no longer says `watchlist 기반 SEC feed 자동 생성은 여전히 deferred item이다`.

- [ ] **Step 2: Run RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_rss_provider_policy_recheck_promotes_only_sec_watchlist_spec -q
```

Expected: FAIL because the R1o spec does not exist yet.

## Task 3: GREEN Docs/Spec Update

**Files:**
- Create: `docs/decisions/tech-spec/sources/R1o-SEC-WATCHLIST-FILING-FEEDS_sec_watchlist_filing_feeds_tech_spec_2026_06_28.md`
- Modify: `docs/decisions/tech-spec/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `BACKLOG.md`
- Modify: `DECISIONS.md`
- Modify: `WORKLOG.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

- [ ] **Step 1: Write the draft tech spec**

Create a Draft spec for `R1o-SEC-WATCHLIST-FILING-FEEDS`.

Required product boundary:

- Add only an opt-in draft setting such as `sources.rss.sec.watchlist_company_filings`.
- Default is `false`; no new feed generation by default.
- SEC-only. Reuse `sources.rss.sec.company_filings`, local `ticker_cik_map_path`, and opt-in `ticker_cik_map_refresh`.
- Use watchlist `us` symbols only.
- Keep request count explicit and bounded by generated feeds.
- Require `MIMIR_SEC_USER_AGENT` for SEC fair-access.
- Keep generic provider discovery deferred: no SEC-external provider discovery, no HTML RSS link crawling, and no vendor URL pattern inference.

- [ ] **Step 2: Link and summarize the draft spec**

Update the tech spec README and improvement catalog. The catalog should say R1o is a Draft tech spec, not implemented code.

- [ ] **Step 3: Update root state docs**

Move `RSS-PROVIDER-POLICY-RECHECK` to `BACKLOG.md` Done, record the decision in `DECISIONS.md`, and add work evidence to `WORKLOG.md`.

- [ ] **Step 4: Update README counts**

After collect-only shows the new count, update all three README badges and test table rows.

## Task 4: Verify, Review, Commit

**Files:**
- All files touched in Tasks 2-3.

- [ ] **Step 1: Run focused guard**

```bash
uv run pytest tests/test_readme_docs.py::test_rss_provider_policy_recheck_promotes_only_sec_watchlist_spec -q
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
git add tests/test_readme_docs.py \
  docs/decisions/tech-spec/README.md \
  docs/decisions/tech-spec/sources/R1o-SEC-WATCHLIST-FILING-FEEDS_sec_watchlist_filing_feeds_tech_spec_2026_06_28.md \
  docs/architecture/improvement-catalog.md \
  docs/IMPROVEMENTS.md \
  BACKLOG.md DECISIONS.md WORKLOG.md \
  README.md README.ko.md README.zh.md
git commit -m "docs(sources): promote sec watchlist rss spec"
```

Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.

