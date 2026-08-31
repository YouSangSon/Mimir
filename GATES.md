# Delivery Gates

This is the current evidence ledger. `GOAL.md` is stable; `PLAN.md` names the
active loop; dated detail stays in `WORKLOG.md` and `DECISIONS.md`.

## Global

- Source terms and provenance must be verified from current official sources.
- Official terms incompatible with the intended built-in use fail closed before
  that source's network or data writes. Existing GRAY-source policy is preserved.
- Trust-boundary validation, error handling, and accessibility are not optional.
- Focused tests must prove RED then GREEN for changed behavior.
- Full pytest, coverage `>=80%`, Ruff, mypy, docs guards, diff-check, secrets
  scan, independent spec review, and independent quality review must pass.
- Stage and commit only loop-owned files. Never push, deploy, publish, change
  credentials, or perform live-money actions without explicit approval.
- Preserve user-owned untracked files and clean only processes or temporary
  resources created by this loop.

## Current Loop — FRED-TERMS-SAFETY-BOUNDARY

| Gate | State | Evidence |
|---|---|---|
| Official terms | PASS | FRED Services Terms API prohibitions `(k)`/`(l)` and the cumulative API terms were checked on 2026-08-31: <https://fred.stlouisfed.org/legal/terms/> and <https://fred.stlouisfed.org/docs/api/terms_of_use.html> |
| Contract decision | PASS | The JSONL collect/backfill/analysis path is incompatible with the current storage prohibition; attribution alone is insufficient |
| Local data preflight | PASS | `git ls-files data reports` and local `find data reports -type f` returned no files; no user data deletion is authorized or needed |
| Detailed design and plan | PASS | Placeholder/diff checks passed; independent contract review found no remaining Critical or Important issue |
| TDD RED | PASS | Exact focused RED command produced five expected failures (`5 failed in 4.44s`): builder `AssertionError: assert "fred" not in ...`; config `DID NOT RAISE ValidationError`; collect `assert responses.calls == []` (3 intercepted FRED calls); backfill expected `SystemExit` but reached `FetchError`; stored payload `DID NOT RAISE PayloadSchemaError`. `responses` intercepted the requests; no real network I/O. |
| Minimal implementation | PASS | Deleted the built-in adapter and its builder/settings/config/payload/default-metadata activation paths; existing strict config, unknown-source, ECOS, and `_narrow()` boundaries now fail closed |
| Focused GREEN | PASS | `uv run pytest tests/core/test_macro_series.py tests/core/test_payloads.py tests/storage/test_record_envelope.py tests/core/test_builder.py tests/sources/test_config.py tests/test_collect.py tests/test_backfill.py -q` — `196 passed in 2.05s` |
| Docs TDD RED | PASS | New current-surface guard failed before doc edits on `README.md missing removal notice`: `1 failed in 0.18s` |
| Current docs GREEN | PASS | `uv run pytest tests/test_readme_docs.py -q` — `36 passed in 1.50s`; collect-only reported `662 tests collected in 0.61s`, synced in all three README badges/tables |
| Docs history/safety | PASS | `uv run ruff check tests/test_readme_docs.py`, `git diff --check`, and the exact `git diff --exit-code HEAD -- docs/superpowers/plans docs/superpowers/specs docs/decisions/tech-spec` invariant passed; explicit executable-FRED and credential-pattern scans returned no matches |
| Docs fix round 1 | SUPERSEDED | Round 1 corrected ECOS legal-clearance claims, positional/current-surface coverage, and the manual-RSS evidence boundary. A subsequent re-review found that the trilingual guard still tested permission and series-rights words separately without locking the explicit re-enable condition or downstream notice/terms/privacy/citation obligations. |
| Docs fix round 2 | PASS | The guard independently locks each README's exact re-enable condition and all applicable notice/terms/privacy/citation obligations. Final tracked-tree rerun: focused guard `1 passed in 0.03s`; docs `36 passed in 1.14s`; full suite `662 passed in 9.56s`; count `662 tests collected in 0.37s`; test-file Ruff, diff-check, dated-history invariant, active-surface, and credential scans passed. |
| Full local gates | PASS | `uv run pytest -q` — `662 passed in 10.73s`; isolated coverage run — `662 passed in 11.42s`; `coverage report --fail-under=80` — `8447` statements, `134` missed, `98%`; `uv run ruff check .` and `uv run mypy mimir` passed (`83` source files); `git diff --check` passed |
| Count and dated history | PASS | Collect-only: `662 tests collected in 0.53s`; each README has the exact count in its badge and table (two `662` occurrences each), and coverage remains `98%`; `git diff --exit-code HEAD -- docs/superpowers/plans docs/superpowers/specs docs/decisions/tech-spec` returned no diff |
| Final safety scans | PASS | Explicit runtime/config/workflow/sample-env/current-doc/state scan found no executable activation; multiline positional `SourceSpec("fred", ...)` scan found none. Remaining FRED hits are removal/terms notices, negative guards, decisions/worklog, or dated history. Credential-value scan of `f87895a..HEAD` found no matches and printed no values |
| Final cleanup and ownership | PASS | No Mimir pytest/coverage process, Podman container, or Kind cluster remains; only the pre-existing ignored `.coverage` is outside the isolated plan-workspace `coverage-data`. `data/` and `reports/` have no tracked or local files and are unchanged; protected `CLAUDE.md`, `docs/superpowers/handoffs/`, and `uv.lock` remain untracked and unstaged |
| Independent whole-diff reviews | PASS | Final merge-review scoped re-review: APPROVE. The meta-less-plugin backfill Important and ECOS/KR fixture Minor are addressed; no Critical or Important finding remains |
| Final consolidation | PASS | Separate plan checkpoint `f87895a`; one final implementation commit, `fix(sources): remove incompatible FRED integration`, covers reviewed range `f87895a..this implementation commit` after the approved correction wave |
| Exact local verification commit | PASS | This final implementation commit carries the approved correction wave and its `662`-test, `98%` isolated-coverage, Ruff/mypy, docs/history, and diff-check evidence; no push or remote mutation |
| PR | PENDING | Controller-owned; no PR created in this phase |
| CI | PENDING | No remote workflow run triggered in this phase |
| Main merge | PENDING | Controller-owned after review, integration, and CI evidence |
