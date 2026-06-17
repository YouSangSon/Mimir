# Sources Config CLI Validation Implementation Plan

**Goal:** Make every CLI that reads `sources.yaml` enforce the documented fail-fast config contract with the same `[mimir] invalid sources.yaml:` message, while preserving narrow exception handling so downstream validation errors still surface as real bugs.

**Architecture:** Add one CLI helper in `mimir.config` that loads raw `sources.yaml` and validates it with `parse_sources_config()`. CLI `main()` functions call the helper inside a narrow `try/except ValidationError`, then pass either the raw dict or parsed `SourcesConfig` to the existing runtime functions.

## Global Constraints

- Do not broaden `try/except ValidationError` around runtime pipeline calls.
- Do not convert downstream data/model validation failures into `invalid sources.yaml`.
- Do not change `sources.yaml` schema or plugin-owned schema rules.
- Do not change report rendering language normalization.
- Keep untracked `uv.lock` unstaged.

---

## File Map

| File | Responsibility |
|---|---|
| `mimir/config.py` | Shared CLI helper for validated source config loading |
| `mimir/analyze.py` | Friendly malformed config handling for analyze CLI |
| `mimir/deliver.py` | Friendly malformed config handling for deliver CLI |
| `mimir/dashboard.py` | Friendly malformed config handling for dashboard CLI |
| `mimir/collect.py` | Existing behavior uses helper without semantic change |
| `mimir/run.py` | Existing behavior uses helper without broadening catch |
| `mimir/backfill.py` | Existing behavior uses helper without semantic change |
| `tests/test_analyze.py` | Analyze malformed config CLI test |
| `tests/test_deliver.py` | Deliver malformed config CLI test |
| `tests/test_dashboard_cli.py` | Dashboard malformed config CLI test |
| `tests/test_run.py` | Existing downstream ValidationError guard |
| `docs/architecture/improvement-catalog.md` | Tracking |
| `docs/IMPROVEMENTS.md` | Backlog/status |
| `docs/superpowers/specs/2026-06-18-sources-config-cli-validation-design.md` | Acceptance checklist |

---

## Task 1: Add Failing CLI Validation Tests

- [x] Add malformed `sources.yaml` tests for `analyze`, `deliver`, and `dashboard`.
- [x] Assert stderr starts with `[mimir] invalid sources.yaml:`.
- [x] Assert deliver/dashboard do not create report output on config failure.
- [x] Run the focused tests and confirm RED:

```bash
uv run pytest tests/test_analyze.py tests/test_deliver.py tests/test_dashboard_cli.py -q
```

Expected: at least one new test fails before implementation.

## Task 2: Implement Shared Validated Config Helper

- [x] Add `load_validated_sources_config()` to `mimir.config`.
- [x] Update `collect`, `run`, `backfill` to use it while keeping current behavior.
- [x] Update `analyze`, `deliver`, `dashboard` to catch only config-load validation errors.
- [x] Run focused tests and confirm GREEN.

## Task 3: Update Tracking Docs

- [x] Record the CLI `sources.yaml` validation contract fix in `docs/IMPROVEMENTS.md`.
- [x] Add a completed `CFG1` item to `docs/architecture/improvement-catalog.md`.
- [x] Mark spec/plan checklists complete after verification.

## Task 4: Verify

- [x] Run focused tests:

```bash
uv run pytest tests/test_analyze.py tests/test_deliver.py tests/test_dashboard_cli.py tests/test_run.py tests/test_backfill.py tests/test_collect.py -q
```

- [x] Run full gates:

```bash
uv run ruff check .
uv run mypy mimir
uv run pytest -q
uv run coverage run -m pytest
uv run coverage report --fail-under=80
git diff --check
```

- [ ] Task review.
- [ ] Final review.
- [ ] Commit branch.
