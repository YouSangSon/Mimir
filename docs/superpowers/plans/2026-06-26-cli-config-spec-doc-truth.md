# CLI Config Spec Doc Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the completed CLI, dotenv autoload, and `sources.yaml` CLI-validation design specs match current implementation truth and add a docs health guard that prevents the stale fixed-count claims from returning.

**Architecture:** This is a docs-truth slice. It adds one focused test in `tests/test_readme_docs.py` that reads the three completed design specs as documentation artifacts, rejects stale historical status/count/coverage claims, and asserts the current code contracts are documented. Then it updates only the three specs plus README test badges/counts if pytest collection increases.

**Tech Stack:** Python 3.14, pytest, pathlib-based Markdown checks, existing README docs health tests, existing Mimir CLI/config modules.

## Global Constraints

- Work in-place on `main`; do not create a worktree for this slice because the repo handoff explicitly says to continue from this checkout.
- Do not touch, stage, remove, or commit the pre-existing untracked `uv.lock`.
- Do not stage or commit new `.superpowers/` scratch files.
- Keep implementation scope to `tests/test_readme_docs.py`, the three target specs, and README EN/KO/ZH test counts if collection changes.
- Do not edit runtime code unless the RED docs guard proves a current documentation claim is false.
- Use TDD: add the failing docs guard first, run the targeted test and observe RED, then update docs.
- Completed design specs must not claim stale fixed test counts in status lines.
- Completed design specs must not leave unchecked `- [ ]` items in their acceptance sections.
- Current verification wording must point to README test badges and docs health guards, not historical suite sizes or coverage-gate snapshots.
- Preserve design-history context. Specs may describe what the increment meant at the time, but completion metadata must match current truth.

---

## File Structure

- Modify `tests/test_readme_docs.py`: add constants for the three design specs and one guard test after the existing news/RSS docs-truth guard.
- Modify `docs/superpowers/specs/2026-06-18-cli-entrypoints-design.md`: replace stale status/count/coverage metadata and document current `mimir.cli` + `[project.scripts]` truth.
- Modify `docs/superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md`: replace stale status/count/coverage metadata and document current `Settings.from_env(env=None)` runtime dotenv behavior.
- Modify `docs/superpowers/specs/2026-06-18-sources-config-cli-validation-design.md`: replace stale status/count/coverage metadata and document current `RuntimeSourcesConfig`, path-resolution, CLI list, and doctor validation truth.
- Modify `README.md`, `README.ko.md`, `README.zh.md` only if `uv run pytest --collect-only -q` reports a new collected-test count.

## Task 1: Guard CLI/Config Design Spec Truth

**Files:**
- Modify: `tests/test_readme_docs.py`
- Modify: `docs/superpowers/specs/2026-06-18-cli-entrypoints-design.md`
- Modify: `docs/superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md`
- Modify: `docs/superpowers/specs/2026-06-18-sources-config-cli-validation-design.md`
- Maybe modify: `README.md`
- Maybe modify: `README.ko.md`
- Maybe modify: `README.zh.md`

**Interfaces:**
- Consumes: existing `_status_line(text: str) -> str` and `_markdown_section(text: str, heading: str) -> str` helpers in `tests/test_readme_docs.py`.
- Produces: a pytest guard named `test_cli_config_design_specs_match_current_completion_state`.

- [ ] **Step 1: Write the failing docs guard**

Add these constants near the other completed design-spec constants:

```python
CLI_ENTRYPOINTS_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-cli-entrypoints-design.md"
)
DOTENV_CLI_AUTOLOAD_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md"
)
SOURCES_CONFIG_CLI_VALIDATION_SPEC = Path(
    "docs/superpowers/specs/2026-06-18-sources-config-cli-validation-design.md"
)
```

Add this test after `test_news_rss_design_specs_match_current_completion_state`:

```python
def test_cli_config_design_specs_match_current_completion_state() -> None:
    specs = {
        CLI_ENTRYPOINTS_SPEC: (
            "## 8. 수용 기준",
            ("484 tests", "97% coverage", "coverage gate"),
            (
                "`mimir/cli.py`",
                "`COMMANDS`",
                "`_help_text()`",
                "`mimir <command>`",
                "`[project.scripts]`",
                '`mimir = "mimir.cli:main"`',
                '`mimir.doctor = "mimir.doctor.doctor_cli:main"`',
                "`mimir.collect`",
                "`python -m mimir.collect`",
                "`[mimir] unknown command:`",
            ),
        ),
        DOTENV_CLI_AUTOLOAD_SPEC: (
            "## 8. 수용 기준",
            ("492 tests", "98% coverage", "coverage gate"),
            (
                "`Settings.from_env(env=None)`",
                "`load_dotenv(find_dotenv(usecwd=True), override=False)`",
                "`env={...}`",
                "`override=False`",
                "`run_collect`",
                "`run_pipeline`",
                "`run_deliver`",
                "`run_backfill`",
                "`Settings.from_env(env)`",
            ),
        ),
        SOURCES_CONFIG_CLI_VALIDATION_SPEC: (
            "## 8. 수용 기준",
            ("495 tests", "98% coverage", "coverage gate"),
            (
                "`load_validated_sources_config()`",
                "`parse_runtime_sources_config()`",
                "`RuntimeSourcesConfig`",
                "`_resolve_sources_config_paths()`",
                "`report_invalid_sources()`",
                "`[mimir] invalid sources.yaml:`",
                "`SourcesConfigError`",
                "`collect`, `run`, `backfill`, `analyze`, `deliver`, `dashboard`, `doctor`",
                "`history`는 `sources.yaml`을 읽지 않는다",
                "`doctor_cli.main()`",
                "HTML 파일을 쓰기 전",
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

- [ ] **Step 2: Run the targeted test and verify RED**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_cli_config_design_specs_match_current_completion_state -q
```

Expected: FAIL. The failure must be due to stale status lines such as `484 tests · 97% coverage`, `492 tests · 98% coverage`, or `495 tests · 98% coverage`, not a syntax/import error.

- [ ] **Step 3: Update the CLI entrypoints design spec**

In `docs/superpowers/specs/2026-06-18-cli-entrypoints-design.md`:

- Replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`mimir/cli.py` + `[project.scripts]` console scripts). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

- Update implementation truth so it explicitly mentions:
  - `mimir/cli.py`
  - `COMMANDS`
  - `_help_text()`
  - `mimir <command>`
  - `[project.scripts]`
  - `mimir = "mimir.cli:main"`
  - `mimir.doctor = "mimir.doctor.doctor_cli:main"`
  - dotted aliases such as `mimir.collect`
  - module fallback such as `python -m mimir.collect`
  - unknown-command stderr prefix `[mimir] unknown command:` and exit code `2`

- Keep all acceptance criteria checked, but replace historical suite/coverage wording with README badge/docs health wording.

- [ ] **Step 4: Update the dotenv autoload design spec**

In `docs/superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md`:

- Replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`Settings.from_env(env=None)` runtime `.env` autoload). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

- Update implementation truth so it explicitly mentions:
  - `Settings.from_env(env=None)`
  - `load_dotenv(find_dotenv(usecwd=True), override=False)`
  - explicit `env={...}` injection bypasses dotenv loading
  - real env vars win because `override=False`
  - runtime functions `run_collect`, `run_pipeline`, `run_deliver`, and `run_backfill`
  - those runtime functions call `Settings.from_env(env)` and CLI `main()` paths omit `env`, preserving the default `env=None` path

- Keep all acceptance criteria checked, but replace historical suite/coverage wording with README badge/docs health wording.

- [ ] **Step 5: Update the sources config CLI validation design spec**

In `docs/superpowers/specs/2026-06-18-sources-config-cli-validation-design.md`:

- Replace the status line with:

```markdown
> **상태**: ✅ 구현 완료 (`load_validated_sources_config()` + CLI-friendly `sources.yaml` validation). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
```

- Update implementation truth so it explicitly mentions:
  - `load_validated_sources_config()`
  - returned `RuntimeSourcesConfig`
  - `parse_runtime_sources_config()`
  - `_resolve_sources_config_paths()`
  - `report_invalid_sources()`
  - `[mimir] invalid sources.yaml:`
  - `SourcesConfigError`
  - `collect`, `run`, `backfill`, `analyze`, `deliver`, `dashboard`, `doctor`
  - `history` does not read `sources.yaml`
  - `doctor_cli.main()` validates before data checks and before writing HTML
  - downstream `ValidationError` is not mislabeled as `sources.yaml`

- Keep all acceptance criteria checked, but replace historical suite/coverage wording with README badge/docs health wording.

- [ ] **Step 6: Run the targeted test and verify GREEN**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_cli_config_design_specs_match_current_completion_state -q
```

Expected: PASS.

- [ ] **Step 7: Run collect-only and update README test counts if needed**

Run:

```bash
uv run pytest --collect-only -q
```

Expected: the collected test count increases by one from the current `635`. If the output reports `636 tests collected`, update these six locations:

```text
README.md tests badge
README.md Tests table row
README.ko.md tests badge
README.ko.md 테스트 table row
README.zh.md tests badge
README.zh.md 测试 table row
```

Use the exact collected count from the command, not an assumption.

- [ ] **Step 8: Run focused docs tests**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Expected: all README/docs health tests pass.

- [ ] **Step 9: Commit the implementation**

Before committing:

```bash
git diff --check
git status --short --branch
```

Stage only the intended files. Do not stage `uv.lock`, `CLAUDE.md`, `docs/superpowers/handoffs/`, or new `.superpowers/` files.

```bash
git add tests/test_readme_docs.py \
  docs/superpowers/specs/2026-06-18-cli-entrypoints-design.md \
  docs/superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md \
  docs/superpowers/specs/2026-06-18-sources-config-cli-validation-design.md \
  README.md README.ko.md README.zh.md
git commit -m "test(docs): guard cli config spec truth"
```

If README counts did not change, omit the README files from `git add`.

---

## Self-Review

- Spec coverage: The plan covers all three stale completed design specs, blocks stale counts and coverage snapshots, and requires current CLI/dotenv/config-validation truth anchors.
- Placeholder scan: No TBD/TODO/fill-in placeholders remain; all file paths, test names, commands, and expected outcomes are explicit.
- Type consistency: The test uses existing `Path`, `_status_line`, and `_markdown_section` helpers already present in `tests/test_readme_docs.py`.
