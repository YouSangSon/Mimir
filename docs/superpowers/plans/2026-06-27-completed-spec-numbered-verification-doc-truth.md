# Completed Design Spec Numbered Verification Metadata Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completed design specs must not publish stale fixed coverage/tool-clean metadata in test headings or numbered completion/acceptance criteria.

**Architecture:** Extend the existing docs health tests in `tests/test_readme_docs.py` with one generic guard for completed `docs/superpowers/specs/*.md` files. The guard should cover `## ... 테스트 ... 80%+` headings and numbered lines inside `완료 기준`/`수용 기준`/`Acceptance Criteria` sections, while reusing the current acceptance-verification stale-metadata detector so legitimate CLI behavior and domain references are not blocked.

**Tech Stack:** Python 3.14, pytest, pathlib, regex, Markdown docs.

## Global Constraints

- Do not touch, stage, remove, or commit the unrelated untracked `uv.lock`.
- Do not stage or commit `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` scratch files.
- Scope this slice to `tests/test_readme_docs.py`, the five affected design specs, and README EN/KO/ZH test counts if collection changes.
- Preserve legitimate tool-stack documentation such as `docs/superpowers/specs/2026-05-31-collector-design.md:365`; a development tools list is not a stale current verification claim.
- Preserve legitimate domain references such as typed payload docs' `mypy strict 내로잉` and data doctor expected-coverage wording.
- Current verification wording should point to README test badges and docs health guards, not fixed test counts, fixed coverage targets, `ruff`, `mypy`, `pytest`, `uv run ...`, or `git diff --check`.
- Use TDD: add the failing docs health test first, run it and observe RED, then update docs and README counts.

---

### Task 1: Guard Numbered Completion Criteria And Test Headings

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-05-31-analysis-design.md`
- Modify: `docs/superpowers/specs/2026-05-31-delivery-design.md`
- Modify: `docs/superpowers/specs/2026-05-31-historical-design.md`
- Modify: `docs/superpowers/specs/2026-05-31-collector-design.md`
- Modify: `docs/superpowers/specs/2026-06-13-signal-backtest-design.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

**Interfaces:**
- Consumes: existing helpers and constants in `tests/test_readme_docs.py`, especially `_status_line()`, `_has_stale_acceptance_verification_metadata()`, and `COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION`.
- Produces: one new docs health test that fails on the current stale headings/numbered criteria and passes once the affected docs point verification to README/docs health guards.

- [ ] **Step 1: Add the failing docs health test**

Add helper constants/functions near the existing completed-design-spec guard helpers:

```python
COMPLETED_DESIGN_SPEC_COMPLETION_HEADING_KEYWORDS = (
    "완료 기준",
    "수용 기준",
    "Acceptance Criteria",
    "Acceptance",
)
COMPLETED_DESIGN_SPEC_NUMBERED_CURRENT_VERIFICATION = (
    "최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다."
)
COMPLETED_DESIGN_SPEC_TEST_HEADING_STALE_PATTERN = re.compile(
    r"^##\s+.*테스트.*(?:80%|coverage|커버리지)",
    re.IGNORECASE,
)
COMPLETED_DESIGN_SPEC_NUMBERED_ITEM_RE = re.compile(r"^\s*\d+\.\s+")
```

Add this test after `test_completed_design_spec_acceptance_verification_lines_use_current_metadata()`:

```python
def test_completed_design_spec_numbered_completion_criteria_use_current_metadata() -> None:
    stale_headings = (
        "## 9. 테스트 (TDD, 80%+)",
        "## 15. 테스트 전략 (TDD, 80%+)",
    )
    current_headings = (
        "## 9. 테스트 전략 (TDD)",
        "## 11. 테스트 계획 (TDD, 합성 데이터 · 네트워크 없음)",
    )
    stale_numbered_examples = (
        "5. 커버리지 80%+, ruff·mypy --strict clean.",
        "7. 커버리지 80%+ , `ruff`·`mypy` 통과.",
        "10. 커버리지 80%+, `ruff` clean, `mypy --strict` clean, 모든 파일 <800줄.",
    )
    current_numbered_examples = (
        "1. `python -m mimir.analyze --date D`가 저장된 데이터로 동작한다.",
        "2. 이벤트 2종 + analog 요약 + 엔진 단위/통합 테스트 통과.",
        f"5. {COMPLETED_DESIGN_SPEC_NUMBERED_CURRENT_VERIFICATION}",
    )

    for heading in stale_headings:
        assert COMPLETED_DESIGN_SPEC_TEST_HEADING_STALE_PATTERN.search(heading)
    for heading in current_headings:
        assert not COMPLETED_DESIGN_SPEC_TEST_HEADING_STALE_PATTERN.search(heading)
    for line in stale_numbered_examples:
        assert _has_stale_acceptance_verification_metadata(line)
    for line in current_numbered_examples:
        assert not _has_stale_acceptance_verification_metadata(line)

    for path in sorted(Path("docs/superpowers/specs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            status = _status_line(text)
        except StopIteration:
            continue
        if "구현 완료" not in status:
            continue

        in_completion_section = False
        for line in text.splitlines():
            if line.startswith("## "):
                if "테스트" in line:
                    assert not COMPLETED_DESIGN_SPEC_TEST_HEADING_STALE_PATTERN.search(line), (
                        f"{path} test heading carries stale fixed verification metadata: {line}"
                    )
                in_completion_section = any(
                    keyword in line
                    for keyword in COMPLETED_DESIGN_SPEC_COMPLETION_HEADING_KEYWORDS
                )
                continue

            if not in_completion_section:
                continue
            if not COMPLETED_DESIGN_SPEC_NUMBERED_ITEM_RE.match(line):
                continue

            if "README 테스트 배지와 docs health guard" in line:
                assert line.strip().endswith(
                    COMPLETED_DESIGN_SPEC_NUMBERED_CURRENT_VERIFICATION
                ), f"{path} uses non-canonical numbered current verification: {line}"
                continue

            assert not _has_stale_acceptance_verification_metadata(line), (
                f"{path} has stale numbered completion verification metadata: {line}"
            )
```

- [ ] **Step 2: Run the new test and verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_completed_design_spec_numbered_completion_criteria_use_current_metadata -q
```

Expected: FAIL before doc edits. The failure should point at at least one of:

- `docs/superpowers/specs/2026-05-31-analysis-design.md:150`
- `docs/superpowers/specs/2026-05-31-delivery-design.md:66`
- `docs/superpowers/specs/2026-05-31-historical-design.md:77`
- `docs/superpowers/specs/2026-05-31-collector-design.md:350`
- a numbered criterion containing `커버리지 80%+`, `ruff`, or `mypy`.

- [ ] **Step 3: Update affected design specs**

Apply these exact doc changes:

```markdown
docs/superpowers/specs/2026-05-31-analysis-design.md
- ## 9. 테스트 (TDD, 80%+)
+ ## 9. 테스트 전략 (TDD)
- 5. 커버리지 80%+, ruff·mypy --strict clean.
+ 5. 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.

docs/superpowers/specs/2026-05-31-delivery-design.md
- ## 7. 테스트(TDD, 80%+)
+ ## 7. 테스트 전략 (TDD)
- 5. 커버리지 80%+, ruff·mypy --strict clean.
+ 5. 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.

docs/superpowers/specs/2026-05-31-historical-design.md
- ## 8. 테스트(TDD, 80%+)
+ ## 8. 테스트 전략 (TDD)
- 5. 커버리지 80%+, ruff·mypy --strict clean.
+ 5. 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.

docs/superpowers/specs/2026-05-31-collector-design.md
- ## 15. 테스트 전략 (TDD, 80%+)
+ ## 15. 테스트 전략 (TDD)
- 7. 커버리지 80%+ , `ruff`·`mypy` 통과.
+ 7. 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.

docs/superpowers/specs/2026-06-13-signal-backtest-design.md
- 10. 커버리지 80%+, `ruff` clean, `mypy --strict` clean, 모든 파일 <800줄.
+ 10. 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다. 파일 크기 건전성은 발전 카탈로그의 anti-discovery 항목에서 별도 추적한다.
```

Do not change `docs/superpowers/specs/2026-05-31-collector-design.md:365`; the development-tool list remains legitimate.

- [ ] **Step 4: Verify GREEN for docs guard**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_completed_design_spec_numbered_completion_criteria_use_current_metadata -q
uv run pytest tests/test_readme_docs.py -q
```

Expected: new targeted test passes and the whole docs test file passes.

- [ ] **Step 5: Update README test counts**

Run:

```bash
uv run pytest --collect-only -q | tail -1
```

Expected after adding one test: `642 tests collected`.

Update the badges and test table rows in `README.md`, `README.ko.md`, and `README.zh.md` from `641` to `642`.

- [ ] **Step 6: Run focused and full verification**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q | tail -1
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected:

- `tests/test_readme_docs.py` passes.
- collection reports `642 tests collected`.
- full pytest passes.
- ruff passes.
- mypy passes.
- diff check is clean.

- [ ] **Step 7: Commit implementation**

Stage only intentional files:

```bash
git add tests/test_readme_docs.py \
  docs/superpowers/specs/2026-05-31-analysis-design.md \
  docs/superpowers/specs/2026-05-31-delivery-design.md \
  docs/superpowers/specs/2026-05-31-historical-design.md \
  docs/superpowers/specs/2026-05-31-collector-design.md \
  docs/superpowers/specs/2026-06-13-signal-backtest-design.md \
  README.md README.ko.md README.zh.md
git commit -m "test(docs): guard completed spec numbered verification"
```
