# Generic RSS Discovery Boundary Recheck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recheck the remaining generic provider RSS discovery boundary after R1o and either keep it deferred with evidence or promote one narrow official-source slice.

**Architecture:** Prefer no production code unless current official-source evidence proves a bounded, legal, non-crawling slice. Keep the existing RSS architecture: static catalog ids, explicit manual feeds, SEC company filing helpers, and no resolver-time network discovery.

**Tech Stack:** Python 3.14, existing RSS config/resolver docs, pytest docs guards, official provider docs/ToS pages, ruff, mypy strict.

---

## File Map

- Modify: `PLAN.md` — mark the active loop as `GENERIC-RSS-DISCOVERY-BOUNDARY-RECHECK`.
- Inspect: `BACKLOG.md`, `DECISIONS.md`, `WORKLOG.md`.
- Inspect: `docs/IMPROVEMENTS.md`.
- Inspect: `docs/architecture/improvement-catalog.md`.
- Inspect: `docs/reference/config/sources.md`.
- Inspect: `docs/architecture/extensibility/README.md`.
- Inspect: `mimir/sources/rss_catalog.py`, `mimir/sources/rss.py`, `mimir/core/builder.py`.
- Modify if deferred: `tests/test_readme_docs.py`, `docs/IMPROVEMENTS.md`, `docs/architecture/improvement-catalog.md`, `BACKLOG.md`, `DECISIONS.md`, `WORKLOG.md`, and README EN/KO/ZH counts if a guard is added.
- Modify if promoted to a spec only: `docs/decisions/tech-spec/README.md`, a new file under `docs/decisions/tech-spec/sources/`, `tests/test_readme_docs.py`, `BACKLOG.md`, `DECISIONS.md`, `WORKLOG.md`, and README EN/KO/ZH counts if a guard is added.
- Modify if promoted to code: only after a tech-spec-quality decision exists, use the relevant RSS config/resolver/test files named by that spec.

## Task 1: Plan Commit

**Files:**
- Create: `docs/superpowers/plans/2026-06-28-generic-rss-discovery-boundary-recheck.md`
- Modify: `PLAN.md`

- [ ] **Step 1: Update `PLAN.md`**

Expected current loop block:

```markdown
## Current Loop

`GENERIC-RSS-DISCOVERY-BOUNDARY-RECHECK`

- Plan: `docs/superpowers/plans/2026-06-28-generic-rss-discovery-boundary-recheck.md`
- Backlog: `BACKLOG.md`
- Work log: `WORKLOG.md`
- Decisions: `DECISIONS.md`
```

- [ ] **Step 2: Run diff check**

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 3: Commit the plan**

```bash
git add PLAN.md docs/superpowers/plans/2026-06-28-generic-rss-discovery-boundary-recheck.md
git commit -m "docs(sources): plan generic rss discovery recheck"
```

## Task 2: Recheck Current Boundaries

**Files:**
- Read: `docs/IMPROVEMENTS.md`
- Read: `docs/architecture/improvement-catalog.md`
- Read: `docs/reference/config/sources.md`
- Read: `docs/architecture/extensibility/README.md`
- Read: `mimir/sources/rss_catalog.py`
- Read: `mimir/sources/rss.py`
- Read: `mimir/core/builder.py`
- Read: `tests/test_readme_docs.py`

- [ ] **Step 1: Verify current implemented RSS paths**

Expected current evidence:

- `sources.rss.catalogs` uses static built-in RSS catalog ids.
- `sources.rss.sec.company_filings` builds explicit SEC Company Search feeds.
- `sources.rss.sec.watchlist_company_filings` generates only SEC Company Search feeds from `watchlist.us`.
- `sources.rss.feeds` accepts explicit operator-owned URLs.
- Resolver code does not crawl HTML, guess vendor URL patterns, or perform generic provider discovery.

- [ ] **Step 2: Confirm remaining deferred scope**

Use `rg`:

```bash
rg -n "generic live discovery|SEC 외 provider discovery|HTML RSS link crawling|vendor URL pattern inference|Automatic/live feed discovery" docs README.md tests
```

Expected: remaining scope is limited to generic provider discovery, SEC-external providers, HTML RSS link crawling, and vendor URL pattern inference.

## Task 3: Official Source and Policy Research

**Files:**
- Modify later: `DECISIONS.md`
- Modify later: `WORKLOG.md`

- [ ] **Step 1: Recheck official SEC boundary**

Use official SEC pages only:

- `https://www.sec.gov/about/rss-feeds`
- `https://www.sec.gov/about/developer-resources`
- `https://www.sec.gov/about/webmaster-frequently-asked-questions`
- `https://www.sec.gov/files/company_tickers.json`

Expected: SEC official-source slices already covered by R1f/R1g/R1h/R1i-R1n/R1o unless a new static official SEC RSS URL list is documented.

- [ ] **Step 2: Recheck existing non-SEC source providers**

Use official/provider-owned docs or terms pages for existing Mimir source families only:

- Stooq
- FRED
- Finnhub
- DART/OpenDART
- ECOS
- pykrx/KRX-related docs
- Naver/RSS references already documented in repo

Record source URLs and dates in `WORKLOG.md`. Do not rely on blog posts or scraped examples.

- [ ] **Step 3: Decide whether any one narrow official-source slice exists**

Promote only if all are true:

- The provider documents RSS/feed URLs or an official feed list.
- The feed is legal to fetch with Mimir's public-data/free-source constraints.
- The feed can be represented as a static catalog id or explicit config block.
- The resolver can remain no-network/no-crawling.
- No new dependency is needed.

If any condition fails, keep generic discovery deferred.

## Task 4A: If Deferred, Add a Docs Guard

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `BACKLOG.md`
- Modify: `DECISIONS.md`
- Modify: `WORKLOG.md`
- Modify: `README.md`, `README.ko.md`, `README.zh.md` if test count changes

- [ ] **Step 1: Add a focused docs guard**

Add one test in `tests/test_readme_docs.py` that asserts current docs keep:

```python
def test_generic_rss_discovery_recheck_keeps_policy_boundary_deferred() -> None:
    improvements = Path("docs/IMPROVEMENTS.md").read_text(encoding="utf-8")
    catalog = IMPROVEMENT_CATALOG.read_text(encoding="utf-8")
    config_ref = Path("docs/reference/config/sources.md").read_text(encoding="utf-8")
    decisions = Path("DECISIONS.md").read_text(encoding="utf-8")

    for phrase in (
        "generic live discovery",
        "SEC 외 provider discovery",
        "HTML RSS link crawling",
        "vendor URL pattern inference",
    ):
        assert phrase in improvements
        assert phrase in catalog
        assert phrase in decisions

    assert "Resolver는 코드 안의 정적 catalog만 읽는다" in config_ref
    assert "Catalog를 해석하는 동안 네트워크를 호출하지 않으며" in config_ref
```

- [ ] **Step 2: Run the guard RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_generic_rss_discovery_recheck_keeps_policy_boundary_deferred -q
```

Expected: FAIL until `DECISIONS.md` records this recheck.

- [ ] **Step 3: Update docs/state**

Add a `GENERIC-RSS-DISCOVERY-BOUNDARY-RECHECK` decision entry that says generic discovery remains deferred, unless Task 3 found a narrow official-source slice.

Update `BACKLOG.md` by moving this loop to Done and queueing the next evidence-backed item from `docs/IMPROVEMENTS.md`.

## Task 4B: If One Official-Source Slice Is Promoted

**Files:**
- Create: `docs/decisions/tech-spec/sources/<new-id>_<slug>_tech_spec_2026_06_28.md`
- Modify: `docs/decisions/tech-spec/README.md`
- Modify: `tests/test_readme_docs.py`
- Modify: `BACKLOG.md`
- Modify: `DECISIONS.md`
- Modify: `WORKLOG.md`
- Modify: README EN/KO/ZH counts if a guard is added

- [ ] **Step 1: Write a Draft tech spec, not production code**

Use this status line:

```markdown
**상태**: Draft
```

The spec must state:

- official source URL evidence,
- no resolver-time network discovery,
- no HTML crawling,
- no vendor URL inference,
- exact config surface,
- exact tests required before implementation.

- [ ] **Step 2: Add a docs guard**

Add one guard in `tests/test_readme_docs.py` that asserts the new Draft spec exists, is indexed, includes official source URLs, and keeps generic discovery deferred.

- [ ] **Step 3: Queue the implementation slice**

Update `BACKLOG.md` so the new implementation slice is the next queue item.

## Task 5: Verify, Review, Commit

**Files:**
- All files touched by Task 4A or Task 4B.

- [ ] **Step 1: Run focused tests**

Run the new focused docs guard:

```bash
uv run pytest tests/test_readme_docs.py::<new_test_name> -q
```

Expected: 1 passed.

- [ ] **Step 2: Run full gates**

```bash
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q | tail -1
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

- [ ] **Step 3: Review**

Use spec and quality reviewers. Fix Critical/Important issues before committing.

- [ ] **Step 4: Commit exact files**

Use exact staging. Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `uv.lock`.

Suggested deferred commit:

```bash
git add tests/test_readme_docs.py docs/IMPROVEMENTS.md docs/architecture/improvement-catalog.md BACKLOG.md DECISIONS.md WORKLOG.md README.md README.ko.md README.zh.md
git commit -m "docs(sources): keep generic rss discovery deferred"
```

Suggested spec-promotion commit:

```bash
git add tests/test_readme_docs.py docs/decisions/tech-spec/README.md docs/decisions/tech-spec/sources/<new-id>_<slug>_tech_spec_2026_06_28.md BACKLOG.md DECISIONS.md WORKLOG.md README.md README.ko.md README.zh.md
git commit -m "docs(sources): plan official rss source slice"
```

## Self-Review

- Spec coverage: Tasks cover current boundary inspection, official/provider-owned evidence gathering, defer-vs-promote decision, docs guard, verification, review, and exact commit.
- Placeholder scan: No `TBD`, `TODO`, or open implementation placeholders are used. Conditional paths are explicit and bounded.
- Type consistency: No new runtime type names are introduced in the plan. Existing names match current code: `RssFeed`, `RssSource`, `RSS_CATALOG`, `resolve_rss_feeds()`, and `build_sources()`.
