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

## Current Loop — CONFIG-YAML-SYNTAX-ERROR-BOUNDARY

The shared loaders normalize YAML parser failures into the existing config
errors; all affected CLI entry points catch them before side effects. A
parameterized regression covers 14 command/file combinations and ensures
parser diagnostics never print input values. Local gates pass (676 tests,
production coverage 97%, Ruff/mypy), along with spec/quality review and installed-CLI smoke. Remote CI and main integration
are pending; source-rights research continues independently.

Previous FRED work is merged through PR #10, with integration evidence in #11.

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
