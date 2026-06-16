# News Mention Alias Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 공식 RSS feed가 티커 대신 회사명을 쓰는 경우에도 `news_volume`과 opt-in LLM 감성 시그널이 종목 관련 뉴스를 찾도록 alias 기반 매칭을 추가한다.

**Architecture:** `analysis.news.aliases` 설정을 `SourcesConfig`가 검증한다. `mimir/analysis/signals/news_matching.py`가 공통 matcher를 제공하고, `NewsVolumeSignal`과 `LlmSentimentSignal`이 같은 matcher를 사용한다.

**Tech Stack:** Python 3.14, pydantic config validation, pytest, ruff, mypy.

---

### Task 1: Shared News Mention Matcher

**Files:**
- Create: `mimir/analysis/signals/news_matching.py`
- Modify: `mimir/analysis/signals/news_volume.py`
- Modify: `mimir/analysis/signals/llm_sentiment.py`
- Test: `tests/analysis/signals/test_signals.py`
- Test: `tests/analysis/signals/test_llm_sentiment.py`

- [x] **Step 1: Write failing `news_volume` alias tests**

Add these tests to `tests/analysis/signals/test_signals.py`:

```python
def test_news_volume_matches_configured_alias_in_title(tmp_path: Path):
    recs = [_rec(Dataset.NEWS, None, 31, _news("Apple announces supplier update", ""))]
    signal = NewsVolumeSignal(aliases={"AAPL": ["Apple", "Apple Inc."]})

    r = signal.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))

    assert r is not None
    assert r.signal == "news_volume"


def test_news_volume_matches_configured_alias_in_summary(tmp_path: Path):
    recs = [_rec(Dataset.NEWS, None, 31, _news("Market update", "Samsung Electronics reports"))]
    signal = NewsVolumeSignal(aliases={"005930": ["Samsung Electronics", "삼성전자"]})

    r = signal.evaluate("005930", Market.KR, AS_OF, _reader(tmp_path, recs))

    assert r is not None


def test_news_volume_ignores_blank_alias(tmp_path: Path):
    recs = [_rec(Dataset.NEWS, None, 31, _news("Unrelated", ""))]
    signal = NewsVolumeSignal(aliases={"AAPL": ["", "   "]})

    assert signal.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs)) is None
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest \
  tests/analysis/signals/test_signals.py::test_news_volume_matches_configured_alias_in_title \
  tests/analysis/signals/test_signals.py::test_news_volume_matches_configured_alias_in_summary \
  tests/analysis/signals/test_signals.py::test_news_volume_ignores_blank_alias \
  -q
```

Expected: FAIL because `NewsVolumeSignal(aliases=...)` is not supported yet.

- [x] **Step 3: Add shared matcher and wire `NewsVolumeSignal`**

Create `mimir/analysis/signals/news_matching.py` with `NewsMentionMatcher`.

Implementation requirements:

- `terms_for(symbol)` returns symbol plus configured aliases for that symbol.
- Blank aliases are ignored.
- Duplicate terms are removed while preserving order.
- Matching is case-insensitive.
- Regex boundaries use Unicode word-character guards: `(?<![\w])` and `(?![\w])`.
- `mentions(record, symbol)` reads `title` and `summary` via `news_payload(record)`.

Update `NewsVolumeSignal.__init__(aliases=None)` and replace the local `_mentions` helper with `self._matcher.mentions(...)`.

- [x] **Step 4: Run focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/analysis/signals/test_signals.py -q
```

Expected: PASS.

- [x] **Step 4a: Add matcher hardening tests**

Add tests that prove:

- `terms_for()` returns a tuple, keeps the symbol first, and removes duplicate aliases case-insensitively.
- Matching is case-insensitive.
- A Korean alias like `삼성전자` does not match inside `삼성전자우`.
- Mutating the caller's alias dict/list after constructing `NewsMentionMatcher` does not change matcher behavior.

- [x] **Step 5: Wire `LlmSentimentSignal` to the same matcher**

Update `LlmSentimentSignal.__init__` with `aliases: Mapping[str, Sequence[str]] | None = None`.

Replace its local `_mentions` helper with `self._matcher.mentions(...)`.

Add a test in `tests/analysis/signals/test_llm_sentiment.py` that injects `_FakeClassifier`, creates a news record with `Apple` but no `AAPL`, constructs `LlmSentimentSignal(aliases={"AAPL": ["Apple"]}, ...)`, and asserts the signal returns a result.

- [x] **Step 6: Run LLM sentiment focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/analysis/signals/test_llm_sentiment.py -q
```

Expected: PASS without importing or calling real `anthropic`.

### Task 2: Config and Builder Wiring

**Files:**
- Modify: `mimir/sources/config.py`
- Modify: `mimir/analysis/builder.py`
- Test: `tests/sources/test_config.py`
- Test: `tests/analysis/test_builder.py`

- [x] **Step 1: Write failing config tests**

Add these tests to `tests/sources/test_config.py`:

```python
def test_analysis_news_aliases_parse_from_config():
    cfg = parse_sources_config(
        {"analysis": {"news": {"aliases": {"AAPL": ["Apple", "Apple Inc."]}}}}
    )
    assert cfg.news_aliases == {"AAPL": ["Apple", "Apple Inc."]}


def test_analysis_news_alias_typo_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config({"analysis": {"news": {"aliasez": {"AAPL": ["Apple"]}}}})


def test_analysis_news_alias_value_must_be_list():
    with pytest.raises(ValidationError):
        parse_sources_config({"analysis": {"news": {"aliases": {"AAPL": "Apple"}}}})
```

- [x] **Step 2: Run config tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest \
  tests/sources/test_config.py::test_analysis_news_aliases_parse_from_config \
  tests/sources/test_config.py::test_analysis_news_alias_typo_raises_validation_error \
  tests/sources/test_config.py::test_analysis_news_alias_value_must_be_list \
  -q
```

Expected: FAIL because `analysis.news` is not modeled yet.

- [x] **Step 3: Implement config model**

Add `news_aliases: dict[str, list[str]] | None = None` to `SourcesConfig`.

Add `_NewsBlock` with `aliases: dict[str, list[str]] | None = None`.

Add `news: _NewsBlock | None = None` to `_AnalysisBlock`.

Map `top_level.analysis.news.aliases` into `SourcesConfig.news_aliases`.

- [x] **Step 4: Write builder wiring tests**

Add a test to `tests/analysis/test_builder.py` that builds signals with aliases and proves the constructed `news_volume` signal can match an alias.

Add a fake-classifier test that enables LLM sentiment and proves the constructed `llm_sentiment` signal can match an alias.

- [x] **Step 5: Implement builder wiring**

Update `build_signals()`:

```python
NewsVolumeSignal(aliases=cfg.news_aliases)
```

When appending `LlmSentimentSignal`, pass:

```python
aliases=cfg.news_aliases
```

- [x] **Step 6: Run focused config and builder tests**

Run:

```bash
.venv/bin/python -m pytest tests/sources/test_config.py tests/analysis/test_builder.py -q
```

Expected: PASS.

### Task 3: Documentation and Verification

**Files:**
- Modify: `config/sources.yaml`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/superpowers/specs/2026-06-13-llm-sentiment-seam-design.md`
- Create: `docs/superpowers/specs/2026-06-16-news-mention-alias-design.md`
- Create: `docs/superpowers/plans/2026-06-16-news-mention-aliases.md`

- [x] **Step 1: Update config example**

Add a commented `analysis.news.aliases` example to `config/sources.yaml`:

```yaml
# analysis:
#   news:
#     aliases:
#       AAPL: ["Apple", "Apple Inc."]
```

Keep the existing `macro_regime` example under the same `analysis:` block.

- [x] **Step 2: Update config reference**

Update `docs/reference/config/sources.md`:

- Add `analysis.news.aliases` to the overview YAML.
- Add a subsection explaining alias keys and values.
- Explain that aliases affect stored title/summary matching only.
- Explain that alias settings do not enable LLM calls by themselves.

- [x] **Step 3: Update architecture and backlog docs**

Update `docs/architecture/extensibility/README.md` to describe news alias matching as an analysis extension point.

Update `docs/architecture/improvement-catalog.md` and `docs/IMPROVEMENTS.md` so R1 is no longer fully open. Mark alias matching as implemented and leave remaining limitations as per-symbol feeds, default alias dictionaries, or LLM promotion.

Update the LLM seam spec to say its headline selection now uses the shared alias matcher when configured.

- [x] **Step 4: Run full verification**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy mimir
.venv/bin/coverage run -m pytest
.venv/bin/coverage report --fail-under=80
git diff --check
```

Expected: ruff passes, mypy passes, pytest passes, coverage stays at or above 80%, and no whitespace errors exist.

---

## Self-Review

- Spec coverage: The plan covers alias config validation, shared matcher behavior, `news_volume` wiring, LLM seam wiring, documentation, and full verification.
- Placeholder scan: No `TBD`, `TODO`, or "similar to" placeholders remain.
- Type consistency: The config field is `news_aliases`, the YAML path is `analysis.news.aliases`, and both news signals receive `aliases=cfg.news_aliases`.
- Non-goal: The plan does not add article body crawling, a built-in company alias dictionary, or default LLM activation.
