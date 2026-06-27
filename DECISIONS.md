# Decisions

This file records durable loop-level decisions. Canonical domain tech specs live
in `docs/decisions/tech-spec/README.md`.

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

External research recorded for next loop:

- GitHub Docs documents `concurrency.queue: max` for workflow/job concurrency:
  https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
- GitHub Docs workflow syntax also covers concurrency behavior:
  https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Finding: default queueing keeps one pending run in a concurrency group, while
  `queue: max` queues up to 100 pending runs. GitHub documents that
  `queue: max` cannot be used with `cancel-in-progress: true`.

Follow-up:

- `WORKFLOW-CONCURRENCY-QUEUE` should be a separate loop with a workflow guard
  before changing `.github/workflows/_pipeline.yml`.
