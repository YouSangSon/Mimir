# Symbol-Tagged RSS Feeds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자가 `sources.rss.feeds[].symbol`로 종목별 RSS feed를 선언하면, RSS 수집과 뉴스 시그널이 그 feed를 해당 symbol의 뉴스로 안정적으로 해석한다.

**Architecture:** `RssFeed` 모델에 optional `symbol`을 추가한다. RSS source는 symbol-tagged record를 만들고, `NewsMentionMatcher`는 record envelope symbol을 텍스트 매칭보다 먼저 인정한다.

**Tech Stack:** Python 3.14, pydantic, pytest, responses, ruff, mypy.

---

### Task 1: Config And RSS Source Contract

**Files:**
- Modify: `mimir/sources/rss.py`
- Modify: `tests/sources/test_config.py`
- Modify: `tests/sources/test_rss.py`

- [x] **Step 1: Write failing config symbol test**

Add a test that parses:

```python
{"sources": {"rss": {"feeds": [
    {"url": "https://x/feed.rss", "publisher": "Example", "market": "US", "symbol": " AAPL "}
]}}}
```

Assert the parsed `RssFeed.symbol` is `"AAPL"`.

Run:

```bash
uv run pytest tests/sources/test_config.py::test_rss_feed_symbol_parses_from_config -q
```

Expected: FAIL because `RssFeed` does not expose symbol yet.

- [x] **Step 2: Write failing validation tests**

Add tests for blank symbol and typo fields:

```python
test_rss_feed_blank_symbol_raises_validation_error
test_rss_feed_typo_field_raises_validation_error
```

Run:

```bash
uv run pytest tests/sources/test_config.py::test_rss_feed_blank_symbol_raises_validation_error tests/sources/test_config.py::test_rss_feed_typo_field_raises_validation_error -q
```

Expected: FAIL until `RssFeed` validates `symbol` and forbids unknown fields.

- [x] **Step 3: Write failing RSS source symbol test**

Add `test_rss_parses_entries_with_feed_symbol`.

Assert:

- `rec.symbol == "AAPL"`
- `rec.idempotency_key == "rss:AAPL:https://example.test/news/1"`
- payload shape remains the existing `NewsPayload` shape.

Run:

```bash
uv run pytest tests/sources/test_rss.py::test_rss_parses_entries_with_feed_symbol -q
```

Expected: FAIL because RSS records still use `symbol=None` and URL-only key.

- [x] **Step 4: Implement `RssFeed.symbol` and RSS key policy**

Update `RssFeed`:

- Add `ConfigDict(extra="forbid")`.
- Add `symbol: str | None = None`.
- Add a field validator that strips non-empty symbols and rejects blank strings.

Update `RssSource.fetch()`:

- Use `symbol=feed.symbol`.
- Use `rss:{symbol}:{link}` when symbol is present.
- Keep `rss:{link}` for symbol-less feeds.

- [x] **Step 5: Run focused RSS/config tests**

```bash
uv run pytest tests/sources/test_config.py tests/sources/test_rss.py -q
```

Expected: PASS.

### Task 2: News Matcher And Signals

**Files:**
- Modify: `mimir/analysis/signals/news_matching.py`
- Modify: `tests/analysis/signals/test_signals.py`
- Modify: `tests/analysis/signals/test_llm_sentiment.py`

- [x] **Step 1: Write failing matcher test**

Add `test_news_mention_matcher_matches_record_symbol_before_text`.

Use a news record whose `symbol="AAPL"` but title and summary do not contain `AAPL`, `Apple`, or aliases. Assert `NewsMentionMatcher().mentions(record, "AAPL")` is true and another symbol is false.

Run:

```bash
uv run pytest tests/analysis/signals/test_signals.py::test_news_mention_matcher_matches_record_symbol_before_text -q
```

Expected: FAIL because matcher only checks text.

- [x] **Step 2: Write failing signal tests**

Add:

```python
test_news_volume_counts_symbol_tagged_feed_without_text_mention
test_llm_sentiment_matches_symbol_tagged_feed_without_text_mention
```

Run:

```bash
uv run pytest tests/analysis/signals/test_signals.py::test_news_volume_counts_symbol_tagged_feed_without_text_mention tests/analysis/signals/test_llm_sentiment.py::test_llm_sentiment_matches_symbol_tagged_feed_without_text_mention -q
```

Expected: FAIL because both signals depend on the matcher.

- [x] **Step 3: Implement record-symbol matching**

Update `NewsMentionMatcher.mentions()`:

```python
if record.symbol == symbol:
    return True
```

Keep existing symbol/alias text matching unchanged.

- [x] **Step 4: Run focused matcher/signal tests**

```bash
uv run pytest tests/analysis/signals/test_signals.py tests/analysis/signals/test_llm_sentiment.py -q
```

Expected: PASS.

### Task 3: Documentation And Catalog Updates

**Files:**
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `config/sources.yaml`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md`
- Modify: `docs/superpowers/plans/2026-06-16-symbol-tagged-rss-feeds.md`

- [x] **Step 1: Update user-facing config docs**

Document `sources.rss.feeds[].symbol` as optional.

Explain:

- General feeds keep `symbol=None`.
- Symbol-tagged feeds are matched to that symbol even when the title has no ticker.
- Symbol-tagged feeds use symbol-specific idempotency keys.

- [x] **Step 2: Update improvement tracking docs**

Add R1d to the improvement catalog and mark the explicit "종목별 news feed" follow-up as implemented for user-configured RSS feeds.

Keep a remaining limitation for automatic vendor/feed discovery.

- [x] **Step 3: Update spec/plan status after verification**

After full verification, mark the spec acceptance criteria and plan checkboxes complete. Update the test count in docs that state it.

### Task 4: Verification And Review

**Files:** no intended source writes except review fixes.

- [x] **Step 1: Run focused tests**

```bash
uv run pytest tests/sources/test_config.py tests/sources/test_rss.py tests/analysis/signals/test_signals.py tests/analysis/signals/test_llm_sentiment.py -q
```

- [x] **Step 2: Run quality gates**

```bash
uv run ruff check .
uv run mypy mimir
uv run coverage run -m pytest
uv run coverage report --fail-under=80
git diff --check
```

- [x] **Step 3: Run subagent reviews**

Dispatch a spec compliance review first. After it approves, dispatch a code quality review.

- [x] **Step 4: Commit**

Commit only tracked intended files. Do not stage unrelated `uv.lock`.

Suggested commit:

```bash
git commit -m "feat: add symbol-tagged rss feeds"
```
