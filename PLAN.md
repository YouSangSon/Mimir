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

## Current Loop — CLI-DATE-ARGUMENT-BOUNDARY

Six CLI date options now use argparse's standard type conversion, preserving
the existing `date.fromisoformat` accepted inputs and omitted-date defaults.
Focused CLI/consumer tests pass (63); the full 688-test coverage suite,
production coverage 97%, Ruff/mypy, spec/quality review, and installed CLI
checks pass. Remote CI/main integration is pending.

The previous YAML loop is merged in PR #12 at `2c0bcb9`; the main tree exactly
matches reviewed head `0d3b26e`. CI run `39981998281` passed in 35 seconds.
Source-rights research has confirmed ECOS provider terms and the default BOK
series metadata. Implementing custom-input provenance and durable raw-to-derived
attribution remains next; changing current config cannot authorize old data.

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
