# Default News Aliases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기본 watchlist의 핵심 종목에 대해 보수적 news alias를 제공하고, 사용자가 필요하면 끌 수 있게 한다.

**Architecture:** `mimir/analysis/news_aliases.py`가 기본 alias registry와 병합 함수를 가진다. `build_signals()`는 병합된 alias map을 `NewsVolumeSignal`과 opt-in `LlmSentimentSignal`에 전달한다. `analysis.news.use_default_aliases`가 기본 alias opt-out을 담당한다.

**Tech Stack:** Python 3.14, pydantic config model, pytest, ruff, mypy.

---

### Task 1: Alias Registry

**Files:**
- Create: `mimir/analysis/news_aliases.py`
- Test: `tests/analysis/test_news_aliases.py`

- [x] **Step 1: Write failing default merge test**

Create `tests/analysis/test_news_aliases.py`:

```python
from mimir.analysis.news_aliases import merge_news_aliases


def test_merge_news_aliases_includes_defaults_and_user_aliases():
    aliases = merge_news_aliases({"AAPL": ["Apple", "Cupertino company"]})

    assert aliases["AAPL"] == ("Apple", "Apple Inc.", "Cupertino company")
    assert aliases["MSFT"] == ("Microsoft", "Microsoft Corp.")
```

Run:

```bash
uv run pytest tests/analysis/test_news_aliases.py::test_merge_news_aliases_includes_defaults_and_user_aliases -q
```

Expected: FAIL because `mimir.analysis.news_aliases` does not exist.

- [x] **Step 2: Write failing opt-out merge test**

Add:

```python
def test_merge_news_aliases_can_disable_defaults():
    aliases = merge_news_aliases(
        {"AAPL": ["Cupertino company"]},
        include_defaults=False,
    )

    assert aliases == {"AAPL": ("Cupertino company",)}
```

Run:

```bash
uv run pytest tests/analysis/test_news_aliases.py::test_merge_news_aliases_can_disable_defaults -q
```

Expected: FAIL for the same missing module reason.

- [x] **Step 3: Implement registry and merge helper**

Create `mimir/analysis/news_aliases.py` with:

```python
from __future__ import annotations

from collections.abc import Mapping, Sequence

DEFAULT_NEWS_ALIASES: dict[str, tuple[str, ...]] = {
    "AAPL": ("Apple", "Apple Inc."),
    "MSFT": ("Microsoft", "Microsoft Corp."),
    "NVDA": ("NVIDIA", "Nvidia Corporation"),
    "005930": ("Samsung Electronics", "삼성전자"),
}


def merge_news_aliases(
    configured: Mapping[str, Sequence[str]] | None = None,
    *,
    include_defaults: bool = True,
) -> dict[str, tuple[str, ...]]:
    ...
```

The helper must dedupe case-insensitively per symbol and drop blank aliases.

- [x] **Step 4: Run registry tests**

```bash
uv run pytest tests/analysis/test_news_aliases.py -q
```

Expected: PASS.

### Task 2: Config Opt-Out

**Files:**
- Modify: `mimir/sources/config.py`
- Modify: `tests/sources/test_config.py`

- [x] **Step 1: Write failing parse test**

Add:

```python
def test_analysis_news_use_default_aliases_parse_from_config():
    cfg = parse_sources_config({"analysis": {"news": {"use_default_aliases": False}}})

    assert cfg.use_default_news_aliases is False
```

Run:

```bash
uv run pytest tests/sources/test_config.py::test_analysis_news_use_default_aliases_parse_from_config -q
```

Expected: FAIL because `SourcesConfig` has no `use_default_news_aliases`.

- [x] **Step 2: Write failing typo test**

Add:

```python
def test_analysis_news_use_default_aliases_typo_raises():
    with pytest.raises(ValidationError):
        parse_sources_config({"analysis": {"news": {"use_defaults_aliases": False}}})
```

Run:

```bash
uv run pytest tests/sources/test_config.py::test_analysis_news_use_default_aliases_typo_raises -q
```

Expected: PASS if `extra="forbid"` already catches the typo, or FAIL until `_NewsBlock` accepts the correct field.

- [x] **Step 3: Implement config field**

Add `use_default_news_aliases: bool = True` to `SourcesConfig`.

Add `use_default_aliases: bool = True` to `_NewsBlock`.

In `parse_sources_config()`, derive:

```python
news_block = top_level.analysis.news if top_level.analysis and top_level.analysis.news else None
use_default_news_aliases = news_block.use_default_aliases if news_block else True
```

- [x] **Step 4: Run config tests**

```bash
uv run pytest tests/sources/test_config.py -q
```

Expected: PASS.

### Task 3: Builder Wiring

**Files:**
- Modify: `mimir/analysis/builder.py`
- Modify: `tests/analysis/test_builder.py`

- [x] **Step 1: Write failing news_volume default alias test**

Add:

```python
def test_build_signals_uses_default_news_aliases_for_news_volume(tmp_path: Path):
    news_volume = next(s for s in build_signals() if s.id == "news_volume")

    result = news_volume.evaluate(
        "AAPL",
        Market.US,
        AS_OF,
        _reader(tmp_path, [_news_record(31, "Apple supplier update", "")]),
    )

    assert result is not None
```

Run:

```bash
uv run pytest tests/analysis/test_builder.py::test_build_signals_uses_default_news_aliases_for_news_volume -q
```

Expected: FAIL because `build_signals()` still passes no alias when config is absent.

- [x] **Step 2: Write failing default alias opt-out test**

Add:

```python
def test_build_signals_can_disable_default_news_aliases(tmp_path: Path):
    cfg = SourcesConfig(use_default_news_aliases=False)
    news_volume = next(s for s in build_signals(cfg) if s.id == "news_volume")

    result = news_volume.evaluate(
        "AAPL",
        Market.US,
        AS_OF,
        _reader(tmp_path, [_news_record(31, "Apple supplier update", "")]),
    )

    assert result is None
```

Run:

```bash
uv run pytest tests/analysis/test_builder.py::test_build_signals_can_disable_default_news_aliases -q
```

Expected: PASS before and after implementation if the new config field exists but builder does not use defaults; it protects opt-out semantics after implementation.

- [x] **Step 3: Write failing LLM default alias test**

Add a fake-classifier test proving opt-in `llm_sentiment` also matches `Apple` without explicit user aliases.

Run:

```bash
uv run pytest tests/analysis/test_builder.py::test_build_signals_uses_default_news_aliases_for_llm_sentiment -q
```

Expected: FAIL because LLM gets no alias map by default.

- [x] **Step 4: Wire builder**

In `build_signals()`:

```python
from mimir.analysis.news_aliases import merge_news_aliases

aliases = merge_news_aliases(
    cfg.news_aliases,
    include_defaults=cfg.use_default_news_aliases,
)
```

Pass `aliases=aliases` to both news signals.

- [x] **Step 5: Run builder tests**

```bash
uv run pytest tests/analysis/test_builder.py tests/analysis/signals/test_signals.py tests/analysis/signals/test_llm_sentiment.py -q
```

Expected: PASS.

### Task 4: Docs And Verification

**Files:**
- Modify: `config/sources.yaml`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/superpowers/specs/2026-06-16-news-mention-alias-design.md`
- Create: `docs/superpowers/specs/2026-06-16-default-news-aliases-design.md`
- Create: `docs/superpowers/plans/2026-06-16-default-news-aliases.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

- [x] **Step 1: Update docs**

Document that built-in aliases are enabled by default, user aliases are additive, and `analysis.news.use_default_aliases: false` disables them.

- [x] **Step 2: Mark acceptance checkboxes**

After tests pass, update R1c status and plan checkboxes.

- [x] **Step 3: Run full verification**

```bash
uv run ruff check .
uv run mypy mimir
uv run coverage run -m pytest
uv run coverage report --fail-under=80
git diff --check
```

Expected: all commands exit 0. Final run: 388 tests passed, total coverage 97%.

- [x] **Step 4: Run local pre-commit review**

Review `git diff`, `git status`, and the verification output before committing. Fix Critical and Important issues before committing.

- [x] **Step 5: Commit**

```bash
git add mimir tests docs config README.md README.ko.md README.zh.md
git commit -m "feat: add default news aliases"
```
