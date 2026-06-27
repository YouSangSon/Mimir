# Decisions

This file records durable loop-level decisions. Canonical domain tech specs live
in `docs/decisions/tech-spec/README.md`.

## 2026-06-28 — DECISIONS-FOLLOWUP-DOC-TRUTH

Decision: once a follow-up loop is complete, remove the stale follow-up from
the earlier decision instead of leaving it as historical current-state text.

Reason:

- `DECISIONS.md` records durable rationale, but a `Follow-up:` block reads as
  active work.
- `WORKFLOW-CONCURRENCY-QUEUE` now has its own decision entry and verification
  evidence.
- Keeping the old follow-up in `PROJECT-STATE-ENTRYPOINTS` made the root state
  docs contradict themselves.

Rejected:

- Leaving the old follow-up for historical context. Git history already
  preserves it, and the newer workflow decision now carries the durable
  rationale.

## 2026-06-28 — BACKLOG-NOTES-DOC-TRUTH

Decision: completed backlog items should keep verification and rationale in
`WORKLOG.md` and `DECISIONS.md`, not as item-specific pre-implementation
warnings in `BACKLOG.md` Notes.

Reason:

- `BACKLOG.md` is the active queue and lightweight policy surface.
- Once `WORKFLOW-CONCURRENCY-QUEUE` moved to Done, the old note saying it still
  needed a RED guard became stale current-state wording.
- A generic evidence rule preserves the useful process constraint without
  implying completed work is still pending.

Rejected:

- Keeping a workflow-specific warning in Notes after completion, because it
  contradicts Done state and duplicates evidence already recorded in
  `WORKLOG.md`.

## 2026-06-28 — WORKFLOW-CONCURRENCY-QUEUE

Decision: set workflow-level `concurrency.queue: max` in the reusable scheduled
pipeline while keeping `cancel-in-progress: false`.

Reason:

- Mimir's hourly/daily/weekly/monthly schedulers all call `_pipeline.yml`, which
  uses one `collect` concurrency group.
- GitHub's default concurrency queue keeps only one pending run in a group.
  Later pending runs can replace earlier pending runs before they collect data.
- `queue: max` keeps up to 100 pending runs. That matches Mimir's data
  collection goal better than silently replacing scheduled runs.

Sources:

- GitHub Docs, control workflow/job concurrency:
  https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
- GitHub Docs, workflow syntax:
  https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub Docs, Actions limits:
  https://docs.github.com/en/actions/reference/limits

Rejected:

- `cancel-in-progress: true` remains off because GitHub documents that it cannot
  be combined with `queue: max`, and canceling in-progress collection would risk
  data gaps.

## 2026-06-28 — PROJECT-STATE-ENTRYPOINTS

Decision: add root project-state entrypoints as pointers, not a second planning
database.

Reason:

- The user requested `PLAN.md`, `BACKLOG.md`, `WORKLOG.md`, and `DECISIONS.md`
  as continuation sources.
- The repo already has canonical detail in `docs/IMPROVEMENTS.md`,
  `docs/architecture/improvement-catalog.md`,
  `docs/decisions/tech-spec/README.md`, and `docs/superpowers/plans/`.
- Thin root docs satisfy continuation needs while avoiding copied state that
  will drift.

External research recorded before implementation:

- GitHub Docs documents `concurrency.queue: max` for workflow/job concurrency:
  https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
- GitHub Docs workflow syntax also covers concurrency behavior:
  https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Finding: default queueing keeps one pending run in a concurrency group, while
  `queue: max` queues up to 100 pending runs. GitHub documents that
  `queue: max` cannot be used with `cancel-in-progress: true`.
