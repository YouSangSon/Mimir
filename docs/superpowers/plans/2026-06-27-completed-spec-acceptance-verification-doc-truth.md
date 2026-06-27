# Completed Spec Acceptance Verification Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completed design specs must not keep stale acceptance-checklist verification bullets that claim fixed command, coverage, ruff, mypy, pytest, or diff-check state.

**Architecture:** Add one generic docs health guard in `tests/test_readme_docs.py` for checked acceptance bullets in completed design specs, then normalize the affected design specs to the existing README badge/docs health wording. Preserve historical design context and implementation facts; only current verification metadata changes.

**Tech Stack:** Python 3.14, pytest docs health tests, Markdown specs under `docs/superpowers/specs/`.

## Global Constraints

- Do not touch, stage, remove, or commit the pre-existing untracked `uv.lock`.
- Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` into this slice.
- Keep the broad goal active; do not mark it complete.
- Use TDD: add the failing docs health guard first, run the targeted test and observe RED, then update docs/tests.
- Scope is completed design-spec acceptance verification bullets only. Do not rewrite historical tech-spec verification tables in `docs/decisions/tech-spec/`.
- Preserve design-history context. A spec can describe original test strategy or historical implementation details, but checked acceptance/completion verification metadata must point at README test badges and docs health guards.
- Canonical checked acceptance verification bullet:

```markdown
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

- README EN/KO/ZH test counts must be updated if pytest collection changes.
- Run controller gates before ledger/handoff updates: `uv run pytest -q`, `uv run ruff check .`, `uv run mypy mimir`, and `git diff --check`.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `tests/test_readme_docs.py` | Add a generic guard that rejects stale verification metadata in checked acceptance bullets of completed design specs. Update the old R1c assertion that still expected a stale gate bullet. |
| `docs/superpowers/specs/*.md` | Replace only stale checked acceptance verification bullets with the canonical README/docs health bullet, removing duplicates when a canonical bullet is already present. |
| `README.md`, `README.ko.md`, `README.zh.md` | Update badge/table count only if pytest collection increases. |
| `.superpowers/sdd/progress.md` | Append completion after review and full gates pass. |
| `CLAUDE.md`, `docs/superpowers/handoffs/2026-06-26-claude-goal-handoff.md` | Refresh local continuation state after the slice, but do not stage into implementation commits. |
| `/Users/yousang/Desktop/obsidian/Projects/Mimir/Long/llm-wiki/index.md` and `log.md` | Refresh durable project memory after the slice. |

### Task 1: Completed Design-Spec Acceptance Verification Guard

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md`
- Modify: `docs/superpowers/specs/2026-06-13-typed-payload-design.md`
- Modify: `docs/superpowers/specs/2026-06-13-data-doctor-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-macro-series-registry-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-source-entry-points-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-news-mention-alias-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-default-news-aliases-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-backfill-manifest-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md`
- Modify: `docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md`
- Modify: `docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md`
- Modify: `docs/superpowers/specs/2026-06-18-cli-entrypoints-design.md`
- Modify: `docs/superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md`
- Modify: `docs/superpowers/specs/2026-06-18-sources-config-cli-validation-design.md`
- Modify if count changes: `README.md`, `README.ko.md`, `README.zh.md`

**Interfaces:**
- Consumes: `_status_line(text: str) -> str`, existing `COMPLETED_DESIGN_SPEC_STATUS_STALE_*` constants, and docs paths already declared in `tests/test_readme_docs.py`.
- Produces: `test_completed_design_spec_acceptance_verification_lines_use_current_metadata() -> None`, a docs health guard that scans all completed design specs.

- [ ] **Step 1: Add the failing docs health guard**

Add these constants near the completed status stale constants:

```python
COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION = (
    "- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다."
)
COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_TERMS = re.compile(
    r"(?<![\w.-])(?:ruff|mypy|pytest|coverage|cov)(?![\w.-])"
    r"|커버리지|diff[- ]check|uv\s+run|git\s+diff",
    re.IGNORECASE,
)
COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_OUTCOMES = re.compile(
    r"통과|passed|pass|gate|클린|clean|≥\s*80%",
    re.IGNORECASE,
)
```

Add this test after `test_completed_design_spec_status_lines_use_current_verification_metadata()`:

```python
def test_completed_design_spec_acceptance_verification_lines_use_current_metadata() -> None:
    stale_examples = (
        "- [x] ruff, mypy, pytest, coverage 80% gate가 통과한다.",
        "- [x] `uv run pytest tests/test_cli.py -q`가 통과한다.",
        "- [x] 네트워크 호출 0 · ruff · mypy strict 클린 · 커버리지 ≥ 80%.",
    )
    current_examples = (
        COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION,
        "- [x] **영업일 오탐 방지**: 금요일 종가가 최신, `now`=월요일 → DAILY 나이 = 1 영업일 → OK(오탐 없음).",
        "- [x] mypy strict 내로잉 헬퍼는 payload mismatch에서 예외를 낸다.",
    )

    for line in stale_examples:
        assert COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_TERMS.search(line)
        assert COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_OUTCOMES.search(line)

    for line in current_examples:
        if line == COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION:
            continue
        assert not (
            COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_TERMS.search(line)
            and COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_OUTCOMES.search(line)
        )

    for path in sorted(Path("docs/superpowers/specs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        status = _status_line(text)
        if "구현 완료" not in status:
            continue

        for line in text.splitlines():
            if not line.startswith("- [x]"):
                continue
            if "README 테스트 배지와 docs health guard" in line:
                assert line == COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION, (
                    f"{path} uses non-canonical current verification acceptance: {line}"
                )
                continue
            assert not (
                COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_TERMS.search(line)
                and COMPLETED_DESIGN_SPEC_ACCEPTANCE_VERIFICATION_OUTCOMES.search(line)
            ), f"{path} has stale acceptance verification metadata: {line}"
```

Also replace the existing stale R1c assertion:

```python
assert "- [x] ruff, mypy, pytest, coverage 80% gate가 통과한다." in r1c
```

with:

```python
assert COMPLETED_DESIGN_SPEC_ACCEPTANCE_CURRENT_VERIFICATION in r1c
```

- [ ] **Step 2: Run targeted docs test and verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_completed_design_spec_acceptance_verification_lines_use_current_metadata -q
```

Expected: FAIL because completed design specs still contain checked acceptance bullets such as `ruff, mypy, pytest, coverage 80% gate가 통과한다.` and backticked `uv run pytest ...` current-verification claims.

- [ ] **Step 3: Normalize stale acceptance verification bullets**

Replace each stale checked acceptance verification bullet with the canonical bullet. If a canonical bullet already appears immediately after the stale command bullet, remove the stale command bullet instead of duplicating the canonical bullet.

Use this exact canonical bullet:

```markdown
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

Affected stale bullets from the discovery scan:

```text
docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md:125
docs/superpowers/specs/2026-06-13-typed-payload-design.md:314
docs/superpowers/specs/2026-06-13-data-doctor-design.md:313
docs/superpowers/specs/2026-06-16-macro-series-registry-design.md:193
docs/superpowers/specs/2026-06-16-source-entry-points-design.md:146
docs/superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md:152
docs/superpowers/specs/2026-06-16-news-mention-alias-design.md:228
docs/superpowers/specs/2026-06-16-default-news-aliases-design.md:155
docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md:150
docs/superpowers/specs/2026-06-16-backfill-manifest-design.md:172
docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md:238
docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md:248
docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md:206
docs/superpowers/specs/2026-06-18-cli-entrypoints-design.md:141
docs/superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md:102
docs/superpowers/specs/2026-06-18-sources-config-cli-validation-design.md:129
```

- [ ] **Step 4: Run targeted docs test and collect count**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q
```

Expected after docs updates: `tests/test_readme_docs.py` passes. If collection reports `640`, update README EN/KO/ZH tests badge/table counts from `639` to `640`.

- [ ] **Step 5: Commit implementation**

Stage only intentional tracked files:

```bash
git add tests/test_readme_docs.py \
  docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md \
  docs/superpowers/specs/2026-06-13-typed-payload-design.md \
  docs/superpowers/specs/2026-06-13-data-doctor-design.md \
  docs/superpowers/specs/2026-06-16-macro-series-registry-design.md \
  docs/superpowers/specs/2026-06-16-source-entry-points-design.md \
  docs/superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md \
  docs/superpowers/specs/2026-06-16-news-mention-alias-design.md \
  docs/superpowers/specs/2026-06-16-default-news-aliases-design.md \
  docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md \
  docs/superpowers/specs/2026-06-16-backfill-manifest-design.md \
  docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md \
  docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md \
  docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md \
  docs/superpowers/specs/2026-06-18-cli-entrypoints-design.md \
  docs/superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md \
  docs/superpowers/specs/2026-06-18-sources-config-cli-validation-design.md \
  README.md README.ko.md README.zh.md
git commit -m "test(docs): guard completed spec acceptance verification"
```

Only include README files if their counts changed. Do not stage `CLAUDE.md`, `docs/superpowers/handoffs/`, `.superpowers/`, or `uv.lock`.

- [ ] **Step 6: Review and controller gates**

Run a task review against the plan commit and implementation commit. Fix Critical/Important findings and re-review.

Then run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
git status --short --branch
```

Expected: full pytest passes, ruff passes, mypy passes, diff check is clean, and only expected untracked continuation files plus `uv.lock` remain.

## Self-Review

- Spec coverage: The plan covers the discovered acceptance verification drift without changing runtime code or archived tech-spec verification tables.
- Placeholder scan: No `TBD`, `TODO`, or unspecified "write tests" steps remain.
- Type/signature consistency: The new pytest constants and test use existing `Path`, `re`, and `_status_line()` imports/helpers.
