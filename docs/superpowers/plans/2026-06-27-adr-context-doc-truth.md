# ADR Context Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop architecture ADR context metadata from carrying stale fixed test/coverage/tool snapshots and update ADR-0001 to point current verification at the living docs health sources.

**Architecture:** Add one focused docs health guard beside the existing README/design-spec guards in `tests/test_readme_docs.py`. Update only ADR-0001's context metadata so it preserves the 2026-06-13 decision history while delegating current health/verification state to the improvement catalog and README/docs health guards.

**Tech Stack:** Python 3.14, pytest, Markdown docs, existing `tests/test_readme_docs.py` docs health suite.

## Global Constraints

- Do not touch, stage, remove, or commit the pre-existing untracked `uv.lock`.
- Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` scratch/report files into implementation commits.
- Use exact staging only.
- Preserve ADR history: ADR-0001 may say it records the 2026-06-13 branch decision, but it must not present stale fixed test counts, stale coverage percentages, or tool-clean claims as current health metadata.
- Current verification wording should point to README test badges/docs health guards and the improvement catalog, not historical suite sizes.

---

### Task 1: Guard ADR-0001 Current Context Metadata

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/architecture/adr/0001-incremental-extensibility-and-deferral.md`
- Maybe modify: `README.md`, `README.ko.md`, `README.zh.md` only if pytest collection count changes.

**Interfaces:**
- Consumes: existing docs health helpers in `tests/test_readme_docs.py`, especially `_status_line()` style direct Markdown assertions and the existing stale verification regex constants.
- Produces: `test_architecture_adrs_do_not_publish_stale_current_verification_context()` as the regression guard for ADR current-context metadata.

- [ ] **Step 1: Add the failing ADR docs health test**

  Add this constant near the other top-level docs paths:

  ```python
  INCREMENTAL_EXTENSIBILITY_ADR = Path(
      "docs/architecture/adr/0001-incremental-extensibility-and-deferral.md"
  )
  ```

  Add this test near the completed design-spec status/acceptance guards:

  ```python
  def test_architecture_adrs_do_not_publish_stale_current_verification_context() -> None:
      text = INCREMENTAL_EXTENSIBILITY_ADR.read_text(encoding="utf-8")
      header = text.split("\n\n", 1)[0]

      assert "발전 카탈로그" in header
      assert "README 테스트 배지와 docs health guard" in header
      assert "122 테스트" not in header
      assert "95% 커버리지" not in header
      assert "mypy strict" not in header

      for pattern in COMPLETED_DESIGN_SPEC_STATUS_STALE_PATTERNS:
          assert not pattern.search(header), (
              f"{INCREMENTAL_EXTENSIBILITY_ADR} header carries stale verification metadata"
          )
  ```

- [ ] **Step 2: Run the targeted test and verify RED**

  Run:

  ```bash
  uv run pytest tests/test_readme_docs.py::test_architecture_adrs_do_not_publish_stale_current_verification_context -q
  ```

  Expected: FAIL because ADR-0001 currently says `122 테스트 · 95% 커버리지 · mypy strict`.

- [ ] **Step 3: Update ADR-0001 header only**

  Replace the stale context lines at the top of `docs/architecture/adr/0001-incremental-extensibility-and-deferral.md` with wording equivalent to:

  ```markdown
  > **맥락**: S1–S4가 구현된 건강한 코드베이스에서 "원래 스코프 이상의 확장·개선·심화"를 진행하라는 요청.
  > **현재 보정(2026-06-27)**: 이 ADR은 2026-06-13 당시의 분기 결정을 기록한다. 이후 A4, C1, B1, B2와 후속 운영·확장성 증분이 구현됐다. 최신 구현 상태는 [발전 카탈로그](../improvement-catalog.md)를 기준으로 보고, 최신 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
  ```

  Keep the decision, rationale, result, and reference sections unchanged unless the new guard proves another stale current-state claim exists in the header.

- [ ] **Step 4: Run focused docs health tests and verify GREEN**

  Run:

  ```bash
  uv run pytest tests/test_readme_docs.py::test_architecture_adrs_do_not_publish_stale_current_verification_context -q
  uv run pytest tests/test_readme_docs.py -q
  ```

  Expected: targeted test passes, then the docs health suite passes.

- [ ] **Step 5: Run collection count and update README counts only if needed**

  Run:

  ```bash
  uv run pytest --collect-only -q
  ```

  Expected after adding one test: collection count increases by 1. Update tests badges and quality table rows in `README.md`, `README.ko.md`, and `README.zh.md` to the collected count if they no longer match.

- [ ] **Step 6: Run controller gates**

  Run:

  ```bash
  uv run pytest -q
  uv run ruff check .
  uv run mypy mimir
  git diff --check
  git status --short --branch
  ```

  Expected: all tests pass, ruff passes, mypy passes, diff-check clean. Git status should show only intentional tracked edits plus the expected unrelated untracked `CLAUDE.md`, `docs/superpowers/handoffs/`, and `uv.lock`.

- [ ] **Step 7: Commit exactly the intentional files**

  Stage only:

  ```bash
  git add tests/test_readme_docs.py docs/architecture/adr/0001-incremental-extensibility-and-deferral.md README.md README.ko.md README.zh.md
  ```

  If README counts did not change, do not stage the README files.

  Commit:

  ```bash
  git commit -m "test(docs): guard architecture adr verification context"
  ```
