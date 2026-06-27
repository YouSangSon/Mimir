# Backlog

This file is the root queue. Canonical detail stays in:

- `docs/IMPROVEMENTS.md`
- `docs/architecture/improvement-catalog.md`

## Priority Policy

1. Stability and bug fixes
2. Testability and verification
3. Extensibility
4. Developer experience
5. Documentation
6. New features

Move a feature higher only when it materially advances Mimir's core purpose:
free, legal public-data collection and investment insight generation.

## Queue

1. Audit remaining typing casts/guards and keep only those that document a real
   pydantic or intentionally invalid-test boundary.

## Done

- `NORMALIZE-PAYLOAD-TYPE-CLEANUP` — normalize now parses payloads before
  `Record` construction and payload dispatch uses a typed cast instead of local
  `type: ignore` comments.
- `STOOQ-FLOAT-PARSER-TYPE-CLEANUP` — Stooq optional numeric CSV fields are
  covered, and `_f()` no longer needs a local `type: ignore[arg-type]`.
- Fresh docs-truth scan — no stronger stale current-state claim remained after
  the backlog/decision follow-up cleanups; deferred items stay in the catalog
  until measurement or policy evidence changes.
- `DECISIONS-FOLLOWUP-DOC-TRUTH` — stale `PROJECT-STATE-ENTRYPOINTS`
  decision follow-up removed after `WORKFLOW-CONCURRENCY-QUEUE` completed.
- `BACKLOG-NOTES-DOC-TRUTH` — `BACKLOG.md` Notes now keep completed-item
  evidence policy generic instead of item-specific pre-implementation warnings.
- `WORKFLOW-CONCURRENCY-QUEUE` — `.github/workflows/_pipeline.yml` now uses
  `concurrency.queue: max` with `cancel-in-progress: false` so scheduled
  collection runs queue in the shared `collect` group.
- `PROJECT-STATE-ENTRYPOINTS` — root `PLAN.md`, `BACKLOG.md`, `WORKLOG.md`,
  and `DECISIONS.md` pointers added so future sessions can resume from repo
  documents plus git history.

## Notes

- `PROJECT-STATE-ENTRYPOINTS` must not duplicate the long backlog/catalog.
- Completed items keep verification evidence in `WORKLOG.md` and decision
  rationale in `DECISIONS.md`; Notes should not keep pre-implementation
  warnings after an item moves to Done.
