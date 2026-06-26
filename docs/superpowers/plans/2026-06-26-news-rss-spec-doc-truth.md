# News RSS Spec Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the completed news captured-window, symbol-tagged RSS, and RSS feed catalog design specs with current implementation truth and prevent stale completion metadata from returning.

**Architecture:** Add one focused docs health guard in `tests/test_readme_docs.py` for the three connected news/RSS design specs, then update only those specs and README test counts if the new guard changes the collected pytest count. Runtime code remains untouched because `mimir/storage/reader.py`, `mimir/analysis/signals/*`, `mimir/sources/rss.py`, `mimir/sources/rss_catalog.py`, `mimir/sources/config.py`, and `mimir/core/builder.py` already implement the relevant behavior.

**Tech Stack:** Python 3.12, pytest, markdown docs, existing Mimir docs health tests.

## Global Constraints

- Do not edit runtime code for this slice unless the RED docs guard proves a current implementation claim is false.
- Do not stage, edit, delete, or commit the unrelated untracked `uv.lock`.
- Do not stage or commit `.superpowers/` worker or reviewer reports.
- Do not stage or commit unrelated untracked continuation files unless the controller explicitly scopes them into a separate commit.
- Keep changes scoped to `tests/test_readme_docs.py`, the three target design specs, and README EN/KO/ZH test counts if collection increases.
- Use TDD: add the failing docs health guard first, run it and observe the expected failure, then update docs.
- Preserve design-history context: the specs may explain what each increment did at the time, but the completed status lines must not claim stale fixed test counts.
- Completed design specs must not leave unchecked `- [ ]` acceptance criteria in their acceptance sections.
- Current verification wording for completed specs must point to README test badges and docs health guards, not hard-coded historical suite sizes.
- The RSS feed catalog spec must distinguish the original R1e static catalog from later implemented SEC structured catalog, SEC company filing feed generation, ticker/CIK mapping, and off-by-default mapping refresh.
- External actions are read-only by default; do not push or publish.

---

## File Structure

- Modify: `tests/test_readme_docs.py`
  - Add path constants for the R1b, R1d, and R1e design specs.
  - Add one docs health guard that blocks stale fixed test-count status lines, unchecked acceptance criteria, stale RSS catalog completion wording, and missing current implementation terms.
- Modify: `docs/superpowers/specs/2026-06-16-news-captured-window-design.md`
  - Replace the stale `377 테스트` status phrase with current docs-health wording.
  - Update the old "full scan every call" design text to current in-memory captured-date index truth.
- Modify: `docs/superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md`
  - Replace the stale `415 테스트` status phrase with current docs-health wording.
  - Document the current code terms for feed symbol parsing, `RawRecord.symbol`, symbol idempotency keys, and shared matcher behavior.
- Modify: `docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md`
  - Replace the stale `438 tests` status phrase with current docs-health wording.
  - Document current RSS resolver truth: `RSS_CATALOG`, `resolve_rss_catalogs()`, `resolve_rss_feeds()`, SEC structured catalog ids, SEC company filing feed generation, `ticker_cik_map_refresh`, resolver no-network boundary, and feed ordering.
- Modify if collected count changes: `README.md`, `README.ko.md`, `README.zh.md`
  - Update tests badge and test table count to match `pytest --collect-only`.

## Current Implementation Evidence

- `mimir/storage/reader.py` implements `DataReader.read_captured_window()` over `_captured_date_index(dataset)`, which builds an in-memory `captured_at.date()` index with `JsonlStore.read_all(dataset)`, caches by `JsonlStore.revision`, invalidates after append/replace, and logs `captured-date index rebuilt`.
- `mimir/analysis/signals/news_volume.py` uses `reader.read_captured_window(Dataset.NEWS, ...)` for both today and the 7-day baseline.
- `mimir/analysis/signals/llm_sentiment.py` uses `reader.read_captured_window(Dataset.NEWS, ...)` before classifying headlines.
- `mimir/analysis/signals/news_matching.py` implements `NewsMentionMatcher.mentions()` with `if record.symbol == symbol: return True` before text/alias matching.
- `mimir/sources/rss.py` defines `RssFeed.symbol`, strips nonblank symbols, rejects blank symbols, writes symbol-tagged records with `RawRecord.symbol`, keeps `rss:{link}` for symbol-less feeds, and uses `rss:{symbol}:{link}` for symbol-tagged feeds.
- `mimir/sources/config.py` parses `sources.rss.catalogs`, `sources.rss.sec.company_filings`, `sources.rss.sec.ticker_cik_map_path`, and `sources.rss.sec.ticker_cik_map_refresh`.
- `mimir/sources/rss_catalog.py` defines `RssCatalogSelection`, `RSS_CATALOG`, `resolve_rss_catalogs()`, `resolve_rss_feeds()`, SEC structured catalog ids, SEC company filing feed generation, local SEC ticker/CIK map loading, and duplicate `(url, symbol)` validation.
- `mimir/core/builder.py` calls `resolve_rss_feeds(config.rss_catalogs, config.rss_feeds, config.rss_sec_company_filings, _load_configured_sec_ticker_cik_map(config))`, sends `MIMIR_SEC_USER_AGENT` into `RssSource`, and runs `ticker_cik_map_refresh` as an off-by-default build-prep step outside the resolver.
- Tests cover these facts in `tests/analysis/test_reader.py`, `tests/analysis/signals/test_signals.py`, `tests/analysis/signals/test_llm_sentiment.py`, `tests/sources/test_rss.py`, `tests/sources/test_rss_catalog.py`, `tests/sources/test_config.py`, and `tests/core/test_builder.py`.

---

### Task 1: News/RSS Design Spec Truth Guard

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-06-16-news-captured-window-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md`
- Modify: `docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md`
- Modify if needed: `README.md`
- Modify if needed: `README.ko.md`
- Modify if needed: `README.zh.md`

**Interfaces:**
- Consumes: existing `_status_line(text: str) -> str` helper.
- Consumes: existing `_markdown_section(text: str, heading: str) -> str` helper.
- Produces: `test_news_rss_design_specs_match_current_completion_state()`.
- Produces: status lines in the three target specs that use `최신 검증은 README 테스트 배지와 docs health guard가 추적`.

- [ ] **Step 1: Add spec path constants**

In `tests/test_readme_docs.py`, add these constants near the existing design-spec path constants:

```python
NEWS_CAPTURED_WINDOW_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-news-captured-window-design.md"
)
SYMBOL_TAGGED_RSS_FEEDS_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md"
)
RSS_FEED_CATALOG_SPEC = Path(
    "docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md"
)
```

- [ ] **Step 2: Write the failing docs health guard**

Add this test after `test_storage_backfill_design_specs_match_current_completion_state()`:

```python
def test_news_rss_design_specs_match_current_completion_state() -> None:
    specs = {
        NEWS_CAPTURED_WINDOW_SPEC: (
            "## 7. 수용 기준",
            ("377 테스트", "coverage gate 클린"),
        ),
        SYMBOL_TAGGED_RSS_FEEDS_SPEC: (
            "## 7. 수용 기준",
            ("415 테스트", "coverage gate 클린"),
        ),
        RSS_FEED_CATALOG_SPEC: (
            "## 13. 수용 기준",
            ("438 tests", "coverage gate 통과"),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"

    captured = texts[NEWS_CAPTURED_WINDOW_SPEC]
    assert "`DataReader.read_captured_window()`" in captured
    assert "`captured_at.date()`" in captured
    assert "`_captured_date_index()`" in captured
    assert "`JsonlStore.read_all(dataset)`" in captured
    assert "`JsonlStore.revision`" in captured
    assert "captured-date index rebuilt" in captured
    assert "`NewsVolumeSignal`" in captured
    assert "`LlmSentimentSignal`" in captured
    assert "저장 파티션" in captured
    assert "on-disk index" in captured

    symbol_tagged = texts[SYMBOL_TAGGED_RSS_FEEDS_SPEC]
    assert "`sources.rss.feeds[].symbol`" in symbol_tagged
    assert "`RssFeed.symbol`" in symbol_tagged
    assert "`RawRecord.symbol`" in symbol_tagged
    assert "`rss:{link}`" in symbol_tagged
    assert "`rss:{symbol}:{link}`" in symbol_tagged
    assert "`NewsMentionMatcher`" in symbol_tagged
    assert "`record.symbol == symbol`" in symbol_tagged
    assert "`NewsVolumeSignal`" in symbol_tagged
    assert "`LlmSentimentSignal`" in symbol_tagged

    catalog = texts[RSS_FEED_CATALOG_SPEC]
    assert "`RssCatalogSelection`" in catalog
    assert "`RSS_CATALOG`" in catalog
    assert "`resolve_rss_catalogs()`" in catalog
    assert "`resolve_rss_feeds()`" in catalog
    assert "`sec_press_releases`" in catalog
    assert "`sec_structured_usgaap`" in catalog
    assert "`sec_structured_risk_return`" in catalog
    assert "`sec_structured_inline_xbrl`" in catalog
    assert "`sec_structured_all_xbrl`" in catalog
    assert "`sources.rss.sec.company_filings`" in catalog
    assert "`ticker_cik_map_refresh`" in catalog
    assert "`MIMIR_SEC_USER_AGENT`" in catalog
    assert "`catalogs`, `sec.company_filings`, `feeds`" in catalog
    assert "네트워크를 호출하지 않는다" in catalog
    assert "HTML scraping" in catalog
    assert "vendor URL" in catalog
```

- [ ] **Step 3: Run the new test and verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_news_rss_design_specs_match_current_completion_state -q
```

Expected: FAIL because the three selected specs still carry stale fixed test-count status phrases, R1b still describes a plain full scan instead of the current cached captured-date index, and R1e does not yet describe later implemented SEC RSS resolver truth.

- [ ] **Step 4: Update R1b news captured-window status and current-state wording**

In `docs/superpowers/specs/2026-06-16-news-captured-window-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`DataReader.read_captured_window` + in-memory captured-date index + 뉴스 시그널 captured window). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

Replace section `### 4.2 파티션 프루닝은 의도적으로 쓰지 않는다` with:

```markdown
### 4.2 현재 구현은 in-memory captured-date index를 쓴다

저장 파티션은 여전히 `rec.ts.date()` 기준이다. `captured_at` 기준으로 날짜를 자르면서 `read_window(since, until)`을 쓰면, 발행일이 윈도우 밖인 레코드를 읽기 전에 놓친다.

현재 구현은 `DataReader.read_captured_window()`가 `_captured_date_index()`를 통해 dataset별 in-memory index를 만든다. 첫 호출은 `JsonlStore.read_all(dataset)`으로 전체 dataset을 읽고 `captured_at.date()`별 bucket을 만든다. 같은 `DataReader`의 다음 captured window 호출은 이 index를 재사용한다.

Cache key는 `JsonlStore.revision`이다. 같은 store 객체에 record가 append되거나 `replace_partition()`이 실행되면 revision이 바뀌고, 다음 `read_captured_window()` 호출이 index를 다시 만든다. Index rebuild 때는 `mimir.storage.reader` DEBUG log에 `captured-date index rebuilt`와 함께 record 수, day 수, elapsed time을 남긴다.

이 index는 on-disk index가 아니다. 저장 구조, JSONL partition, `idempotency_key`, migration 경로는 바꾸지 않는다. 큰 NEWS 데이터에서 scan 비용이 의미 있게 보이면 별도 persistent index 설계로 넘어간다.
```

In section `### 4.3 뉴스 시그널만 새 API를 사용한다`, add this paragraph after the code examples:

```markdown
현재 코드에서 `NewsVolumeSignal`은 today와 baseline 모두 `DataReader.read_captured_window()`를 호출한다. `LlmSentimentSignal`도 classifier 호출 전에 같은 captured window로 mention 후보를 고른다.
```

In `## 8. 남는 한계`, replace the first sentence with:

```markdown
`read_captured_window()`는 captured-date on-disk index를 만들지 않는다. 현재는 첫 captured window 호출에서 in-memory index를 만들고 `JsonlStore.revision`이 바뀔 때까지 재사용한다.
```

- [ ] **Step 5: Update R1d symbol-tagged RSS status and current-state wording**

In `docs/superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`RssFeed.symbol` + record-symbol 뉴스 매칭). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

Add this paragraph after section `### 4.1 RSS feed 모델`:

```markdown
현재 구현에서 `RssFeed.symbol`은 `mimir/sources/rss.py`의 pydantic model 필드다. Validator는 공백을 제거하고 빈 문자열이면 `ValueError("RSS feed symbol must not be blank")`로 실패한다. `extra="forbid"` 때문에 `symbl` 같은 오타 field도 조용히 무시되지 않는다.
```

Add this paragraph after section `### 4.2 RawRecord symbol과 idempotency key`:

```markdown
현재 `RssSource.fetch()`는 symbol-tagged feed에서 `RawRecord.symbol`을 feed symbol로 채운다. Symbol 없는 feed는 기존 `rss:{link}` key를 유지하고, symbol 있는 feed는 `rss:{symbol}:{link}` key를 쓴다. Payload schema에는 symbol을 추가하지 않고 record envelope symbol만 사용한다.
```

Add this paragraph after section `### 4.3 NewsMentionMatcher 우선순위`:

```markdown
현재 `NewsMentionMatcher`는 코드상 `record.symbol == symbol`을 먼저 확인한 뒤 제목·요약의 symbol/alias term을 검사한다. `NewsVolumeSignal`과 `LlmSentimentSignal`은 같은 matcher를 사용하므로 symbol-tagged RSS feed는 무료 뉴스량 시그널과 opt-in LLM 감성 시그널 모두에 적용된다.
```

- [ ] **Step 6: Update R1e RSS feed catalog status and current-state wording**

In `docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`sources.rss.catalogs` + RSS resolver chain). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

Replace the scope line with:

```markdown
> **범위**: `sources.rss.catalogs` 정적 catalog, `sources.rss.sec.company_filings` SEC Atom URL 조립, local resolver, off-by-default SEC mapping refresh prep. Live endpoint discovery, HTML scraping, vendor URL 추측은 제외한다.
```

In section `## 7. Resolver 설계`, keep the original `resolve_rss_catalogs()` description and add this paragraph after its behavior list:

```markdown
현재 구현에는 상위 resolver인 `resolve_rss_feeds()`도 있다. 이 함수는 `resolve_rss_catalogs(selections)`, `resolve_sec_company_filing_feeds(sec.company_filings, sec_ticker_cik_map)`, manual `sources.rss.feeds`를 합친 뒤 같은 `(url, symbol)` 중복을 검증한다. Catalog-only resolver는 여전히 순수 함수이고, 통합 resolver도 네트워크를 호출하지 않는다.
```

In section `## 8. Config와 Builder 흐름`, replace the ordered list with:

```markdown
`build_sources()`의 RSS factory는 다음 순서로 feed를 만든다.

1. `resolve_rss_catalogs(cfg.rss_catalogs)`
2. `resolve_sec_company_filing_feeds(cfg.rss_sec_company_filings, sec_ticker_cik_map)`
3. `cfg.rss_feeds or []`
4. 세 list를 합친 값이 비어 있으면 `None`을 넘겨 기존 `DEFAULT_FEEDS`를 유지한다.
5. 하나라도 있으면 합친 list를 `RssSource(feeds=..., user_agent=settings.sec_user_agent)`에 넘긴다.

즉 현재 ordering은 `catalogs`, `sec.company_filings`, `feeds` 순서다. `MIMIR_SEC_USER_AGENT`는 build된 RSS source의 모든 RSS HTTP 요청에 `User-Agent` header로 전달된다.
```

Add this paragraph after that list:

```markdown
`ticker_cik_map_refresh`는 resolver 안에서 실행되지 않는다. 설정에서 `sources.rss.sec.ticker_cik_map_refresh.enabled: true`와 `sources.rss.sec.ticker_cik_map_path`를 함께 둔 경우, `build_sources()`가 resolver 호출 전에 TTL/ETag 기반 best-effort refresh를 수행한다. 기본값은 disabled라서 표준 경로의 mapping download 요청은 0회다.
```

Replace section `## 9. 초기 Catalog 범위` with:

```markdown
## 9. Catalog 범위와 후속 SEC RSS 증분

R1e 당시 초기 catalog는 SEC 공식 RSS 문서와 SEC 공식 newsroom page에서 확인 가능하고, 직접 HEAD 요청으로 RSS 응답이 확인된 feed만 포함했다.

| id | feed URL | publisher | market | 근거 |
|---|---|---|---|---|
| `sec_press_releases` | `https://www.sec.gov/news/pressreleases.rss` | `SEC` | `US` | SEC RSS Feeds page와 Press Releases page |

현재 `RSS_CATALOG`에는 후속 R1g-SEC-STRUCTURED에서 추가된 SEC structured disclosure catalog도 포함된다.

| id | 범위 |
|---|---|
| `sec_structured_usgaap` | US GAAP/IFRS tagged financial statement filings |
| `sec_structured_risk_return` | mutual fund risk/return tagged filings |
| `sec_structured_inline_xbrl` | Inline XBRL financial statement filings |
| `sec_structured_all_xbrl` | all XBRL filings submitted to the SEC |

이 네 feed는 broad SEC/XBRL feed다. 특정 watchlist symbol 전용 feed가 아니므로 `symbol`을 붙이지 않는다.

SEC Company Search Atom feed 조립은 후속 R1f/R1h/R1i 흐름으로 구현되어 현재 `sources.rss.sec.company_filings` 아래에 있다. 사용자는 CIK 또는 ticker token을 명시하고, 필요하면 `ticker_cik_map_path`로 로컬 SEC mapping file을 읽어 ticker를 10자리 CIK로 바꿀 수 있다. Generic live discovery, watchlist 기반 feed 자동 생성, SEC 외 provider discovery, HTML scraping, vendor URL pattern inference는 여전히 제외한다.
```

- [ ] **Step 7: Update README counts if collection changed**

Run:

```bash
uv run pytest --collect-only -q
```

Expected: one more collected test than before this task. If the output shows `635 tests collected` or `collected 635 items`, update all three README files:

- `README.md`
- `README.ko.md`
- `README.zh.md`

Replace both the tests badge count and the tests table count from `634` to the collected count. Do not change the coverage percentage unless the repository's existing badge policy requires it and a coverage run proves a new value.

- [ ] **Step 8: Run focused GREEN checks**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_news_rss_design_specs_match_current_completion_state -q
uv run pytest tests/test_readme_docs.py::test_readme_test_badges_match_collected_pytest_count -q
```

Expected: both pass.

- [ ] **Step 9: Run docs test file**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Expected: all docs health tests pass.

- [ ] **Step 10: Commit exact files**

Before staging, verify the working tree:

```bash
git status --short
```

Stage only the files in this task:

```bash
git add tests/test_readme_docs.py \
  docs/superpowers/specs/2026-06-16-news-captured-window-design.md \
  docs/superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md \
  docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md \
  README.md README.ko.md README.zh.md
```

Do not stage `uv.lock`, `.superpowers/`, `CLAUDE.md`, or `docs/superpowers/handoffs/`.

Commit:

```bash
git commit -m "test(docs): guard news rss spec truth"
```

Report the focused RED/GREEN evidence, collected test count, and commit SHA in `.superpowers/sdd/news-rss-spec-doc-truth-task-1-report.md`.
