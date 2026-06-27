# Work Log

## 2026-06-28 — PROJECT-STATE-ENTRYPOINTS

Goal: make root repo documents the starting point for continuation without
duplicating the canonical docs under `docs/`.

Plan: `docs/superpowers/plans/2026-06-28-project-state-entrypoints.md`

Research:

- Repo inspection found no root `PLAN.md`, `BACKLOG.md`, `WORKLOG.md`, or
  `DECISIONS.md`.
- Existing canonical state already lives in `docs/IMPROVEMENTS.md`,
  `docs/architecture/improvement-catalog.md`,
  `docs/decisions/tech-spec/README.md`, `docs/superpowers/plans/`, git history,
  and committed project docs.

TDD:

- RED: `uv run pytest tests/test_readme_docs.py::test_root_project_state_entrypoints_link_canonical_sources -q`
  failed because `PLAN.md` was missing.

Verification:

- `uv run pytest tests/test_readme_docs.py::test_root_project_state_entrypoints_link_canonical_sources -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 27 passed
- `uv run pytest --collect-only -q | tail -1` — 645 tests collected
- `uv run pytest -q` — 645 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed

Review:

- Spec review found that root entrypoints initially referenced local scratch
  state; fixed by keeping root docs pointed at tracked docs and git history only.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused docs test, docs test suite, full pytest, ruff, mypy, and
  diff-check pass.

Result:

- Root project-state entrypoints added as pointers to canonical docs.
- README EN/KO/ZH test counts updated to 645.
- Backlog reordered so `WORKFLOW-CONCURRENCY-QUEUE` is next.
