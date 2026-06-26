# OPS RSS Visibility Spec Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a docs health guard and update the completed doctor HTML, SEC RSS, SEC structured RSS, and scheduled dashboard publication design specs so their completion metadata matches current implementation truth.

**Architecture:** This is a docs-truth slice. The runtime implementation already exists; the change adds one focused `tests/test_readme_docs.py` guard, updates four completed design specs to use current verification wording and implementation anchors, and updates README EN/KO/ZH test counts after pytest collection proves the new count.

**Tech Stack:** Python 3.14, pytest, pathlib-based Markdown checks, existing README docs health tests, existing Mimir doctor/report/RSS/workflow implementation.

## Global Constraints

- Work in-place on `main`; do not create a worktree for this slice because the repo handoff explicitly says to continue from this checkout.
- Do not touch, stage, remove, or commit the pre-existing untracked `uv.lock`.
- Do not stage or commit `CLAUDE.md`, `docs/superpowers/handoffs/`, or new `.superpowers/` scratch reports.
- Do not edit runtime code for this slice unless the RED docs guard proves a current implementation claim is false.
- Keep implementation scope to `tests/test_readme_docs.py`, the four target specs, and README EN/KO/ZH test count updates if collection changes.
- Use TDD: add the failing docs guard first, run the targeted test and observe RED, then update docs.
- Completed design specs must not claim stale fixed test counts or historical command-gate completion wording in completion metadata.
- Completed design specs must not leave unchecked `- [ ]` items in their acceptance sections.
- Current verification wording must point to README test badges and docs health guards, not historical suite sizes, coverage gates, or command lists.
- Preserve design-history context. Specs may describe what the increment meant at the time, but completion metadata must match current truth.
- Commit only intentional plan/test/docs/README files with exact staging.

---

## File Structure

- Modify `tests/test_readme_docs.py`: add constants for four design specs and one guard test after the existing OPS/config docs-truth guard.
- Modify `docs/superpowers/specs/2026-06-18-doctor-html-report-design.md`: replace stale status/verification wording and document current doctor HTML anchors.
- Modify `docs/superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md`: replace historical command acceptance wording and document current SEC company filing resolver anchors.
- Modify `docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md`: replace historical command acceptance wording and document current static catalog anchors.
- Modify `docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md`: replace historical command acceptance wording and document current workflow-test anchors.
- Modify `README.md`, `README.ko.md`, `README.zh.md` only if `uv run pytest --collect-only -q` reports a new collected-test count.

---

## Task 1: Guard OPS/RSS Visibility Design Spec Truth

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-06-18-doctor-html-report-design.md`
- Modify: `docs/superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md`
- Modify: `docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md`
- Modify: `docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md`
- Maybe modify: `README.md`
- Maybe modify: `README.ko.md`
- Maybe modify: `README.zh.md`

**Interfaces:**
- Consumes: existing `_status_line(text: str) -> str` and `_markdown_section(text: str, heading: str) -> str` helpers in `tests/test_readme_docs.py`.
- Consumes: existing README count guard `test_readme_test_badges_match_collected_pytest_count()`.
- Produces: a pytest guard named `test_ops_rss_visibility_design_specs_match_current_completion_state`.
- Produces: completed spec status wording containing `최신 검증은 README 테스트 배지와 docs health guard가 추적`.

- [ ] **Step 1: Write the failing docs guard**

Add these constants immediately after `SEC_RSS_TICKER_INPUT_SPEC` in `tests/test_readme_docs.py`:

```python
DOCTOR_HTML_REPORT_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-doctor-html-report-design.md"
)
SEC_EDGAR_RSS_PROVIDER_SPEC = Path(
    "docs/superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md"
)
SEC_STRUCTURED_RSS_CATALOG_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md"
)
SCHEDULED_DASHBOARD_PUBLICATION_SPEC = Path(
    "docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md"
)
```

Add this test immediately after `test_ops_config_design_specs_match_current_completion_state()`:

```python
def test_ops_rss_visibility_design_specs_match_current_completion_state() -> None:
    specs = {
        DOCTOR_HTML_REPORT_SPEC: (
            "## 6. 수용 기준",
            ("coverage gate", "diff-check가 통과한다"),
            (
                "`mimir/report/doctor_html.py`",
                "`render_doctor_html()`",
                "`mimir doctor --html <path>`",
                "`--lang en|ko|zh`",
                "`Finding.scope`",
                "`Finding.message`",
                "`Finding.severity`",
                "`doctor_cli.main()`",
            ),
        ),
        SEC_EDGAR_RSS_PROVIDER_SPEC: (
            "## 10. 수용 기준",
            (
                "uv run pytest tests/sources/test_rss_catalog.py "
                "tests/sources/test_config.py tests/sources/test_rss.py "
                "tests/core/test_builder.py -q",
                "uv run ruff check .",
                "uv run mypy mimir",
                "uv run pytest -q",
            ),
            (
                "`SecCompanyFilingFeed`",
                "`sources.rss.sec.company_filings`",
                "`resolve_sec_company_filing_feeds()`",
                "`resolve_rss_feeds()`",
                "`RssSource(user_agent=settings.sec_user_agent)`",
                "`MIMIR_SEC_USER_AGENT`",
                "`User-Agent`",
                "`browse-edgar`",
                "`duplicate RSS feed`",
                "네트워크를 호출하지 않는다",
            ),
        ),
        SEC_STRUCTURED_RSS_CATALOG_SPEC: (
            "## 9. 수용 기준",
            (
                "uv run pytest tests/sources/test_rss_catalog.py "
                "tests/sources/test_config.py -q",
                "uv run ruff check .",
                "uv run mypy mimir",
                "uv run pytest -q",
                "git diff --check",
            ),
            (
                "`RSS_CATALOG`",
                "`RssCatalogSelection`",
                "`resolve_rss_catalogs()`",
                "`resolve_rss_feeds()`",
                "`sec_structured_usgaap`",
                "`sec_structured_risk_return`",
                "`sec_structured_inline_xbrl`",
                "`sec_structured_all_xbrl`",
                "broad SEC/XBRL feed",
                "symbol-specific feed가 아니다",
                "네트워크를 호출하지 않는다",
            ),
        ),
        SCHEDULED_DASHBOARD_PUBLICATION_SPEC: (
            "## 7. 수용 기준",
            (
                "uv run pytest tests/test_workflows.py -q",
                "uv run ruff check .",
                "uv run mypy mimir",
                "uv run pytest -q",
            ),
            (
                "`PIPELINE_WORKFLOW`",
                "`test_reusable_pipeline_publishes_dashboard_before_commit()`",
                "`test_reusable_pipeline_does_not_add_doctor_hard_gate()`",
                "`Run dashboard`",
                "`python -m mimir.dashboard --data-root data --reports-root reports`",
                "`Run pipeline`",
                "`Commit data + reports`",
                "`mimir.doctor`",
                "`--strict`",
                "publish-first",
            ),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases, required_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"
        for phrase in required_phrases:
            assert phrase in text, f"{path} missing current truth: {phrase}"
```

- [ ] **Step 2: Run RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_ops_rss_visibility_design_specs_match_current_completion_state -q
```

Expected before docs edits: FAIL. The first failure should be a missing current verification phrase or stale command/coverage wording in one of the four target design specs, not a Python syntax/import error. Capture the command and relevant failure in the worker report.

- [ ] **Step 3: Update DCHTML doctor HTML design spec**

In `docs/superpowers/specs/2026-06-18-doctor-html-report-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`mimir doctor --html` + `render_doctor_html()` standalone report). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

In section `## 4.1 독립 renderer를 둔다`, ensure the implementation truth uses the exact current anchor names:

```markdown
현재 구현 파일은 `mimir/report/doctor_html.py`이고 공개 renderer는 `render_doctor_html()`이다. `doctor_cli.main()`은 `--html`이 있을 때 같은 `DoctorReport`를 이 renderer에 넘긴다.
```

In section `## 4.4 CLI 계약`, ensure the CLI contract appears literally:

```markdown
현재 CLI 계약은 `mimir doctor --html <path>`와 `--lang en|ko|zh`다.
```

In section `## 6. 수용 기준`, replace:

```markdown
- [x] ruff, mypy, pytest, coverage gate, diff-check가 통과한다.
```

with:

```markdown
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 4: Update R1f SEC EDGAR RSS provider design spec**

In `docs/superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`SecCompanyFilingFeed` + SEC Company Search Atom resolver). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

In section `## 6. 아키텍처`, ensure the current implementation anchors appear literally:

```markdown
현재 model은 `SecCompanyFilingFeed`이며 설정 경로는 `sources.rss.sec.company_filings`다. Resolver는 `resolve_sec_company_filing_feeds()`를 통해 SEC company filing entries를 `RssFeed` 목록으로 확장하고, 최종 조립은 `resolve_rss_feeds()`가 catalog/manual feed와 같은 중복 정책으로 처리한다.
```

In section `## 8. 운영 정책`, preserve the no-network resolver boundary and ensure these anchors appear literally:

```markdown
Fetch 시점의 SEC RSS 요청은 `RssSource(user_agent=settings.sec_user_agent)`가 담당하며, `MIMIR_SEC_USER_AGENT` 값이 `User-Agent` header로 전달된다.
```

In section `## 10. 수용 기준`, replace the two historical command bullets:

```markdown
- [x] `uv run pytest tests/sources/test_rss_catalog.py tests/sources/test_config.py tests/sources/test_rss.py tests/core/test_builder.py -q`가 통과한다.
- [x] `uv run ruff check .`, `uv run mypy mimir`, `uv run pytest -q`가 통과한다.
```

with:

```markdown
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 5: Update R1g SEC structured RSS catalog design spec**

In `docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`RSS_CATALOG` SEC structured disclosure ids). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

In section `## 5. 아키텍처`, ensure the current implementation anchors appear literally:

```markdown
현재 구현은 `RSS_CATALOG`의 정적 entries와 `RssCatalogSelection` model을 사용한다. `resolve_rss_catalogs()`는 catalog id를 `RssFeed`로 확장하고, `resolve_rss_feeds()`는 catalog/manual/SEC company filing feed를 같은 중복 정책으로 조립한다.
```

In section `## 4. Catalog ID 계약`, keep all four ids and ensure this phrase appears:

```markdown
이 항목들은 broad SEC/XBRL feed이며 symbol-specific feed가 아니다.
```

In section `## 9. 수용 기준`, replace the two historical command bullets:

```markdown
- [x] `uv run pytest tests/sources/test_rss_catalog.py tests/sources/test_config.py -q`가 통과한다.
- [x] `uv run ruff check .`, `uv run mypy mimir`, `uv run pytest -q`, `git diff --check`가 통과한다.
```

with:

```markdown
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 6: Update OPS1 scheduled dashboard publication design spec**

In `docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`_pipeline.yml` scheduled dashboard publish). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

In section `## 4.4 테스트 설계`, ensure the current test anchors appear literally:

```markdown
현재 guard는 `PIPELINE_WORKFLOW`를 읽는 `test_reusable_pipeline_publishes_dashboard_before_commit()`와 `test_reusable_pipeline_does_not_add_doctor_hard_gate()`다.
```

In section `## 4.3 왜 hard gate를 넣지 않는가`, ensure this exact summary appears:

```markdown
이 문서에서 고정하는 정책은 publish-first다. `Run dashboard`는 `Run pipeline` 뒤와 `Commit data + reports` 앞에 오지만, `_pipeline.yml`은 `mimir.doctor`나 `--strict`를 직접 실행하지 않는다.
```

In section `## 7. 수용 기준`, replace the two historical command bullets:

```markdown
- [x] `uv run pytest tests/test_workflows.py -q`가 통과한다.
- [x] `uv run ruff check .`, `uv run mypy mimir`, `uv run pytest -q`가 통과한다.
```

with:

```markdown
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 7: Run the targeted guard and verify GREEN**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_ops_rss_visibility_design_specs_match_current_completion_state -q
```

Expected: PASS.

- [ ] **Step 8: Run collect-only and update README test counts if needed**

Run:

```bash
uv run pytest --collect-only -q
```

Expected: the collected test count increases by one from the current `637`. If the output reports `638 tests collected`, update these six locations:

```text
README.md tests badge
README.md Tests table row
README.ko.md tests badge
README.ko.md 테스트 table row
README.zh.md tests badge
README.zh.md 测试 table row
```

Use the exact collected count from the command, not an assumption.

- [ ] **Step 9: Run focused docs tests**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Expected: all README/docs health tests pass.

- [ ] **Step 10: Commit the implementation**

Before committing:

```bash
git status --short --branch
git diff -- tests/test_readme_docs.py docs/superpowers/specs/2026-06-18-doctor-html-report-design.md docs/superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md README.md README.ko.md README.zh.md
```

Stage exactly:

```bash
git add tests/test_readme_docs.py \
  docs/superpowers/specs/2026-06-18-doctor-html-report-design.md \
  docs/superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md \
  docs/superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md \
  docs/superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md \
  README.md README.ko.md README.zh.md
git commit -m "test(docs): guard ops rss visibility spec truth"
```

- [ ] **Step 11: Run controller gates after review approval**

The controller runs these after SDD review is approved:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: all pass.

---

## Self-Review

- Spec coverage: The plan covers the four unguarded completed design specs found by the rescan: DCHTML, R1f-SEC, R1g-SEC-STRUCTURED, and OPS1.
- Placeholder scan: No TBD/TODO placeholders remain; exact paths, test code, commands, and replacement snippets are included.
- Type/name consistency: The guard uses existing helpers `_status_line` and `_markdown_section`; new constants follow existing `*_SPEC` naming.
