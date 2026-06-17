# SEC RSS Ticker Input Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `sources.rss.sec.company_filings` accept `ticker` as an alternative to `cik` without adding resolver-time network calls or watchlist-wide feed generation.

**Architecture:** Keep SEC company filing expansion in `mimir/sources/rss_catalog.py`. `SecCompanyFilingFeed` validates exactly one identifier (`cik` or `ticker`) and `_sec_company_filing_url()` writes that identifier into the existing SEC Company Search Atom URL. Builder and `RssSource` fetch behavior remain unchanged.

**Tech Stack:** Python 3.14, pydantic v2, pytest, ruff, mypy, markdown docs.

## Global Constraints

- Do not fetch `company_tickers.json`, `ticker.txt`, or any SEC mapping file in resolver/build/config parsing.
- Do not add a local full SEC ticker map snapshot.
- Do not add watchlist-wide automatic SEC RSS feed generation.
- Preserve existing CIK URL behavior.
- Preserve feed order: catalog, SEC company filings, manual feeds.
- Preserve duplicate detection by `(url, symbol)`.
- Do not stage or commit unrelated untracked `uv.lock`.

---

## File Map

| File | Responsibility |
|---|---|
| `tests/sources/test_rss_catalog.py` | Contract tests for ticker URL generation, validation, duplicate behavior |
| `tests/sources/test_config.py` | Config parser tests for ticker input |
| `tests/core/test_builder.py` | Builder integration and `User-Agent`/ordering regression |
| `mimir/sources/rss_catalog.py` | `SecCompanyFilingFeed` model and SEC Atom URL assembly |
| `config/sources.yaml` | Commented operator example |
| `docs/reference/config/sources.md` | User-facing config reference |
| `docs/architecture/extensibility/README.md` | Architecture boundary |
| `docs/architecture/improvement-catalog.md` | R1h tracking |
| `docs/IMPROVEMENTS.md` | Follow-up backlog wording |
| `docs/superpowers/specs/2026-06-18-sec-rss-ticker-input-design.md` | Acceptance checklist |

---

### Task 1: Add Failing Tests

- [x] Add `SecCompanyFilingFeed(ticker=" aapl ", symbol="AAPL")` resolver test.
- [x] Add ticker + forms/count/owner URL encoding test.
- [x] Add validation tests for both identifiers, neither identifier, blank ticker, invalid ticker token.
- [x] Add duplicate manual/ticker-generated feed test.
- [x] Add config parser ticker test.
- [x] Add builder ticker integration test.
- [x] Run focused tests and confirm RED:

```bash
uv run pytest tests/sources/test_rss_catalog.py tests/sources/test_config.py tests/core/test_builder.py -q
```

Expected: FAIL because `ticker` is not yet supported and `cik` is still required.

### Task 2: Implement Ticker Input

- [x] Update `SecCompanyFilingFeed.cik` to optional.
- [x] Add optional `ticker` with strip/uppercase normalization and conservative token validation.
- [x] Add model-level exactly-one validation for `cik`/`ticker`.
- [x] Update `_sec_company_filing_url()` to choose the configured SEC identifier.
- [x] Run focused tests and confirm GREEN.

### Task 3: Update Docs

- [x] Update `config/sources.yaml` example.
- [x] Update `docs/reference/config/sources.md` with `ticker` field and no-network boundary.
- [x] Update `docs/architecture/extensibility/README.md`.
- [x] Update `docs/architecture/improvement-catalog.md` with R1h.
- [x] Update `docs/IMPROVEMENTS.md`.
- [x] Mark spec and plan acceptance criteria complete after verification.

### Task 4: Verify And Land

- [x] Run focused tests:

```bash
uv run pytest tests/sources/test_rss_catalog.py tests/sources/test_config.py tests/core/test_builder.py -q
```

- [x] Run full gates:

```bash
uv run ruff check .
uv run mypy mimir
uv run pytest -q
git diff --check
```

- [ ] Review `git diff`.
- [ ] Commit logical changes.
- [ ] Rebase/merge with latest `origin/main`.
- [ ] Fast-forward merge to `main`.
- [ ] Push `main`.
