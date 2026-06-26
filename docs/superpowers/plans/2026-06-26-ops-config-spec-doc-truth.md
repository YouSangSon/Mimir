# OPS/Config Spec Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a docs health guard and update the remaining completed ops/config design specs so their completion metadata matches current implementation truth instead of stale fixed test counts.

**Architecture:** This is a docs-truth slice. The product/runtime implementation already exists; the change adds one targeted `tests/test_readme_docs.py` guard, then updates four completed design specs to use current verification wording and required implementation anchors. README EN/KO/ZH test counts are updated only after `pytest --collect-only` proves the new collected count.

**Tech Stack:** Python 3.14, pytest, markdown docs under `docs/superpowers/specs/`, README badges in `README.md`, `README.ko.md`, and `README.zh.md`.

## Global Constraints

- Do not edit runtime code for this slice unless the RED docs guard proves an implementation claim is false.
- Use TDD: add the failing docs guard first, run the targeted test, and capture RED before editing docs.
- Keep the slice scoped to `tests/test_readme_docs.py`, the four target spec docs, and README EN/KO/ZH test count updates if collection changes.
- Completed design specs must not claim stale fixed test counts in status lines.
- Completed design specs must not leave unchecked `- [ ]` items in acceptance sections.
- Current verification wording must point to README test badges and docs health guards, not historical suite sizes or historical coverage snapshots.
- Preserve design-history context. A spec may describe what the increment meant at the time, but its completion metadata must match current truth.
- Do not stage `uv.lock`, `CLAUDE.md`, `docs/superpowers/handoffs/`, or new `.superpowers/` scratch reports.
- Commit only the intentional plan/test/docs/README files with exact staging.

---

## File Structure

- Modify: `tests/test_readme_docs.py`
  - Add constants for the four target specs.
  - Add `test_ops_config_design_specs_match_current_completion_state()`.
- Modify: `docs/superpowers/specs/2026-06-16-github-actions-node24-design.md`
  - Replace stale status count/coverage wording.
  - Replace final acceptance gate wording with current docs-health wording.
- Modify: `docs/superpowers/specs/2026-06-16-pykrx-retry-policy-design.md`
  - Replace stale status count/coverage wording.
  - Replace final acceptance gate wording with current docs-health wording.
- Modify: `docs/superpowers/specs/2026-06-17-plugin-settings-namespace-design.md`
  - Replace stale status count/coverage wording.
  - Replace final acceptance gate wording with current docs-health wording.
- Modify: `docs/superpowers/specs/2026-06-18-sec-rss-ticker-input-design.md`
  - Replace stale status count/diff-check wording.
  - Add current truth about later off-by-default SEC ticker CIK mapping refresh/cache while preserving the original no-network resolver boundary.
  - Replace final acceptance gate wording with current docs-health wording.
- Modify: `README.md`, `README.ko.md`, `README.zh.md`
  - Update test badge/table counts to the count reported by `uv run pytest --collect-only -q` after the new guard is added. Expected value is probably one above `636`, but verify before editing.

---

### Task 1: Guard OPS/Config Completed Spec Truth

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-06-16-github-actions-node24-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-pykrx-retry-policy-design.md`
- Modify: `docs/superpowers/specs/2026-06-17-plugin-settings-namespace-design.md`
- Modify: `docs/superpowers/specs/2026-06-18-sec-rss-ticker-input-design.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

**Interfaces:**
- Consumes: existing helpers `_status_line(text)` and `_markdown_section(text, heading)` in `tests/test_readme_docs.py`.
- Consumes: existing README count guard `test_readme_test_badges_match_collected_pytest_count()`.
- Produces: one docs guard test named `test_ops_config_design_specs_match_current_completion_state()`.
- Produces: completed spec status wording containing `최신 검증은 README 테스트 배지와 docs health guard가 추적`.

- [ ] **Step 1: Add path constants for the four specs**

In `tests/test_readme_docs.py`, add these constants immediately after `SOURCES_CONFIG_CLI_VALIDATION_SPEC`:

```python
GITHUB_ACTIONS_NODE24_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-github-actions-node24-design.md"
)
PYKRX_RETRY_POLICY_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-pykrx-retry-policy-design.md"
)
PLUGIN_SETTINGS_NAMESPACE_SPEC = Path(
    "docs/superpowers/specs/2026-06-17-plugin-settings-namespace-design.md"
)
SEC_RSS_TICKER_INPUT_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-sec-rss-ticker-input-design.md"
)
```

- [ ] **Step 2: Add the failing docs guard**

In `tests/test_readme_docs.py`, add this test immediately after `test_cli_config_design_specs_match_current_completion_state()`:

```python
def test_ops_config_design_specs_match_current_completion_state() -> None:
    specs = {
        GITHUB_ACTIONS_NODE24_SPEC: (
            "## 6. 수용 기준",
            ("365 테스트", "coverage gate 클린"),
            (
                "`actions/checkout@v6`",
                "`actions/setup-python@v6`",
                "`.github/workflows/ci.yml`",
                "`.github/workflows/_pipeline.yml`",
                "`tests/test_workflows.py`",
                "`EXPECTED_WORKFLOW_ACTION_MAJORS`",
                "`ACTION_USES_RE`",
            ),
        ),
        PYKRX_RETRY_POLICY_SPEC: (
            "## 6. 수용 기준",
            ("368 테스트", "coverage gate 클린"),
            (
                "`PykrxSource`",
                "`DEFAULT_MAX_RETRIES = 2`",
                "`DEFAULT_BACKOFF = 0.5`",
                "`max_retries`",
                "`backoff`",
                "`sleep`",
                "`_fetch_ohlcv()`",
                "`Throttle.wait()`",
                "`FetchError`",
                "`pykrx OHLCV failed after`",
                "manifest",
            ),
        ),
        PLUGIN_SETTINGS_NAMESPACE_SPEC: (
            "## 7. 수용 기준",
            ("424 테스트", "coverage gate 클린"),
            (
                "`sources.plugins.<source_id>`",
                "`SourcesConfig.plugin_settings`",
                "`plugin_config()`",
                "`parse_plugin_config()`",
                "`_SourcesBlock.plugins`",
                "`dict[str, dict[str, Any]]`",
                "`build_sources()`",
                "`source plugin config`",
                "`sources.plugins.rss`",
                "`sources.plugins.sec_edgar`",
            ),
        ),
        SEC_RSS_TICKER_INPUT_SPEC: (
            "## 8. 수용 기준",
            ("478 tests", "diff check 통과"),
            (
                "`SecCompanyFilingFeed`",
                "`ticker`",
                "`cik`",
                "`_normalize_ticker()`",
                "`CIK=AAPL`",
                "`resolve_sec_company_filing_feeds()`",
                "`resolve_rss_feeds()`",
                "`duplicate RSS feed`",
                "네트워크를 호출하지 않는다",
                "`ticker_cik_map_refresh`",
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

- [ ] **Step 3: Run RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_ops_config_design_specs_match_current_completion_state -q
```

Expected before docs edits: FAIL. The first failure should report stale current truth in one of:

```text
docs/superpowers/specs/2026-06-16-github-actions-node24-design.md
docs/superpowers/specs/2026-06-16-pykrx-retry-policy-design.md
docs/superpowers/specs/2026-06-17-plugin-settings-namespace-design.md
docs/superpowers/specs/2026-06-18-sec-rss-ticker-input-design.md
```

Capture the command and relevant failing line in the worker report.

- [ ] **Step 4: Update D2 GitHub Actions Node24 spec**

In `docs/superpowers/specs/2026-06-16-github-actions-node24-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`actions/checkout@v6` + `actions/setup-python@v6` + workflow guard). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

Update section `## 2.2 현재 workflow 상태` so the table reflects the current implementation, not the old pre-change state:

```markdown
현재 repository의 직접 JavaScript action 사용은 두 곳이며, 둘 다 Node24 호환 major를 쓴다.

| 파일 | checkout | setup-python |
|---|---|---|
| `.github/workflows/ci.yml` | `actions/checkout@v6` | `actions/setup-python@v6` |
| `.github/workflows/_pipeline.yml` | `actions/checkout@v6` | `actions/setup-python@v6` |
```

In section `## 4.2 검증 테스트`, keep the existing `EXPECTED_WORKFLOW_ACTION_MAJORS` code block and add this sentence if not already present:

```markdown
`ACTION_USES_RE`는 대상 action의 `uses:` 줄을 찾아 major tag만 비교한다.
```

In `## 6. 수용 기준`, replace:

```markdown
- [x] ruff, mypy, pytest, coverage gate가 통과한다.
```

with:

```markdown
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 5: Update C3 pykrx retry policy spec**

In `docs/superpowers/specs/2026-06-16-pykrx-retry-policy-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`PykrxSource` retry/backoff + `FetchError` manifest surface). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

In section `## 4.1 생성자 옵션`, ensure these identifiers appear literally in prose or table text:

```markdown
현재 구현은 `DEFAULT_MAX_RETRIES = 2`, `DEFAULT_BACKOFF = 0.5`, `max_retries`, `backoff`, `sleep` 주입점을 유지한다.
```

In section `## 4.2 호출 흐름`, ensure these identifiers appear literally:

```markdown
구현은 `PykrxSource._fetch_ohlcv()`에서 각 시도마다 `Throttle.wait()`를 먼저 호출하고, 실패 시 `backoff * (2 ** attempt)`만큼 `sleep`한 뒤 재시도한다.
```

In section `## 4.3 실패 메시지`, ensure these identifiers appear literally:

```markdown
소진된 실패는 `FetchError`로 감싸며, orchestrator가 이 오류 문자열을 source failure manifest에 남긴다.
```

In `## 6. 수용 기준`, replace:

```markdown
- [x] 전체 ruff, mypy, pytest, coverage gate가 통과한다.
```

with:

```markdown
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 6: Update A3c plugin settings namespace spec**

In `docs/superpowers/specs/2026-06-17-plugin-settings-namespace-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`sources.plugins.<source_id>` namespace + plugin-owned pydantic validation helper). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

In section `## 4.2 SourcesConfig`, ensure the prose or code mentions:

```markdown
`SourcesConfig.plugin_settings`는 `dict[str, dict[str, Any]]` 형태로 plugin raw mapping을 보존한다.
```

In section `## 4.3 Parser`, ensure `_SourcesBlock.plugins` appears literally:

```markdown
현재 parser의 `_SourcesBlock.plugins` 필드는 `dict[str, dict[str, Any]] | None`이며, `sources.plugins.<source_id>` 아래 값이 mapping이 아니면 validation error가 난다.
```

In section `## 4.4 Builder warning`, ensure the current warning phrases appear literally:

```markdown
`build_sources()` 경로의 warning은 `source plugin config`로 시작한다. `sources.plugins.rss`처럼 configurable built-in source를 겨냥하면 `sources.rss`를 쓰라고 안내하고, `sources.plugins.sec_edgar`처럼 built-in이 plugin namespace를 읽지 않는 경우에는 built-in sources do not read `sources.plugins`라고 안내한다.
```

In `## 7. 수용 기준`, replace:

```markdown
- [x] ruff, mypy, pytest, coverage 80% gate를 통과한다.
```

with:

```markdown
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 7: Update R1h SEC RSS ticker input spec**

In `docs/superpowers/specs/2026-06-18-sec-rss-ticker-input-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`SecCompanyFilingFeed.ticker` + SEC Company Search Atom URL expansion). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

In `## 3. 목표`, keep the original resolver no-network goal and add this current-truth note after the goals list:

```markdown
후속 R1i/R1j에서 off-by-default `ticker_cik_map_refresh`와 local SEC mapping file cache path가 추가됐지만, 이 R1h resolver boundary는 그대로다. `resolve_sec_company_filing_feeds()`와 `resolve_rss_feeds()`는 설정을 URL로 조립할 뿐 네트워크를 호출하지 않는다.
```

In `## 7. 실패와 예외 처리`, ensure `duplicate RSS feed` remains literal and add a row if needed:

```markdown
| `ticker_cik_map_refresh`가 꺼져 있음 | 기본값. Resolver는 mapping file을 다운로드하지 않고 ticker token을 `CIK=` query parameter에 그대로 넣는다. |
```

In `## 8. 수용 기준`, replace:

```markdown
- [x] `uv run pytest tests/sources/test_rss_catalog.py tests/sources/test_config.py tests/core/test_builder.py -q`가 통과한다.
- [x] `uv run ruff check .`, `uv run mypy mimir`, `uv run pytest -q`가 통과한다.
```

with:

```markdown
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.
```

- [ ] **Step 8: Run GREEN for targeted docs guard**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_ops_config_design_specs_match_current_completion_state -q
```

Expected: PASS.

- [ ] **Step 9: Verify collected pytest count and update README counts**

Run:

```bash
uv run pytest --collect-only -q
```

Use the final collected count from stdout. If it is `637`, replace every README test badge/table count currently saying `636` with `637` in:

```text
README.md
README.ko.md
README.zh.md
```

If the count is not `637`, use the actual collected count. Do not guess.

- [ ] **Step 10: Run docs tests**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Expected: all tests in `tests/test_readme_docs.py` pass.

- [ ] **Step 11: Run focused repository checks**

Run:

```bash
uv run pytest tests/test_workflows.py tests/sources/test_pykrx_source.py tests/sources/test_config.py tests/sources/test_rss_catalog.py tests/core/test_builder.py -q
git diff --check
```

Expected: all selected tests pass and `git diff --check` prints nothing.

- [ ] **Step 12: Commit implementation**

Stage only:

```bash
git add tests/test_readme_docs.py \
  docs/superpowers/specs/2026-06-16-github-actions-node24-design.md \
  docs/superpowers/specs/2026-06-16-pykrx-retry-policy-design.md \
  docs/superpowers/specs/2026-06-17-plugin-settings-namespace-design.md \
  docs/superpowers/specs/2026-06-18-sec-rss-ticker-input-design.md \
  README.md README.ko.md README.zh.md
```

Then commit:

```bash
git commit -m "test(docs): guard ops config spec truth"
```

Do not stage `uv.lock`, `CLAUDE.md`, `docs/superpowers/handoffs/`, or `.superpowers/` reports.
