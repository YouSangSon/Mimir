# SEC Structured RSS Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SEC structured disclosure RSS feeds as static `sources.rss.catalogs` ids without adding live discovery or resolver-time network calls.

**Architecture:** Extend the existing `RSS_CATALOG` table in `mimir/sources/rss_catalog.py`. Keep all parsing, ordering, copy, and duplicate behavior in the existing resolver functions. Update config and architecture docs so users understand these are broad SEC/XBRL feeds, not symbol-specific feeds.

**Tech Stack:** Python 3.14, pydantic, pytest, ruff, mypy, static markdown docs.

## Global Constraints

- Do not add HTML crawling, vendor URL guessing, ticker→CIK lookup, watchlist-wide feed generation, or resolver-time network calls.
- All new catalog feeds must use `publisher="SEC"`, `market="US"`, and no `symbol`.
- Preserve `resolve_rss_feeds()` order: catalog feeds, SEC company filing feeds, manual feeds.
- Preserve duplicate detection by `(url, symbol)`.
- README EN/KO/ZH are out of scope for this advanced setting.
- Do not stage or commit unrelated untracked `uv.lock`.

---

## File Map

| File | Responsibility |
|---|---|
| `tests/sources/test_rss_catalog.py` | Contract tests for new catalog ids, deep-copy behavior, and duplicate handling |
| `mimir/sources/rss_catalog.py` | Static catalog entries and source metadata |
| `config/sources.yaml` | Commented example ids for operators |
| `docs/reference/config/sources.md` | User-facing config reference for catalog ids and limitations |
| `docs/architecture/extensibility/README.md` | Architecture explanation for RSS extension paths |
| `docs/architecture/improvement-catalog.md` | Improvement tracker status |
| `docs/IMPROVEMENTS.md` | Follow-up backlog wording |
| `docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md` | Acceptance checklist updated after verification |

---

### Task 1: Add Failing Catalog Contract Tests

**Files:**
- Modify: `tests/sources/test_rss_catalog.py`

**Interfaces:**
- Consumes: `RssCatalogSelection`, `RssFeed`, `resolve_rss_catalogs`, `resolve_rss_feeds`
- Produces: failing tests that define the new catalog ids and duplicate behavior

- [ ] **Step 1: Add expected structured feed parametrization**

Append this helper data near the existing imports:

```python
STRUCTURED_FEEDS = [
    (
        "sec_structured_usgaap",
        "https://www.sec.gov/Archives/edgar/usgaap.rss.xml",
    ),
    (
        "sec_structured_risk_return",
        "https://www.sec.gov/Archives/edgar/xbrl-rr.rss.xml",
    ),
    (
        "sec_structured_inline_xbrl",
        "https://www.sec.gov/Archives/edgar/xbrl-inline.rss.xml",
    ),
    (
        "sec_structured_all_xbrl",
        "https://www.sec.gov/Archives/edgar/xbrlrss.all.xml",
    ),
]
```

- [ ] **Step 2: Add known-id tests**

Append these tests after `test_resolve_known_rss_catalog_returns_copy()`:

```python
@pytest.mark.parametrize(("catalog_id", "url"), STRUCTURED_FEEDS)
def test_resolve_sec_structured_rss_catalog_ids(catalog_id: str, url: str):
    feeds = resolve_rss_catalogs([RssCatalogSelection(id=catalog_id)])

    assert feeds == [
        RssFeed(
            url=url,
            publisher="SEC",
            market="US",
        )
    ]


@pytest.mark.parametrize(("catalog_id", "url"), STRUCTURED_FEEDS)
def test_resolve_sec_structured_rss_catalog_returns_copy(catalog_id: str, url: str):
    feeds = resolve_rss_catalogs([RssCatalogSelection(id=catalog_id)])
    feeds[0].publisher = "Mutated"

    resolved_again = resolve_rss_catalogs([RssCatalogSelection(id=catalog_id)])

    assert resolved_again == [
        RssFeed(
            url=url,
            publisher="SEC",
            market="US",
        )
    ]
```

- [ ] **Step 3: Add duplicate manual/catalog regression**

Append this test after `test_resolve_rss_feeds_rejects_duplicate_manual_and_catalog_feed()`:

```python
def test_resolve_rss_feeds_rejects_duplicate_manual_and_structured_catalog_feed():
    manual = RssFeed(
        url="https://www.sec.gov/Archives/edgar/xbrlrss.all.xml",
        publisher="SEC",
        market="US",
    )

    with pytest.raises(ValueError, match="duplicate RSS feed"):
        resolve_rss_feeds([RssCatalogSelection(id="sec_structured_all_xbrl")], [manual])
```

- [ ] **Step 4: Run tests to verify RED**

Run:

```bash
uv run pytest tests/sources/test_rss_catalog.py -q
```

Expected: FAIL with unknown RSS catalog id for the four new ids.

- [ ] **Step 5: Commit RED tests**

```bash
git add tests/sources/test_rss_catalog.py
git commit -m "test: cover sec structured rss catalog"
```

---

### Task 2: Add SEC Structured Catalog Entries

**Files:**
- Modify: `mimir/sources/rss_catalog.py`

**Interfaces:**
- Consumes: failing tests from Task 1
- Produces: four new `RSS_CATALOG` entries

- [ ] **Step 1: Add the four entries to `RSS_CATALOG`**

Insert these entries after `sec_press_releases`:

```python
    "sec_structured_usgaap": RssCatalogEntry(
        id="sec_structured_usgaap",
        feed=RssFeed(
            url="https://www.sec.gov/Archives/edgar/usgaap.rss.xml",
            publisher="SEC",
            market="US",
        ),
        description=(
            "SEC structured disclosure RSS feed for filings containing "
            "financial statements tagged with US GAAP or IFRS taxonomies."
        ),
        source_url="https://www.sec.gov/data-research/structured-data/structured-disclosure-rss-feeds",
        verified_on=date(2026, 6, 18),
    ),
    "sec_structured_risk_return": RssCatalogEntry(
        id="sec_structured_risk_return",
        feed=RssFeed(
            url="https://www.sec.gov/Archives/edgar/xbrl-rr.rss.xml",
            publisher="SEC",
            market="US",
        ),
        description=(
            "SEC structured disclosure RSS feed for mutual fund filings "
            "tagged with the US Mutual Fund Risk/Return taxonomy."
        ),
        source_url="https://www.sec.gov/data-research/structured-data/structured-disclosure-rss-feeds",
        verified_on=date(2026, 6, 18),
    ),
    "sec_structured_inline_xbrl": RssCatalogEntry(
        id="sec_structured_inline_xbrl",
        feed=RssFeed(
            url="https://www.sec.gov/Archives/edgar/xbrl-inline.rss.xml",
            publisher="SEC",
            market="US",
        ),
        description=(
            "SEC structured disclosure RSS feed for Inline XBRL filings "
            "containing financial statements tagged with US GAAP or IFRS taxonomies."
        ),
        source_url="https://www.sec.gov/data-research/structured-data/structured-disclosure-rss-feeds",
        verified_on=date(2026, 6, 18),
    ),
    "sec_structured_all_xbrl": RssCatalogEntry(
        id="sec_structured_all_xbrl",
        feed=RssFeed(
            url="https://www.sec.gov/Archives/edgar/xbrlrss.all.xml",
            publisher="SEC",
            market="US",
        ),
        description="SEC structured disclosure RSS feed for all XBRL filings submitted to the SEC.",
        source_url="https://www.sec.gov/data-research/structured-data/structured-disclosure-rss-feeds",
        verified_on=date(2026, 6, 18),
    ),
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
uv run pytest tests/sources/test_rss_catalog.py -q
```

Expected: PASS.

- [ ] **Step 3: Run style/type checks for touched code**

Run:

```bash
uv run ruff check mimir/sources/rss_catalog.py tests/sources/test_rss_catalog.py
uv run mypy mimir
```

Expected: both PASS.

- [ ] **Step 4: Commit implementation**

```bash
git add mimir/sources/rss_catalog.py
git commit -m "feat: add sec structured rss catalog"
```

---

### Task 3: Document the Catalog Expansion

**Files:**
- Modify: `config/sources.yaml`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md`

**Interfaces:**
- Consumes: new catalog ids from Task 2
- Produces: user-facing docs and updated acceptance checklist

- [ ] **Step 1: Update `config/sources.yaml` example**

Under `sources.rss.catalogs`, show the optional ids:

```yaml
#       - { id: "sec_structured_usgaap" }
#       - { id: "sec_structured_risk_return" }
#       - { id: "sec_structured_inline_xbrl" }
#       - { id: "sec_structured_all_xbrl" }
```

- [ ] **Step 2: Update config reference**

In `docs/reference/config/sources.md`, change the catalog id description from one current id to this table:

```markdown
| id | Feed |
|---|---|
| `sec_press_releases` | SEC press releases |
| `sec_structured_usgaap` | US GAAP/IFRS tagged financial statement filings |
| `sec_structured_risk_return` | mutual fund risk/return tagged filings |
| `sec_structured_inline_xbrl` | Inline XBRL financial statement filings |
| `sec_structured_all_xbrl` | all XBRL filings submitted to the SEC |
```

Also add one paragraph: these are broad SEC feeds, not symbol-specific feeds.

- [ ] **Step 3: Update architecture docs**

In `docs/architecture/extensibility/README.md`, add the four ids to the RSS catalog example and explain that structured disclosure feeds are static official feeds, while ticker→CIK lookup remains deferred.

- [ ] **Step 4: Update improvement catalog and backlog**

In `docs/architecture/improvement-catalog.md`:

1. Add `R1g-SEC-STRUCTURED` to the status line.
2. Add a summary row after `R1f-SEC`.
3. Add a section after `R1f-SEC` explaining the static catalog expansion.
4. Remove “SEC structured disclosure category 자동화” from the remaining generic discovery debt.
5. Keep SEC ticker→CIK, SEC-external providers, HTML RSS link crawling, and vendor URL pattern inference as deferred.

In `docs/IMPROVEMENTS.md`, mirror the remaining follow-up wording.

- [ ] **Step 5: Mark spec accepted**

In `docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md`:

1. Change status to `구현 완료`.
2. Check every acceptance checkbox.

- [ ] **Step 6: Run doc checks**

Run:

```bash
rg -n "R1g-SEC-STRUCTURED|sec_structured_usgaap|sec_structured_all_xbrl|ticker→CIK|generic discovery" config/sources.yaml docs/reference/config/sources.md docs/architecture/extensibility/README.md docs/architecture/improvement-catalog.md docs/IMPROVEMENTS.md docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md
git diff --check
```

Expected: `rg` finds all new ids and boundary wording. `git diff --check` has no output.

- [ ] **Step 7: Commit docs**

```bash
git add config/sources.yaml docs/reference/config/sources.md docs/architecture/extensibility/README.md docs/architecture/improvement-catalog.md docs/IMPROVEMENTS.md docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md
git commit -m "docs: document sec structured rss catalog"
```

---

### Task 4: Final Verification

**Files:**
- No new source changes unless verification finds a defect.

**Interfaces:**
- Consumes: Tasks 1-3
- Produces: verified merge-ready branch

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run pytest tests/sources/test_rss_catalog.py tests/sources/test_config.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full gates**

Run:

```bash
uv run ruff check .
uv run mypy mimir
uv run pytest -q
git diff --check
```

Expected: all PASS.

- [ ] **Step 3: Self-review the branch diff**

Run:

```bash
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
```

Expected: only planned files are changed.

- [ ] **Step 4: Prepare final review package**

Run:

```bash
/Users/yousang/.codex/superpowers/skills/subagent-driven-development/scripts/review-package origin/main HEAD
```

Expected: script prints a review package path.

---

## Self-Review

- Spec coverage: Tasks cover new catalog ids, duplicate handling, no new resolver path, docs, backlog status, and final verification.
- Placeholder scan: no banned placeholder phrases or unspecified test steps remain.
- Type consistency: all code references use existing `RssCatalogSelection`, `RssCatalogEntry`, `RssFeed`, `resolve_rss_catalogs`, and `resolve_rss_feeds`.
