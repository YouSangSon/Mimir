# Task 3 Report: Documentation Truth Guards

## Scope

- Requirements source: `.superpowers/sdd/task-3-brief.md`
- Runtime code edits: none
- Guard/test file edited: `tests/test_readme_docs.py`
- Docs edited:
  - `docs/reference/cli.md` (new)
  - `docs/reference/config/sources.md`
  - `docs/architecture/extensibility/README.md`
  - `docs/decisions/tech-spec/README.md`
  - `docs/reference/analysis/scoring.md`
  - `README.md`
  - `README.ko.md`
  - `README.zh.md`

## RED evidence

### 1. Targeted RED command from the brief

Command:

```bash
uv run pytest tests/test_readme_docs.py::test_readme_links_all_reference_docs tests/test_readme_docs.py::test_sec_ticker_cik_refresh_docs_match_implemented_state tests/test_readme_docs.py::test_scoring_reference_documents_news_volume_confidence -q
```

Result: failed as expected.

Key failures:

- `docs/reference/config/sources.md` was missing `ticker_cik_map_refresh`
- `docs/reference/analysis/scoring.md` still documented `news_volume` default confidence as `—`

Observed summary:

```text
.FF
2 failed, 1 passed
```

## Changes made

### 1. Added documentation truth guards

In `tests/test_readme_docs.py`:

- added `docs/reference/cli.md` to `README_REQUIRED_LINKS`
- added `REFERENCE_DOCS`
- added `SEC_REFRESH_DOCS`
- added:
  - `test_readme_links_all_reference_docs()`
  - `test_sec_ticker_cik_refresh_docs_match_implemented_state()`
  - `test_scoring_reference_documents_news_volume_confidence()`

### 2. Created CLI reference

Created `docs/reference/cli.md` in Korean with:

- command matrix for `run`, `collect`, `backfill`, `analyze`, `deliver`, `history`, `doctor`, `evaluate`, `dashboard`
- which commands read config/data/reports
- fixed friendly error prefixes
- explicit note that `evaluate` does not read `--config-dir`
- explicit note that `doctor --strict` is operator-selected, not a scheduled hard gate
- explicit note that unified `mimir <command>` and dotted aliases both remain available

### 3. Updated SEC refresh docs to match implementation

In `docs/reference/config/sources.md`:

- added `sec.ticker_cik_map_refresh`
- documented `enabled`, `url`, `max_age_hours`
- documented off-by-default behavior and zero default network requests
- documented build-time refresh placement before source build, not inside RSS resolver
- documented TTL gate, ETag conditional GET, `304` mtime reset, orphaned `304` warning/no crash, temp-file validation, atomic adoption, and fallback-on-failure behavior
- removed stale wording that claimed Mimir does not download or judge staleness at all

In `docs/architecture/extensibility/README.md`:

- updated final date to `2026-06-23`
- added `ticker_cik_map_refresh` to the YAML example
- replaced deferred SEC cache wording with the implemented off-by-default refresh behavior
- kept provider RSS live discovery as remaining debt

### 4. Updated supporting docs

- `docs/decisions/tech-spec/README.md`
  - added source-row links to:
    - `docs/superpowers/specs/2026-06-19-sec-ticker-cik-map-cache-design.md`
    - `docs/superpowers/specs/2026-06-19-captured-date-persistent-index-design.md`
  - labeled both as design specs
- `docs/reference/analysis/scoring.md`
  - changed `news_volume` default confidence to `0.5`

### 5. Updated README navigation and test counts

In `README.md`, `README.ko.md`, `README.zh.md`:

- added `docs/reference/cli.md` to Further Reading
- updated tests badge/table count from `576` to `586` to match current pytest collection after the new guards

## GREEN evidence

### 1. Docs guard suite

Command:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Result:

```text
......                                                                   [100%]
6 passed in 1.34s
```

### 2. Pytest collection

Command:

```bash
uv run pytest --collect-only -q
```

Result:

```text
586 tests collected in 0.99s
```

### 3. Ruff

Command:

```bash
uv run ruff check tests/test_readme_docs.py
```

Result:

```text
All checks passed!
```

### 4. Diff whitespace check

Command:

```bash
git diff --check
```

Result:

```text
(no output)
```

## Self-review

- Confirmed all edits stayed within the allowed Task 3 file list plus the requested report file.
- Did not edit runtime code.
- Did not modify `uv.lock`.
- Verified the new CLI reference is linked from all README variants so the new README guard covers the full `docs/reference/` set.
- Matched SEC refresh wording to the as-built implementation in `mimir/sources/sec_ticker_cik_refresh.py` and the build-time hook in `mimir/core/builder.py`.

## Concerns / residual notes

- The README test count is a moving contract. Any future added/removed tests will require a README badge/table update or the doc guard will fail.
- `docs/reference/cli.md` is Korean-first by task requirement; the README link text remains localized per README language.

---

## Task 3 Execution — 2026-06-23

### Scope

- Requirements source: `.superpowers/sdd/task-3-brief.md`
- Runtime code edits: none
- Guard/test file edited: `tests/test_readme_docs.py`
- Docs edited:
  - `docs/architecture/extensibility/README.md`
  - `docs/reference/config/sources.md`
  - `docs/architecture/improvement-catalog.md`
  - `docs/decisions/tech-spec/README.md`
  - `README.md`
  - `README.ko.md`
  - `README.zh.md`
- Report appended: `.superpowers/sdd/task-3-report.md`

### TDD mapping

| Requirement | RED evidence | GREEN evidence |
|---|---|---|
| Add docs guards for AN1 tech spec, latest catalog ID, and signal plugin contract | `uv run pytest tests/test_readme_docs.py::test_signal_plugin_docs_match_extension_contract tests/test_readme_docs.py::test_improvement_catalog_summary_mentions_latest_completed_ids tests/test_readme_docs.py::test_readmes_link_current_decision_and_config_docs -q` failed | `uv run pytest tests/test_readme_docs.py -q` passed |
| Document signal plugin seam in extensibility/config/catalog/tech-spec index/README links | Missing `mimir.analysis_signals`, `analysis.plugins`, and README tech-spec link in RED output | Updated owned docs and README Further Reading tables |
| Sync README test metadata if collected count changes | `tests/test_readme_docs.py` failed on `588 != 611` after collect-only | Updated all three README badges/table rows to `611` |

### RED evidence

#### 1. Focused RED command from the brief

Command:

```bash
uv run pytest \
  tests/test_readme_docs.py::test_signal_plugin_docs_match_extension_contract \
  tests/test_readme_docs.py::test_improvement_catalog_summary_mentions_latest_completed_ids \
  tests/test_readme_docs.py::test_readmes_link_current_decision_and_config_docs \
  -q
```

Result: failed as expected.

Observed summary:

```text
FFF
3 failed in 0.04s
```

Key failures:

- `docs/architecture/extensibility/README.md` missing `mimir.analysis_signals`
- `docs/architecture/improvement-catalog.md` status/conclusion missing `AN1-SIGNAL-PLUGIN-ENTRYPOINTS`
- `README.md` missing `docs/decisions/tech-spec/analysis/AN1_signal_plugin_entrypoints_tech_spec_2026_06_23.md`

#### 2. Collected-count drift discovered during verification

Command:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Intermediate result after doc edits but before README count sync:

```text
F.......
1 failed, 7 passed in 0.77s
```

Key failure:

- README badge/table contract expected `611` collected tests, but all three READMEs still said `588`.

### Changes made

#### 1. Added docs guards first in `tests/test_readme_docs.py`

- added `AN1-SIGNAL-PLUGIN-ENTRYPOINTS` to `LATEST_COMPLETED_IDS`
- added `docs/decisions/tech-spec/analysis/AN1_signal_plugin_entrypoints_tech_spec_2026_06_23.md` to `README_REQUIRED_LINKS`
- added `test_signal_plugin_docs_match_extension_contract()`

#### 2. Updated signal plugin seam docs

`docs/architecture/extensibility/README.md`

- added analysis extension-table row text for `mimir.analysis_signals`
- documented `analysis.plugins.<signal_id>` opt-in config
- documented default path behavior: no entry-point read/import unless plugin config exists
- documented built-ins-first ordering, configured plugins appended after built-ins
- documented warning-on-broken-import and loud-fail cases for wrong object type, duplicate id, entry-point/spec mismatch, factory id mismatch
- documented trust boundary: in-process execution, no sandbox, access to settings/config/data

`docs/reference/config/sources.md`

- added `analysis.plugins` subsection under `analysis:`
- documented `analysis.plugins.<signal_id>` must be a mapping
- documented that core validates only the mapping boundary
- documented plugin-side schema validation via `parse_analysis_plugin_config()`
- documented secrets policy: keep sensitive values in env/GitHub Secrets, not YAML
- documented trust boundary with explicit `sandbox` wording

`docs/architecture/improvement-catalog.md`

- added `AN1-SIGNAL-PLUGIN-ENTRYPOINTS` to the summary table
- added AN1 to the status line
- added a short AN1 section explaining the new seam
- added AN1 to the sequencing section
- kept `LLM signal weight YAML 노출` deferred
- added AN1 to the final conclusion list

`docs/decisions/tech-spec/README.md`

- added the AN1 entry under a new `analysis` section

#### 3. Updated README links and test metadata

`README.md`, `README.ko.md`, `README.zh.md`

- added the direct AN1 tech-spec link to Further Reading
- updated tests badge/table count from `588` to `611` after `uv run pytest --collect-only -q`

### GREEN evidence

#### 1. Docs guard suite

Command:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Result:

```text
........
8 passed in 0.82s
```

#### 2. Pytest collection

Command:

```bash
uv run pytest --collect-only -q
```

Result:

```text
611 tests collected in 0.40s
```

#### 3. Ruff

Command:

```bash
uv run ruff check tests/test_readme_docs.py
```

Result:

```text
All checks passed!
```

#### 4. Diff whitespace check

Command:

```bash
git diff --check
```

Result:

```text
(no output)
```

### Verification commands run

```bash
uv run pytest \
  tests/test_readme_docs.py::test_signal_plugin_docs_match_extension_contract \
  tests/test_readme_docs.py::test_improvement_catalog_summary_mentions_latest_completed_ids \
  tests/test_readme_docs.py::test_readmes_link_current_decision_and_config_docs \
  -q
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q
uv run ruff check tests/test_readme_docs.py
git diff --check
```

### Files changed

- `tests/test_readme_docs.py`
- `docs/architecture/extensibility/README.md`
- `docs/reference/config/sources.md`
- `docs/architecture/improvement-catalog.md`
- `docs/decisions/tech-spec/README.md`
- `README.md`
- `README.ko.md`
- `README.zh.md`
- `.superpowers/sdd/task-3-report.md`

### Commit

- Commit message: `docs(analysis): document signal plugin extension seam`
- Commit hash: `4be752b`

### Self-review notes

- Stayed within the owned doc/test/report files and left the pre-existing untracked `uv.lock` untouched.
- Did not edit runtime code, builder tests, config tests, `pyproject`, or lock files.
- Used the docs guard to force the README count update when pytest collection moved from `588` to `611`.
- Matched the docs to the implemented signal-plugin contract already established in Tasks 1–2: exact entry-point group `mimir.analysis_signals`, opt-in `analysis.plugins.<signal_id>`, built-ins first, configured plugins appended, warning/skip for broken import, loud failure for contract violations, and explicit no-sandbox trust boundary.
