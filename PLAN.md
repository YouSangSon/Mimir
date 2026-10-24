# Project Plan

This file is the root resume point for active work. It intentionally stays
small; detailed plans live under `docs/superpowers/plans/`.

## Active Goal

Finish a usable, verified portfolio version of Mimir's existing S1–S4 pipeline.
The 2026-10-24 user request authorizes commit, push, PR, and main merge after
required checks; it supersedes the older local-commit-only instruction in
`GOAL.md`. No paid execution, credential changes, workflow reactivation, or VM
use is authorized. Keep the existing GRAY-source policy and user-owned files.

Completion requires the finite `BACKLOG.md` queue, a runnable local demo with
real CLI/report success and failure flows, required local/review/CI gates,
main integration, verified branch/resource cleanup, and evidence under the
existing resume `자료수집` structure. S5 trading, paid LLM execution, generic
RSS discovery, and new cloud infrastructure remain outside this goal.

- Original loop contract: `GOAL.md`
- Current delivery evidence: `GATES.md`
- Decisions and work evidence: `DECISIONS.md`, `WORKLOG.md`

## Current Loop — REPORT-HTML-MOBILE-A11Y

Goal resumed on 2026-10-25. Current branch:
`codex/mimir-report-a11y-20261024`. Viewport/theme/table accessibility changes
and their regressions are implemented. Independent review passed; rendered
inspection led to a compact-cell/detail-column CSS correction. Final local
(698 tests, production coverage 97%, Ruff/mypy) and browser checks pass. CI and
main integration remain pending. Evidence:
`/tmp/mimir-20261025-ui/`; completed units are copied to the resume portfolio.

Doctor optimization merged in PR #14 (`00b103b`); YAML/date fixes merged in
PR #12/#13. Continue the finite `BACKLOG.md` queue, runnable CLI demo, and
verified branch/resource cleanup after this unit. Rights research does not
constitute runtime provenance enforcement or approval for third-party data.

## Canonical Sources

- Implementation plans: `docs/superpowers/plans/`
- Improvement backlog: `docs/IMPROVEMENTS.md`
- Architecture catalog: `docs/architecture/improvement-catalog.md`
- Decision tech specs: `docs/decisions/tech-spec/README.md`
- History: `git log`

## Next Loop Candidates

Use `BACKLOG.md` first, then choose one coherent slice. Do not mix workflow,
docs-truth, and feature changes in the same loop unless one cannot be verified
without the other.
