# News Alias Docs Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the completed R1/R1c news alias design specs with the current implementation and prevent stale completion metadata from returning.

**Architecture:** Add a docs health guard in `tests/test_readme_docs.py` for the two completed news alias specs, then update only those specs. The guard blocks stale fixed test counts, unchecked completed acceptance criteria, and R1 wording that ignores the later R1c default-alias implementation.

**Tech Stack:** Python 3.14, pytest docs guards, Markdown design specs.

## Global Constraints

- Do not touch, stage, remove, or rewrite the pre-existing untracked `uv.lock`.
- Runtime code write scope is empty. Do not change `mimir/analysis/*`, `mimir/sources/*`, config parsing, signal behavior, storage, network, retry, LLM gating, or default alias behavior.
- Test write scope is `tests/test_readme_docs.py`.
- Documentation write scope is `docs/superpowers/specs/2026-06-16-news-mention-alias-design.md` and `docs/superpowers/specs/2026-06-16-default-news-aliases-design.md`.
- The R1 spec must not claim the current completed state is proven by the stale fixed count `364 테스트`.
- The R1c spec must not claim the current completed state is proven by the stale fixed count `388 테스트`.
- The R1 spec acceptance criteria must be checked off or explicitly superseded to match the current completed implementation.
- The R1 spec must acknowledge the current composed news-alias state after R1c: `analysis.news.aliases` exists, `NewsMentionMatcher` is shared, `DEFAULT_NEWS_ALIASES` exists, and `analysis.news.use_default_aliases` can opt out of built-in aliases.
- Do not change historical implementation plans under `docs/superpowers/plans/`; this task updates completed design specs and the docs guard only.

---

### Task 1: Guard and Fix News Alias Spec Completion Truth

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-06-16-news-mention-alias-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-default-news-aliases-design.md`

**Interfaces:**
- Consumes: current implementation truth from `mimir/analysis/news_aliases.py`, `mimir/analysis/signals/news_matching.py`, `mimir/analysis/builder.py`, and `mimir/sources/config.py`.
- Produces: docs guard tests and updated specs that describe current R1/R1c state without stale completion counts.

- [ ] **Step 1: Add spec path constants**

Add these constants near `ANALYSIS_DESIGN_SPEC` in `tests/test_readme_docs.py`:

```python
NEWS_MENTION_ALIAS_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-news-mention-alias-design.md"
)
DEFAULT_NEWS_ALIASES_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-default-news-aliases-design.md"
)
```

- [ ] **Step 2: Add a markdown section helper**

Add this helper near `_readme_s2_roadmap_row`:

```python
def _markdown_section(text: str, heading: str) -> str:
    start = text.index(heading)
    rest = text[start + len(heading) :]
    next_heading = rest.find("\n## ")
    if next_heading == -1:
        return rest
    return rest[:next_heading]
```

- [ ] **Step 3: Write the failing news alias docs truth guard**

Add this test after `test_readme_s2_rows_match_current_llm_sentiment_state`:

```python
def test_news_alias_specs_match_current_completion_state() -> None:
    r1 = NEWS_MENTION_ALIAS_SPEC.read_text(encoding="utf-8")
    r1c = DEFAULT_NEWS_ALIASES_SPEC.read_text(encoding="utf-8")

    for path, text, stale_count in (
        (NEWS_MENTION_ALIAS_SPEC, r1, "364 테스트"),
        (DEFAULT_NEWS_ALIASES_SPEC, r1c, "388 테스트"),
    ):
        assert stale_count not in text, f"{path} still carries stale test count"
        status_line = next(line for line in text.splitlines() if line.startswith("> **상태**:"))
        assert "구현 완료" in status_line
        assert "ruff" in status_line
        assert "mypy" in status_line

    acceptance = _markdown_section(r1, "## 9. 수용 기준")
    assert "- [ ]" not in acceptance
    assert "기본 alias" in acceptance
    assert "R1c" in acceptance

    assert "NewsMentionMatcher" in r1
    assert "analysis.news.aliases" in r1
    assert "DEFAULT_NEWS_ALIASES" in r1
    assert "analysis.news.use_default_aliases" in r1
    assert "R1c" in r1
    assert "symbol-only 기본값" in r1

    assert "DEFAULT_NEWS_ALIASES" in r1c
    assert "analysis.news.use_default_aliases" in r1c
    assert "- [x] ruff, mypy, pytest, coverage 80% gate가 통과한다." in r1c
```

- [ ] **Step 4: Verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_news_alias_specs_match_current_completion_state -q
```

Expected: FAIL because the R1 spec still says `364 테스트`, the R1c spec still says `388 테스트`, and the R1 acceptance section still contains unchecked `- [ ]` items.

- [ ] **Step 5: Update the R1 status line**

In `docs/superpowers/specs/2026-06-16-news-mention-alias-design.md`, replace:

```markdown
> **상태**: ✅ 구현 완료 (`analysis.news.aliases` + shared `NewsMentionMatcher`). 364 테스트 · ruff · mypy · coverage gate 클린.
```

with:

```markdown
> **상태**: ✅ 구현 완료 (`analysis.news.aliases` + shared `NewsMentionMatcher`). 최신 검증은 README 테스트 배지와 docs health guard가 추적하며, ruff · mypy · coverage gate 클린 상태를 유지한다. 후속 R1c에서 `DEFAULT_NEWS_ALIASES`와 `analysis.news.use_default_aliases`가 추가되었다.
```

- [ ] **Step 6: Update R1 non-goal wording for R1c supersession**

In section `3. 목표와 비목표`, replace:

```markdown
- 기본 alias 사전을 코드에 넣지 않는다. v1은 사용자 설정만 지원한다.
```

with:

```markdown
- R1 v1 자체는 기본 alias 사전을 코드에 넣지 않는다. 현재 전체 구현은 후속 R1c에서 보수적 `DEFAULT_NEWS_ALIASES`와 `analysis.news.use_default_aliases` opt-out을 추가했다.
```

- [ ] **Step 7: Update R1 failure row for broad aliases**

In section `7. 실패와 예외 처리`, replace:

```markdown
| alias가 너무 넓어서 false positive가 생김 | 사용자 설정 문제로 문서화. R1c의 기본 alias는 `use_default_aliases: false`로 끌 수 있음 |
```

with:

```markdown
| alias가 너무 넓어서 false positive가 생김 | 사용자 설정 문제로 문서화. 후속 R1c 기본 alias도 `analysis.news.use_default_aliases: false`로 끌 수 있음 |
```

- [ ] **Step 8: Update R1 acceptance criteria**

Replace the entire `## 9. 수용 기준` checklist in `docs/superpowers/specs/2026-06-16-news-mention-alias-design.md` with:

```markdown
## 9. 수용 기준

- [x] `analysis.news.aliases`가 검증되고 `SourcesConfig.news_aliases`로 전달된다.
- [x] `NewsVolumeSignal`이 symbol과 alias를 모두 사용한다.
- [x] `LlmSentimentSignal`이 같은 alias matcher를 사용한다.
- [x] R1 v1 기준으로 설정이 없으면 기존 symbol-only 동작과 시그널 수가 유지되었다. 현재 `build_signals()` 기본 경로는 후속 R1c의 보수적 기본 alias를 병합하지만, 직접 생성한 `NewsVolumeSignal()`과 `LlmSentimentSignal()`은 symbol-only 기본값을 유지한다.
- [x] 잘못된 alias 설정은 `ValidationError`로 실패한다.
- [x] `config/sources.yaml`, `docs/reference/config/sources.md`, 개선 백로그, 확장성 문서가 새 설정을 설명한다.
- [x] 후속 R1c에서 `DEFAULT_NEWS_ALIASES`와 `analysis.news.use_default_aliases` opt-out이 구현되었다.
- [x] ruff, mypy, pytest, coverage 80% gate가 통과한다.
```

- [ ] **Step 9: Update R1 remaining-limits wording**

In section `10. 남는 한계`, replace the final paragraph with:

```markdown
R1 v1의 alias는 사용자가 관리했다. 이후 R1c에서 기본 watchlist용 보수적 `DEFAULT_NEWS_ALIASES`와 `analysis.news.use_default_aliases` opt-out을 추가했다. 남은 한계는 더 큰 watchlist를 위한 symbol metadata 기반 alias 후보 생성, 종목별 공식 feed, provider별 live endpoint discovery다.
```

- [ ] **Step 10: Update the R1c status line**

In `docs/superpowers/specs/2026-06-16-default-news-aliases-design.md`, replace:

```markdown
> **상태**: ✅ 구현 완료 (`DEFAULT_NEWS_ALIASES` + `analysis.news.use_default_aliases`). 388 테스트 · ruff · mypy · coverage gate 클린.
```

with:

```markdown
> **상태**: ✅ 구현 완료 (`DEFAULT_NEWS_ALIASES` + `analysis.news.use_default_aliases`). 최신 검증은 README 테스트 배지와 docs health guard가 추적하며, ruff · mypy · coverage gate 클린 상태를 유지한다.
```

- [ ] **Step 11: Verify GREEN for the docs guard**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_news_alias_specs_match_current_completion_state -q
uv run pytest tests/test_readme_docs.py -q
```

Expected: both commands pass.

- [ ] **Step 12: Run full gates**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: full suite passes, ruff passes, mypy passes, and diff check has no output.

- [ ] **Step 13: Commit**

Stage only the intentional docs-truth files:

```bash
git add tests/test_readme_docs.py docs/superpowers/specs/2026-06-16-news-mention-alias-design.md docs/superpowers/specs/2026-06-16-default-news-aliases-design.md
git commit -m "test(docs): guard news alias spec truth"
```

Do not stage `.superpowers/sdd/*`, `.git/sdd/*`, Obsidian files, or `uv.lock`.

---

## Self-Review

- Spec coverage: The plan covers stale R1/R1c fixed test counts, unchecked R1 acceptance criteria, current R1c default alias supersession, docs guard tests, full verification, and commit scope.
- Placeholder scan: No `TBD`, `TODO`, "similar to", or unspecified implementation steps remain.
- Type consistency: The plan uses current names `NEWS_MENTION_ALIAS_SPEC`, `DEFAULT_NEWS_ALIASES_SPEC`, `NewsMentionMatcher`, `DEFAULT_NEWS_ALIASES`, `analysis.news.aliases`, and `analysis.news.use_default_aliases`.
- Scope: Runtime code remains untouched; only docs guard and two completed specs are in scope.
