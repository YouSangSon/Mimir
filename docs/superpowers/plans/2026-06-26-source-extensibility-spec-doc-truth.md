# Source Extensibility Spec Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the completed A2/A3/A3b source extensibility design specs with current implementation truth and prevent stale completion metadata from returning.

**Architecture:** Add one focused docs health guard in `tests/test_readme_docs.py` for the three connected source extensibility design specs, then update only those specs and README test counts if the new guard changes the collected pytest count. Runtime code remains untouched because `mimir/core/macro_series.py`, `mimir/core/builder.py`, and `mimir/sources/config.py` already implement the relevant behavior.

**Tech Stack:** Python 3.12, pytest, markdown docs, existing Mimir docs health tests.

## Global Constraints

- Do not edit runtime code for this slice unless the RED docs guard proves a current implementation claim is false.
- Do not stage, edit, delete, or commit the unrelated untracked `uv.lock`.
- Do not stage or commit `.superpowers/` worker or reviewer reports.
- Keep changes scoped to `tests/test_readme_docs.py`, the three target design specs, and README EN/KO/ZH test counts if collection increases.
- Use TDD: add the failing docs health guard first, run it and observe the expected failure, then update docs.
- Preserve design-history context: the specs may explain what each increment did at the time, but the completed status lines must not claim stale fixed test counts.
- Completed design specs must not leave unchecked `- [ ]` acceptance criteria in their acceptance sections.
- Current verification wording for completed specs must point to README test badges and docs health guards, not hard-coded historical suite sizes.
- External actions are read-only by default; do not push or publish.

---

## File Structure

- Modify: `tests/test_readme_docs.py`
  - Add path constants for A2, A3, and A3b design specs.
  - Add one docs health guard that blocks stale fixed test-count status lines and checks current implementation terms.
- Modify: `docs/superpowers/specs/2026-06-16-macro-series-registry-design.md`
  - Replace the stale `현재 364 테스트` status phrase with current docs-health wording.
  - Keep A2's actual boundary: macro metadata registry and `analysis.macro_regime.rate_series`; A3/A3b are later increments.
- Modify: `docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md`
  - Replace the stale `현재 364 테스트` status phrase.
  - Document current `SourceSpec` truth, including `meta`, source id validation, secret/module gates, and the later `sources.plugins.<source_id>` namespace as follow-on context.
- Modify: `docs/superpowers/specs/2026-06-16-source-entry-points-design.md`
  - Replace the stale `397 테스트` status phrase.
  - Document current `mimir.sources` entry point truth, `load_source_specs()`, built-ins-before-plugin ordering, plugin settings namespace follow-on, and trust/sandbox boundary.
- Modify if collected count changes: `README.md`, `README.ko.md`, `README.zh.md`
  - Update tests badge and test table count to match `pytest --collect-only`.

## Current Implementation Evidence

- `mimir/core/macro_series.py` defines `EcosSeriesSpec`, `MacroSeriesMeta`, `DEFAULT_MACRO_RATE_SERIES`, `default_fred_series()`, `default_ecos_series_specs()`, `default_macro_rate_series()`, and `macro_series_cadences()`.
- `tests/core/test_macro_series.py` proves FRED/ECOS defaults, doctor macro cadence, and default macro rate-series all come from the registry.
- `mimir/sources/config.py` parses `analysis.macro_regime.rate_series` into `SourcesConfig.macro_regime_rate_series`.
- `mimir/analysis/builder.py` passes `cfg.macro_regime_rate_series` into `MacroRegimeSignal`.
- `mimir/core/builder.py` defines `SOURCE_ENTRY_POINT_GROUP = "mimir.sources"`, `SourceSpec`, `BUILTIN_SOURCE_SPECS`, `_load_entry_point_source_specs()`, `load_source_specs()`, `_build_sources_from_specs()`, and `build_sources(..., specs=None)`.
- `SourceSpec` currently includes `meta: SourceMeta | None = None`, which supports backfill preflight manifest metadata for registered-but-unavailable sources.
- `tests/core/test_builder.py` proves built-in source order, static metadata, duplicate id validation, secret gates, optional package gates, entry point loading, broken plugin skip logging, source id conflicts, built-in namespace warnings, and plugin config parsing through `sources.plugins.<source_id>`.

---

### Task 1: Source Extensibility Design Spec Truth Guard

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-06-16-macro-series-registry-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-source-entry-points-design.md`
- Modify if needed: `README.md`
- Modify if needed: `README.ko.md`
- Modify if needed: `README.zh.md`

**Interfaces:**
- Consumes: existing `_status_line(text: str) -> str` helper.
- Consumes: existing `_markdown_section(text: str, heading: str) -> str` helper.
- Produces: `test_source_extensibility_design_specs_match_current_completion_state()`.
- Produces: status lines in the three target specs that use `최신 검증은 README 테스트 배지와 docs health guard가 추적`.

- [ ] **Step 1: Add spec path constants**

In `tests/test_readme_docs.py`, add these constants near the existing design-spec path constants:

```python
MACRO_SERIES_REGISTRY_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-macro-series-registry-design.md"
)
DECLARATIVE_SOURCE_REGISTRATION_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md"
)
SOURCE_ENTRY_POINTS_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-source-entry-points-design.md"
)
```

- [ ] **Step 2: Write the failing docs health guard**

Add this test after `test_foundation_design_specs_match_current_completion_state()`:

```python
def test_source_extensibility_design_specs_match_current_completion_state() -> None:
    specs = {
        MACRO_SERIES_REGISTRY_SPEC: (
            "## 8. 수용 기준",
            ("현재 364 테스트", "coverage gate 클린"),
        ),
        DECLARATIVE_SOURCE_REGISTRATION_SPEC: (
            "## 8. 수용 기준",
            ("현재 364 테스트", "coverage gate 클린"),
        ),
        SOURCE_ENTRY_POINTS_SPEC: (
            "## 6. 수용 기준",
            ("397 테스트", "coverage gate 클린"),
        ),
    }

    texts = {path: path.read_text(encoding="utf-8") for path in specs}

    for path, (acceptance_heading, stale_phrases) in specs.items():
        text = texts[path]
        status = _status_line(text)
        acceptance = _markdown_section(text, acceptance_heading)

        assert "구현 완료" in status
        assert "최신 검증은 README 테스트 배지와 docs health guard가 추적" in status
        assert "- [ ]" not in acceptance, f"{path} still has unchecked acceptance"
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"

    a2 = texts[MACRO_SERIES_REGISTRY_SPEC]
    assert "`mimir/core/macro_series.py`" in a2
    assert "`DEFAULT_MACRO_RATE_SERIES`" in a2
    assert "`default_fred_series()`" in a2
    assert "`default_ecos_series_specs()`" in a2
    assert "`macro_series_cadences()`" in a2
    assert "`analysis.macro_regime.rate_series`" in a2
    assert "A3" in a2
    assert "A3b" in a2

    a3 = texts[DECLARATIVE_SOURCE_REGISTRATION_SPEC]
    assert "`SourceSpec`" in a3
    assert "`BUILTIN_SOURCE_SPECS`" in a3
    assert "`required_secret_attr`" in a3
    assert "`required_module`" in a3
    assert "`meta`" in a3
    assert "`sources.plugins.<source_id>`" in a3
    assert "doctor expected coverage" in a3

    a3b = texts[SOURCE_ENTRY_POINTS_SPEC]
    assert "`SOURCE_ENTRY_POINT_GROUP = \"mimir.sources\"`" in a3b
    assert "`_load_entry_point_source_specs()`" in a3b
    assert "`load_source_specs()`" in a3b
    assert "`build_sources(..., specs=...)`" in a3b
    assert "`sources.plugins.<source_id>`" in a3b
    assert "sandbox" in a3b.lower()
```

- [ ] **Step 3: Run the new test and verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_source_extensibility_design_specs_match_current_completion_state -q
```

Expected: FAIL because the three selected specs still carry stale fixed test-count status phrases and do not yet include all current implementation-truth terms.

- [ ] **Step 4: Update A2 status and current-state wording**

In `docs/superpowers/specs/2026-06-16-macro-series-registry-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`mimir/core/macro_series.py` + `analysis.macro_regime.rate_series`). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

Then add this paragraph near the end of section `## 9. A3와의 경계`:

```markdown
현재 구현에서는 A2의 registry가 `DEFAULT_MACRO_RATE_SERIES`, `default_fred_series()`, `default_ecos_series_specs()`, `default_macro_rate_series()`, `macro_series_cadences()`를 제공한다. A3는 `BUILTIN_SOURCE_SPECS`와 `SourceSpec`으로 built-in source 생성을 정리했고, A3b는 `mimir.sources` entry point로 외부 source plugin을 붙였다. 따라서 이 문서는 A2의 registry 경계를 설명하고, source construction/plugin 확장은 후속 A3/A3b 문서가 담당한다.
```

- [ ] **Step 5: Update A3 status and current-state wording**

In `docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`SourceSpec` built-in source table). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

In section `### 4.1 SourceSpec`, update the example dataclass so it includes current fields:

```python
@dataclass(frozen=True)
class SourceSpec:
    id: str
    factory: Callable[[Settings, SourcesConfig], Source]
    required_secret_attr: str | None = None
    required_secret_name: str | None = None
    required_module: str | None = None
    missing_module_hint: str | None = None
    meta: SourceMeta | None = None
```

Add this row to the field table:

```markdown
| `meta` | registered-but-unavailable source를 manifest/preflight에서 설명할 때 쓰는 정적 `SourceMeta` |
```

Add this paragraph to section `## 7. 문서 영향` after the existing required update list:

```markdown
후속 A3c 구현 후 외부 source plugin 설정은 `sources.plugins.<source_id>` namespace에 보존된다. Built-in source 설정은 여전히 `sources.rss`, `sources.fred`, `sources.ecos` 같은 typed block을 사용하고, `sources.plugins.rss`처럼 built-in id를 plugin namespace에 넣으면 builder가 warning한다. 이 후속 namespace는 A3의 built-in `SourceSpec` table을 바꾸지 않고 plugin factory가 자기 pydantic model로 설정을 검증하게 하는 확장이다.
```

- [ ] **Step 6: Update A3b status and current-state wording**

In `docs/superpowers/specs/2026-06-16-source-entry-points-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`mimir.sources` entry point + plugin `SourceSpec` loader). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

In section `### 4.1 entry-point group`, add this implementation note:

```markdown
현재 구현의 group 상수는 `SOURCE_ENTRY_POINT_GROUP = "mimir.sources"`이고, loader는 `_load_entry_point_source_specs()`다. 공개 helper `load_source_specs()`는 `BUILTIN_SOURCE_SPECS`를 먼저 두고 entry point `SourceSpec`들을 뒤에 붙인다. 테스트나 내부 조립에서는 `build_sources(..., specs=...)`로 직접 spec 목록을 주입할 수 있으며, 이 경로는 entry point discovery를 우회한다.
```

In section `## 7. 남는 한계`, replace the plugin settings paragraph with:

```markdown
Plugin별 설정 schema는 core가 소유하지 않는다. 후속 A3c 구현 후 raw 설정은 `sources.plugins.<source_id>` 아래에 보존되고, plugin factory가 `cfg.parse_plugin_config("acme_news", AcmeNewsConfig)`처럼 자기 pydantic model로 검증한다. Built-in source 설정은 이 namespace를 읽지 않으며, built-in id를 `sources.plugins`에 넣으면 builder가 warning한다.
```

- [ ] **Step 7: Run the focused docs guard and verify GREEN**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_source_extensibility_design_specs_match_current_completion_state -q
```

Expected: PASS.

- [ ] **Step 8: Update README test counts if needed**

Run:

```bash
uv run pytest --collect-only -q
```

If the collected count is `633`, update each of these files so both the badge and tests table row say `633`:

- `README.md`
- `README.ko.md`
- `README.zh.md`

Do not hard-code any count other than the actual collect-only output.

- [ ] **Step 9: Run docs test file**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Expected: PASS.

- [ ] **Step 10: Run full verification gates**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: all pass. Full pytest should report the collected count from Step 8.

- [ ] **Step 11: Commit the implementation**

Stage only the scoped files that changed. Do not stage `uv.lock` or `.superpowers/`.

```bash
git add \
  tests/test_readme_docs.py \
  docs/superpowers/specs/2026-06-16-macro-series-registry-design.md \
  docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md \
  docs/superpowers/specs/2026-06-16-source-entry-points-design.md \
  README.md README.ko.md README.zh.md
git commit -m "test(docs): guard source extensibility spec truth"
```

If a README file did not change because the count did not change, omit it from `git add`.

- [ ] **Step 12: Report task completion**

Write `.superpowers/sdd/source-extensibility-spec-doc-truth-task-1-report.md` with:

```markdown
# Source Extensibility Spec Doc Truth Task 1 Report

Status: DONE

## Changed Files

- `tests/test_readme_docs.py`
- `docs/superpowers/specs/2026-06-16-macro-series-registry-design.md`
- `docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md`
- `docs/superpowers/specs/2026-06-16-source-entry-points-design.md`
- `README.md` if count changed
- `README.ko.md` if count changed
- `README.zh.md` if count changed

## RED/GREEN Evidence

- RED: `uv run pytest tests/test_readme_docs.py::test_source_extensibility_design_specs_match_current_completion_state -q` failed before docs updates because stale fixed counts/current-truth terms were missing.
- GREEN: same focused test passed after docs updates.

## Verification

- `uv run pytest tests/test_readme_docs.py -q`
- `uv run pytest -q`
- `uv run ruff check .`
- `uv run mypy mimir`
- `git diff --check`

## Commit

- `<commit-hash> test(docs): guard source extensibility spec truth`

## Concerns

- None.
```
