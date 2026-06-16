# News Captured Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 뉴스 시그널이 발행일(`ts`)이 아니라 수집일(`captured_at`) 기준으로 오늘과 baseline 윈도우를 읽도록 바꾼다.

**Architecture:** `DataReader`에 `read_captured_window()`를 추가해 `captured_at.date()` 기준 필터를 한 곳에 모은다. `news_volume`과 opt-in `llm_sentiment`만 이 API를 사용하고, 다른 데이터셋은 기존 `ts` 기준 reader 의미를 유지한다.

**Tech Stack:** Python 3.14, pytest, pydantic model records, ruff, mypy.

---

### Task 1: Captured Window Reader

**Files:**
- Modify: `mimir/storage/reader.py`
- Test: `tests/analysis/test_reader.py`

- [x] **Step 1: Write failing reader test**

Add this test to `tests/analysis/test_reader.py`:

```python
def test_read_captured_window_filters_by_captured_at_date(tmp_path: Path):
    records = [
        _rec("AAPL", 30, Dataset.NEWS, captured_day=31),
        _rec("AAPL", 30, Dataset.NEWS, captured_day=30),
    ]
    reader = _reader(tmp_path, records)

    recs = reader.read_captured_window(Dataset.NEWS, since=date(2026, 5, 31), until=date(2026, 5, 31))

    assert len(recs) == 1
    assert recs[0].captured_at.date() == date(2026, 5, 31)
```

Update `_rec()` in that test file to accept `captured_day: int = 31` and set `captured_at=datetime(2026, 5, captured_day, tzinfo=UTC)`.

- [x] **Step 2: Run reader test to verify RED**

Run:

```bash
uv run pytest tests/analysis/test_reader.py::test_read_captured_window_filters_by_captured_at_date -q
```

Expected: FAIL because `DataReader.read_captured_window` does not exist.

- [x] **Step 3: Implement `read_captured_window`**

Add this method to `mimir/storage/reader.py`:

```python
def read_captured_window(
    self,
    dataset: Dataset,
    *,
    symbol: str | None = None,
    since: date | None = None,
    until: date | None = None,
) -> list[Record]:
    out: list[Record] = []
    for rec in self._store.read_all(dataset):
        if symbol is not None and rec.symbol != symbol:
            continue
        day = rec.captured_at.date()
        if since is not None and day < since:
            continue
        if until is not None and day > until:
            continue
        out.append(rec)
    return out
```

Do not use `read_window()` here. Storage partitions are keyed by `rec.ts.date()`, so partition pruning by `since`/`until` would drop late-captured news before the captured-time filter can see it.

- [x] **Step 4: Run reader tests**

Run:

```bash
uv run pytest tests/analysis/test_reader.py -q
```

Expected: PASS.

### Task 2: News Signals Use Captured Window

**Files:**
- Modify: `mimir/analysis/signals/news_volume.py`
- Modify: `mimir/analysis/signals/llm_sentiment.py`
- Test: `tests/analysis/signals/test_signals.py`
- Test: `tests/analysis/signals/test_llm_sentiment.py`

- [x] **Step 1: Write failing `news_volume` current-window test**

Update `_rec()` in `tests/analysis/signals/test_signals.py` to accept `captured_day: int = 31` and set `captured_at=datetime(2026, 5, captured_day, tzinfo=UTC)`.

Add this test:

```python
def test_news_volume_counts_news_captured_today_even_when_published_yesterday(tmp_path: Path):
    recs = [_rec(Dataset.NEWS, None, 30, _news("AAPL late item", ""), captured_day=31)]

    r = NewsVolumeSignal().evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is not None
    assert r.signal == "news_volume"
```

- [x] **Step 2: Run test to verify RED**

Run:

```bash
uv run pytest tests/analysis/signals/test_signals.py::test_news_volume_counts_news_captured_today_even_when_published_yesterday -q
```

Expected: FAIL because `NewsVolumeSignal` still reads by `ts.date()`.

- [x] **Step 3: Write failing baseline test**

Add this test:

```python
def test_news_volume_baseline_uses_captured_at_window(tmp_path: Path):
    recs = [
        _rec(Dataset.NEWS, None, 30, _news("Apple current update", ""), captured_day=31),
        *[
            _rec(Dataset.NEWS, None, 20, _news("Apple baseline update", ""), captured_day=day)
            for day in range(24, 31)
        ],
    ]
    signal = NewsVolumeSignal(aliases={"AAPL": ["Apple"]})

    r = signal.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is not None
    assert "vs ~1.0/day baseline" in r.reason
```

- [x] **Step 4: Run baseline test to verify RED**

Run:

```bash
uv run pytest tests/analysis/signals/test_signals.py::test_news_volume_baseline_uses_captured_at_window -q
```

Expected: FAIL because baseline still reads by `ts.date()`.

- [x] **Step 5: Write failing LLM sentiment test**

Update `_rec()` in `tests/analysis/signals/test_llm_sentiment.py` to accept `captured_day: int = 31`.

Add this test:

```python
def test_llm_sentiment_classifies_news_captured_today_even_when_published_yesterday(tmp_path: Path):
    recs = [_rec(None, 30, _news("AAPL late update", ""), captured_day=31)]
    fake = FakeClassifier({"AAPL late update": _verdict(SignalDirection.BULLISH, 0.8)})
    sig = LlmSentimentSignal(classifier=fake, max_headlines=50)

    r = sig.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is not None
    assert r.signal == "llm_sentiment"
    assert fake.calls == [["AAPL late update"]]
```

- [x] **Step 6: Run LLM test to verify RED**

Run:

```bash
uv run pytest tests/analysis/signals/test_llm_sentiment.py::test_llm_sentiment_classifies_news_captured_today_even_when_published_yesterday -q
```

Expected: FAIL because `LlmSentimentSignal` still reads by `ts.date()`.

- [x] **Step 7: Implement signal wiring**

In `mimir/analysis/signals/news_volume.py`, replace both `reader.read(Dataset.NEWS, ...)` calls with `reader.read_captured_window(Dataset.NEWS, ...)`.

In `mimir/analysis/signals/llm_sentiment.py`, replace the news mention source with `reader.read_captured_window(Dataset.NEWS, since=as_of, until=as_of)`.

- [x] **Step 8: Run focused signal tests**

Run:

```bash
uv run pytest tests/analysis/signals/test_signals.py tests/analysis/signals/test_llm_sentiment.py -q
```

Expected: PASS.

### Task 3: Documentation and Verification

**Files:**
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `docs/superpowers/specs/2026-06-16-news-captured-window-design.md`
- Modify: `docs/superpowers/plans/2026-06-16-news-captured-window.md`

- [x] **Step 1: Update backlog and architecture docs**

Update `docs/IMPROVEMENTS.md` so captured window is no longer listed as a remaining R1 limitation. Keep 종목별 feed and 기본 alias 데이터셋 as follow-ups.

Update `docs/architecture/improvement-catalog.md` with an R1b section and remove captured window from the final remaining-debt sentence.

Update `docs/architecture/extensibility/README.md` to explain that news signals use `captured_at` windows while storage partitions still use event `ts`.

- [x] **Step 2: Update README badges**

After the full suite runs, update the README test badge count in:

```text
README.md
README.ko.md
README.zh.md
```

Expected count after adding five tests: `377 passing · 97% cov`.

- [x] **Step 3: Mark spec and plan status**

After verification, update the spec status line and check completed plan steps.

- [x] **Step 4: Run full verification**

Run:

```bash
uv run ruff check .
uv run mypy mimir
git diff --check
uv run coverage run -m pytest
uv run coverage report --fail-under=80
```

Expected: all commands exit 0.

---

## Self-Review

- Spec coverage: The plan covers captured-window reader behavior, both news signals, documentation, and verification.
- Placeholder scan: No `TBD`, `TODO`, or "similar to" placeholders remain.
- Type consistency: The new API is consistently named `read_captured_window` and keeps the same `dataset`, `symbol`, `since`, and `until` argument shape as `read()`.
- Non-goal: The plan does not change JSONL partitioning, add article crawling, add default alias data, or enable LLM by default.
