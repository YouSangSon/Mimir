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

## Current Loop — DELIVERY-CADENCE-CONTRACT

The existing stored-insight delivery regression now covers hourly, daily,
weekly and monthly. It observes the real digest and saved HTML, and the real
credential-free Telegram no-op with zero intercepted HTTP calls. No runtime
change is needed. Focused 21 and full 701 tests pass; production coverage 97%,
Ruff/mypy and independent review pass. CI/main integration is pending.

Report accessibility merged through PR #15: CI run `40106364995` passed;
main `70f533b` tree equals reviewed head `bedd244`. Evidence is under the
resume `자료수집/2026-10-25/mimir-portfolio/report-a11y/` directory.
Continue `BACKLOG.md`, runnable local demo and verified branch/resource cleanup.

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
