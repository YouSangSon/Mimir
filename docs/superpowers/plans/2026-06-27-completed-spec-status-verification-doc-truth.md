# Completed Spec Status Verification Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a scalable docs health guard for completed design-spec status lines and remove the remaining stale `ruff · mypy · coverage gate` completion metadata from already-completed specs.

**Architecture:** This is a docs-truth slice. The runtime implementation already exists; the change adds one generic `tests/test_readme_docs.py` guard over completed `docs/superpowers/specs/*.md` status lines, updates the current stale status lines in five completed specs, and updates README EN/KO/ZH test counts after pytest collection proves the new count.

**Tech Stack:** Python 3.14, pytest, pathlib-based Markdown checks, existing README docs health tests, completed design specs under `docs/superpowers/specs/`, README badges in `README.md`, `README.ko.md`, and `README.zh.md`.

## Global Constraints

- Work in-place on `main`; do not create a worktree for this slice because the repo handoff explicitly says to continue from this checkout.
- Do not touch, stage, remove, or commit the pre-existing untracked `uv.lock`.
- Do not stage or commit `CLAUDE.md`, `docs/superpowers/handoffs/`, or new `.superpowers/` scratch reports.
- Do not edit runtime code for this slice unless the RED docs guard proves a current implementation claim is false.
- Keep implementation scope to `tests/test_readme_docs.py`, the five target specs, and README EN/KO/ZH test count updates.
- Use TDD: add the failing docs guard first, run the targeted test and observe RED, then update docs.
- Completed design-spec status lines must not claim stale fixed test counts or historical command/coverage gate completion wording.
- Completed design-spec status lines that carry current verification wording must point to README test badges and docs health guards, not historical suite sizes, coverage gates, ruff/mypy status, or command lists.
- Preserve design-history context. Specs may keep historical acceptance criteria or design rationale where appropriate, but completion metadata must match current truth.
- Commit only intentional plan/test/docs/README files with exact staging.

---

## File Structure

- Modify `tests/test_readme_docs.py`: add `COMPLETED_DESIGN_SPEC_STATUS_STALE_PHRASES`, `COMPLETED_DESIGN_SPEC_STATUS_STALE_PATTERNS`, and `test_completed_design_spec_status_lines_use_current_verification_metadata()`.
- Modify `docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md`: remove stale `ruff · mypy · coverage gate` current-status wording.
- Modify `docs/superpowers/specs/2026-06-13-typed-payload-design.md`: remove stale `ruff · mypy · coverage gate` current-status wording.
- Modify `docs/superpowers/specs/2026-06-13-data-doctor-design.md`: remove stale `ruff · mypy · coverage gate` current-status wording.
- Modify `docs/superpowers/specs/2026-06-16-news-mention-alias-design.md`: remove stale `ruff · mypy · coverage gate` current-status wording.
- Modify `docs/superpowers/specs/2026-06-16-default-news-aliases-design.md`: remove stale `ruff · mypy · coverage gate` current-status wording.
- Modify `README.md`, `README.ko.md`, and `README.zh.md`: update test badge/table counts to the count reported by `uv run pytest --collect-only -q` after the new guard is added.

---

### Task 1: Guard Completed Design-Spec Status Metadata

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md`
- Modify: `docs/superpowers/specs/2026-06-13-typed-payload-design.md`
- Modify: `docs/superpowers/specs/2026-06-13-data-doctor-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-news-mention-alias-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-default-news-aliases-design.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

**Interfaces:**
- Consumes: existing `Path` import and docs tests in `tests/test_readme_docs.py`.
- Consumes: existing README count guard `test_readme_test_badges_match_collected_pytest_count()`.
- Produces: one docs guard test named `test_completed_design_spec_status_lines_use_current_verification_metadata`.
- Produces: completed spec status wording containing `최신 검증은 README 테스트 배지와 docs health guard가 추적한다`.

- [ ] **Step 1: Add stale status metadata constants**

In `tests/test_readme_docs.py`, add these constants after `S2_ANALYSIS_DESIGN_STALE_PHRASES`:

```python
COMPLETED_DESIGN_SPEC_STATUS_STALE_PHRASES = (
    "coverage gate",
    "coverage 80% gate",
    "커버리지 ≥ 80%",
    "diff-check",
    "diff check",
    "ruff · mypy",
    "ruff, mypy",
    "uv run pytest",
    "uv run ruff",
    "uv run mypy",
    "git diff --check",
)
COMPLETED_DESIGN_SPEC_STATUS_STALE_PATTERNS = (
    re.compile(r"\b\d{3,4}\s+tests?\b"),
    re.compile(r"\b\d{3,4}\s+passed\b"),
    re.compile(r"\b\d{3,4}\s+테스트\b"),
    re.compile(r"\b\d{2,3}%\s*(?:cov|coverage|커버리지)\b", re.IGNORECASE),
)
```

- [ ] **Step 2: Add the failing generic docs guard**

In `tests/test_readme_docs.py`, add this test immediately after `_status_line()`:

```python
def test_completed_design_spec_status_lines_use_current_verification_metadata() -> None:
    for path in sorted(Path("docs/superpowers/specs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            status = _status_line(text)
        except StopIteration:
            continue

        if "구현 완료" not in status:
            continue

        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status, (
            f"{path} completed status must point at README/docs health verification"
        )
        for phrase in COMPLETED_DESIGN_SPEC_STATUS_STALE_PHRASES:
            assert phrase not in status, f"{path} completed status still says: {phrase}"
        for pattern in COMPLETED_DESIGN_SPEC_STATUS_STALE_PATTERNS:
            assert not pattern.search(status), (
                f"{path} completed status still carries stale fixed verification metadata"
            )
```

- [ ] **Step 3: Run RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_completed_design_spec_status_lines_use_current_verification_metadata -q
```

Expected before docs edits: FAIL. The first failure should mention one of these files and the stale phrase `coverage gate`:

```text
docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md
docs/superpowers/specs/2026-06-13-typed-payload-design.md
docs/superpowers/specs/2026-06-13-data-doctor-design.md
docs/superpowers/specs/2026-06-16-news-mention-alias-design.md
docs/superpowers/specs/2026-06-16-default-news-aliases-design.md
```

Capture the command and relevant failure in the worker report. If the test errors because of a syntax/import mistake, fix the test until it fails for the stale status metadata.

- [ ] **Step 4: Update INC1 status metadata**

In `docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (feat/config-driven-extensibility). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다. 후속 A2/A3/A3b에서 macro series registry, 선언적 source registry, source entry points가 추가됐다.
```

- [ ] **Step 5: Update INC2 status metadata**

In `docs/superpowers/specs/2026-06-13-typed-payload-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (Increment 2 typed payload rollout). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다. 이후 `Dataset.EVALUATION`/`BucketStat`도 같은 typed payload boundary에 포함됐다.
```

- [ ] **Step 6: Update INC3 status metadata**

In `docs/superpowers/specs/2026-06-13-data-doctor-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (Increment 3 doctor MVP + 후속 HTML/i18n/dashboard 통합). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다. scheduled workflow의 `mimir.doctor --strict` hard gate는 의도적으로 추가하지 않았다.
```

- [ ] **Step 7: Update R1 status metadata**

In `docs/superpowers/specs/2026-06-16-news-mention-alias-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`analysis.news.aliases` + shared `NewsMentionMatcher`). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다. 후속 R1c에서 `DEFAULT_NEWS_ALIASES`와 `analysis.news.use_default_aliases`가 추가되었다.
```

- [ ] **Step 8: Update R1c status metadata**

In `docs/superpowers/specs/2026-06-16-default-news-aliases-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`DEFAULT_NEWS_ALIASES` + `analysis.news.use_default_aliases`). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 9: Update stale status-specific expectations in existing tests**

In `tests/test_readme_docs.py`, update `test_news_alias_specs_match_current_completion_state()` so it no longer requires `ruff` and `mypy` in the R1/R1c status lines. Replace:

```python
        assert "구현 완료" in status_line
        assert "ruff" in status_line
        assert "mypy" in status_line
```

with:

```python
        assert "구현 완료" in status_line
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status_line
        assert "coverage gate" not in status_line
```

- [ ] **Step 10: Run GREEN for the focused guard**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_completed_design_spec_status_lines_use_current_verification_metadata -q
```

Expected: PASS.

- [ ] **Step 11: Run docs tests and collect count**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q
```

Expected docs tests: PASS after README counts are updated. Expected collect count before README updates is one above the current `638`, but use the actual collected count.

- [ ] **Step 12: Update README test counts**

If `uv run pytest --collect-only -q` reports `639 tests collected`, update all README badge/table counts:

In `README.md`:

```markdown
![tests](https://img.shields.io/badge/tests-639%20passing%20%C2%B7%2098%25%20cov-3da639)
| **Tests** | 639 passing (adapters verified with recorded fixtures, no network) |
```

In `README.ko.md`:

```markdown
![tests](https://img.shields.io/badge/tests-639%20passing%20%C2%B7%2098%25%20cov-3da639)
| **테스트** | 639 passing (어댑터는 녹화 픽스처로 네트워크 없이 검증) |
```

In `README.zh.md`:

```markdown
![tests](https://img.shields.io/badge/tests-639%20passing%20%C2%B7%2098%25%20cov-3da639)
| **测试** | 639 passing（适配器使用录制 fixture 验证，无需网络） |
```

If collection reports a different count, use that count instead and record the actual output in the worker report.

- [ ] **Step 13: Run final task gates**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: all pass. Capture exact output summaries in the worker report.

- [ ] **Step 14: Commit implementation**

Stage only intentional files:

```bash
git add tests/test_readme_docs.py \
  docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md \
  docs/superpowers/specs/2026-06-13-typed-payload-design.md \
  docs/superpowers/specs/2026-06-13-data-doctor-design.md \
  docs/superpowers/specs/2026-06-16-news-mention-alias-design.md \
  docs/superpowers/specs/2026-06-16-default-news-aliases-design.md \
  README.md README.ko.md README.zh.md
git commit -m "test(docs): guard completed spec status metadata"
```

Do not stage `uv.lock`, `CLAUDE.md`, `docs/superpowers/handoffs/`, or new `.superpowers/` files.
