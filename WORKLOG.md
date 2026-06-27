# Work Log

## 2026-06-28 — WORKFLOW-CONCURRENCY-QUEUE

Goal: preserve all pending scheduled collection runs by queueing the reusable
pipeline's shared `collect` concurrency group.

Plan: `docs/superpowers/plans/2026-06-28-workflow-concurrency-queue.md`

Research:

- GitHub Docs documents workflow/job concurrency queueing and `queue: max`.
- GitHub Docs says `queue: max` queues up to 100 pending runs and cannot be
  combined with `cancel-in-progress: true`.
- Mimir already used `concurrency.group: collect` and
  `cancel-in-progress: false`, but without a queue policy GitHub keeps only one
  pending run by default.

TDD:

- RED: `uv run pytest tests/test_workflows.py::test_reusable_pipeline_queues_pending_collect_runs -q`
  failed because `_pipeline.yml` had no `queue: max`.

Verification:

- `uv run pytest tests/test_workflows.py::test_reusable_pipeline_queues_pending_collect_runs -q` — 1 passed
- `uv run pytest tests/test_workflows.py -q` — 4 passed
- `uv run pytest tests/test_readme_docs.py -q` — 27 passed
- `uv run pytest --collect-only -q | tail -1` — 646 tests collected
- `uv run pytest -q` — 646 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched files found only placeholders and existing GitHub
  Actions `secrets.*` references.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused workflow guard, workflow test file, docs guard, full
  pytest, ruff, mypy, and diff-check pass.

Result:

- `_pipeline.yml` now sets `concurrency.queue: max` with
  `cancel-in-progress: false`.
- README EN/KO/ZH test counts updated to 646.
- Spec review approved with no findings.
- Quality reviewer did not return before commit; controller gates passed.

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
