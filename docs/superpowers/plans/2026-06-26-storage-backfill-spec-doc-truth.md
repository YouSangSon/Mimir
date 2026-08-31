# Storage Backfill Spec Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the completed macro revision, backfill manifest, and backfill preflight design specs with current implementation truth and prevent stale completion metadata from returning.

**Architecture:** Add one focused docs health guard in `tests/test_readme_docs.py` for the three connected storage/backfill design specs, then update only those specs and README test counts if the new guard changes the collected pytest count. Runtime code remains untouched because `mimir/storage/policy.py`, `mimir/storage/jsonl_store.py`, `mimir/backfill.py`, and their tests already implement the relevant behavior.

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
- The BF-MANIFEST spec must explicitly note that BF-PREFLIGHT later superseded its original registered-unavailable preflight gap; only truly unknown source ids still skip manifest writes.
- External actions are read-only by default; do not push or publish.

---

## File Structure

- Modify: `tests/test_readme_docs.py`
  - Add path constants for `MACRO-LWW`, `BF-MANIFEST`, and `BF-PREFLIGHT` design specs.
  - Add one docs health guard that blocks stale fixed test-count status lines, unchecked acceptance criteria, and stale BF-MANIFEST preflight wording.
- Modify: `docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md`
  - Replace the stale `407 테스트` status phrase with current docs-health wording.
  - Document current storage policy implementation terms: `append_overwrite_enabled`, `OVERWRITE_ON_APPEND_DATASETS`, `Dataset.MACRO`, `JsonlStore.append(overwrite=True)`, `_same_stored_record`, and `captured_at` no-op behavior.
- Modify: `docs/superpowers/specs/2026-06-16-backfill-manifest-design.md`
  - Replace the stale `368 테스트` status phrase with current docs-health wording.
  - Update the old unknown/unavailable boundary so it points to the later BF-PREFLIGHT behavior for registered unavailable sources.
- Modify: `docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md`
  - Replace the stale `499 테스트` status phrase with current docs-health wording.
  - Document current implementation terms: `SourceSpec(meta=...)`, `load_source_specs()`, `build_sources(settings, runtime.source_config, specs=specs)`, `_preflight_unavailable_error()`, `_write_failure_manifest()`, exact unavailable reasons, and unknown-source boundary.
- Modify if collected count changes: `README.md`, `README.ko.md`, `README.zh.md`
  - Update tests badge and test table count to match `pytest --collect-only`.

## Current Implementation Evidence

- `mimir/storage/policy.py` defines `OVERWRITE_ON_APPEND_DATASETS = frozenset({Dataset.MACRO})` and `append_overwrite_enabled(dataset)`.
- `mimir/storage/jsonl_store.py` implements `JsonlStore.append(..., overwrite=True)`, `_append_overwrite()`, `_same_stored_record()`, and preserves the original `captured_at` when only capture time changes.
- `mimir/core/orchestrator.py` and `mimir/backfill.py` both call `append_overwrite_enabled(source.meta.dataset)`.
- `mimir/backfill.py` creates `Manifest(root=data_root)` before source lookup, loads specs with `load_source_specs()`, builds sources with `build_sources(settings, runtime.source_config, specs=specs)`, and writes failures through `_write_failure_manifest()`.
- `mimir/backfill.py` keeps `SystemExit("unknown or unavailable source: <id>")` for the user-facing boundary, but writes `ok=false` manifest records for registered unavailable sources when `SourceSpec.meta` exists.
- `tests/storage/test_jsonl_store.py`, `tests/core/test_orchestrator.py`, `tests/core/test_builder.py`, and `tests/test_backfill.py` cover the storage policy, macro overwrite behavior, backfill success/runtime failure manifests, registered unavailable preflight manifests, optional-package manifests, and unknown-source no-manifest boundary.

---

### Task 1: Storage and Backfill Design Spec Truth Guard

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-backfill-manifest-design.md`
- Modify: `docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md`
- Modify if needed: `README.md`
- Modify if needed: `README.ko.md`
- Modify if needed: `README.zh.md`

**Interfaces:**
- Consumes: existing `_status_line(text: str) -> str` helper.
- Consumes: existing `_markdown_section(text: str, heading: str) -> str` helper.
- Produces: `test_storage_backfill_design_specs_match_current_completion_state()`.
- Produces: status lines in the three target specs that use `최신 검증은 README 테스트 배지와 docs health guard가 추적`.

- [ ] **Step 1: Add spec path constants**

In `tests/test_readme_docs.py`, add these constants near the existing design-spec path constants:

```python
MACRO_REVISION_POLICY_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md"
)
BACKFILL_MANIFEST_SPEC = Path(
    "docs/superpowers/specs/2026-06-16-backfill-manifest-design.md"
)
BACKFILL_PREFLIGHT_MANIFEST_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md"
)
```

- [ ] **Step 2: Write the failing docs health guard**

Add this test after `test_source_extensibility_design_specs_match_current_completion_state()`:

```python
def test_storage_backfill_design_specs_match_current_completion_state() -> None:
    specs = {
        MACRO_REVISION_POLICY_SPEC: (
            "## 7. 수용 기준",
            ("407 테스트", "coverage gate 클린"),
        ),
        BACKFILL_MANIFEST_SPEC: (
            "## 6. 수용 기준",
            (
                "368 테스트",
                "coverage gate 클린",
                "secret/package gate 때문에 사용할 수 없는 경우에는 현재처럼",
            ),
        ),
        BACKFILL_PREFLIGHT_MANIFEST_SPEC: (
            "## 6. 수용 기준",
            ("499 테스트", "coverage gate 클린"),
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

    macro = texts[MACRO_REVISION_POLICY_SPEC]
    assert "`append_overwrite_enabled(dataset)`" in macro
    assert "`OVERWRITE_ON_APPEND_DATASETS`" in macro
    assert "`Dataset.MACRO`" in macro
    assert "`JsonlStore.append(overwrite=True)`" in macro
    assert "`_same_stored_record()`" in macro
    assert "`captured_at`" in macro
    assert "first-write-wins" in macro
    assert "last-write-wins" in macro

    manifest = texts[BACKFILL_MANIFEST_SPEC]
    assert "`Manifest(root=data_root)`" in manifest
    assert "`SourceResult`" in manifest
    assert "`_write_failure_manifest()`" in manifest
    assert "`append_overwrite_enabled(source.meta.dataset)`" in manifest
    assert "BF-PREFLIGHT" in manifest
    assert "registered-unavailable" in manifest
    assert "unknown source id" in manifest

    preflight = texts[BACKFILL_PREFLIGHT_MANIFEST_SPEC]
    assert "`SourceSpec(meta=...)`" in preflight
    assert "`load_source_specs()`" in preflight
    assert "`build_sources(settings, runtime.source_config, specs=specs)`" in preflight
    assert "`_preflight_unavailable_error()`" in preflight
    assert "`_write_failure_manifest()`" in preflight
    assert "`STOOQ_API_KEY is not set`" in preflight
    assert "`package not installed (pip install -e '.[kr]')`" in preflight
    assert "unknown source id" in preflight
    assert "manifest 없이 argument error" in preflight
```

- [ ] **Step 3: Run the new test and verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_storage_backfill_design_specs_match_current_completion_state -q
```

Expected: FAIL because the three selected specs still carry stale fixed test-count status phrases, and BF-MANIFEST still contains stale registered-unavailable preflight wording.

- [ ] **Step 4: Update MACRO-LWW status and current-state wording**

In `docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`macro` source last-write-wins + source dataset별 저장 정책). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

Add this paragraph after section `### 4.3 overwrite 저장 건수는 변경된 레코드를 센다`:

```markdown
현재 구현에서 정책은 `mimir/storage/policy.py`의 `OVERWRITE_ON_APPEND_DATASETS`와 `append_overwrite_enabled(dataset)`에 있다. 현재 overwrite append 대상은 `Dataset.MACRO`뿐이며, source 수집과 backfill은 모두 `append_overwrite_enabled(source.meta.dataset)`로 같은 규칙을 쓴다. 실제 병합은 `JsonlStore.append(overwrite=True)`의 `_append_overwrite()` 경로에서 수행되고, `_same_stored_record()`가 `captured_at`만 다른 replay를 no-op으로 판정해 최초 capture time을 보존한다.
```

- [ ] **Step 5: Update BF-MANIFEST status and supersession boundary**

In `docs/superpowers/specs/2026-06-16-backfill-manifest-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`backfill` success/failure manifest recording). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

Replace section `### 4.3 unknown source는 manifest에 쓰지 않는다` with:

```markdown
### 4.3 unknown source와 registered-unavailable source의 현재 경계

BF-MANIFEST 당시에는 `source_id`가 build 결과에 없으면 `SystemExit("unknown or unavailable source: ...")`만 올리고 manifest를 쓰지 않았다. 후속 BF-PREFLIGHT 구현 후 현재 경계는 더 좁다.

현재 구현에서 registered-unavailable source는 BF-PREFLIGHT가 `ok=false` manifest로 기록한다. 예를 들어 `stooq`이 등록되어 있지만 `STOOQ_API_KEY`가 없거나, `pykrx`가 등록되어 있지만 optional package가 없으면 zero-count failure manifest를 남긴 뒤 기존 `SystemExit("unknown or unavailable source: <id>")`를 유지한다.

반대로 진짜 unknown source id는 여전히 manifest 없이 argument error로 끝난다. 이 경우에는 registered `SourceSpec.meta`가 없어 `RunRecord.cadence`에 넣을 신뢰 가능한 cadence가 없기 때문이다.
```

Add this paragraph to section `### 4.1 성공 경로` after the `return stored` code block:

```markdown
현재 `run_backfill()`은 저장 시 `append_overwrite_enabled(source.meta.dataset)`를 사용한다. 따라서 BF-MANIFEST의 `stored`는 source dataset별 저장 정책과 같은 의미를 갖는다. `macro` source는 `JsonlStore.append(overwrite=True)` 경로를 통해 개정 payload를 반영하고, `prices`/`filings`/`news`는 first-write-wins로 dedup된다.
```

Add this paragraph to section `### 4.2 실패 경로` after the failure code block:

```markdown
현재 구현은 runtime failure와 BF-PREFLIGHT preflight failure 모두 작은 helper인 `_write_failure_manifest()`로 같은 `SourceResult` shape를 쓴다. Manifest schema는 여전히 `SourceResult`와 `RunRecord`를 그대로 사용하며, `mode`, `phase`, `duration` 같은 필드는 추가하지 않았다.
```

- [ ] **Step 6: Update BF-PREFLIGHT status and current-state wording**

In `docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md`, replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`backfill` registered-unavailable preflight failure manifest). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

In section `### 4.3 backfill preflight failure를 manifest에 쓴다`, replace the current code block with:

```python
manifest = Manifest(root=data_root)
specs = load_source_specs()
built_sources = build_sources(settings, runtime.source_config, specs=specs)
sources = {s.meta.id: s for s in built_sources}
```

Add this paragraph after the bullet list in section `### 4.3 backfill preflight failure를 manifest에 쓴다`:

```markdown
현재 구현은 `_source_spec_for_id()`로 requested id의 `SourceSpec`를 찾고, `_preflight_unavailable_error()`로 비밀값 없는 원인을 만든 뒤 `_write_failure_manifest()`를 호출한다. 이 경로는 `SourceSpec(meta=...)`가 있는 registered source에서만 manifest를 쓴다. `SourceSpec.meta`가 없는 plugin이나 진짜 unknown source id는 신뢰 가능한 cadence가 없으므로 manifest 없이 argument error로 남는다.
```

In section `### 4.5 preflight error는 원인을 담되 secret 값은 담지 않는다`, ensure the exact examples remain:

```markdown
| missing secret | `STOOQ_API_KEY is not set` |
| missing optional module | `package not installed (pip install -e '.[kr]')` |
```

Add this sentence at the end of section `## 7. 남는 한계`:

```markdown
이 제한은 현재 구현에서도 유지된다. 즉, unknown source id와 `SourceSpec(meta=...)`가 없는 plugin unavailable은 manifest 없이 argument error로 남는다.
```

- [ ] **Step 7: Run the focused docs guard and verify GREEN**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_storage_backfill_design_specs_match_current_completion_state -q
```

Expected: PASS.

- [ ] **Step 8: Update README test counts if needed**

Run:

```bash
uv run pytest --collect-only -q
```

If the collected count is `634`, update each of these files so both the badge and tests table row say `634`:

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
  docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md \
  docs/superpowers/specs/2026-06-16-backfill-manifest-design.md \
  docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md \
  README.md README.ko.md README.zh.md
git commit -m "test(docs): guard storage backfill spec truth"
```

If a README file did not change because the count did not change, omit it from `git add`.

- [ ] **Step 12: Report task completion**

Write `.superpowers/sdd/storage-backfill-spec-doc-truth-task-1-report.md` with:

```markdown
# Storage Backfill Spec Doc Truth Task 1 Report

Status: DONE

## Changed Files

- `tests/test_readme_docs.py`
- `docs/superpowers/specs/2026-06-16-macro-revision-policy-design.md`
- `docs/superpowers/specs/2026-06-16-backfill-manifest-design.md`
- `docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md`
- `README.md` if count changed
- `README.ko.md` if count changed
- `README.zh.md` if count changed

## RED/GREEN Evidence

- RED: `uv run pytest tests/test_readme_docs.py::test_storage_backfill_design_specs_match_current_completion_state -q` failed before docs updates because stale fixed counts/current-truth terms were missing.
- GREEN: same focused test passed after docs updates.

## Verification

- `uv run pytest tests/test_readme_docs.py -q`
- `uv run pytest -q`
- `uv run ruff check .`
- `uv run mypy mimir`
- `git diff --check`

## Commit

- `<commit-hash> test(docs): guard storage backfill spec truth`

## Concerns

- None.
```
