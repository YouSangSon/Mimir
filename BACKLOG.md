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

1. Fresh docs-truth scan across `docs/superpowers/specs/`,
   `docs/decisions/tech-spec/`, and `docs/architecture/` for any remaining
   stale current-state claims.

## Done

- `WORKFLOW-CONCURRENCY-QUEUE` — `.github/workflows/_pipeline.yml` now uses
  `concurrency.queue: max` with `cancel-in-progress: false` so scheduled
  collection runs queue in the shared `collect` group.
- `PROJECT-STATE-ENTRYPOINTS` — root `PLAN.md`, `BACKLOG.md`, `WORKLOG.md`,
  and `DECISIONS.md` pointers added so future sessions can resume from repo
  documents plus git history.

## Notes

- `PROJECT-STATE-ENTRYPOINTS` must not duplicate the long backlog/catalog.
- `WORKFLOW-CONCURRENCY-QUEUE` needs its own RED workflow guard before changing
  YAML.
