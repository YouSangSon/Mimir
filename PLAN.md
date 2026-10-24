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

## Current Loop — CURRENT-HEALTH-DOC-TRUTH

Corrected current docs against workflow code, file counts and official GitHub
schedule/billing documentation. No production or test code changes. Reuse the
701-test/97% production-coverage, mypy and Ruff evidence from cadence head
`848ff80`, whose source/test tree equals this branch; rerun docs guards and
diff-check for this doc-only slice. Docs guards (36), diff-check and independent
review passed. CI/main pending.

Cadence regression merged in PR #16: CI `40106816741` passed; main `b902c89`
equals reviewed head `848ff80`. Verified cleanup removed 25 local and six
remote merged branches; unproven `feat/macro-revision-policy`, historical local
main and the active branch were retained. Evidence is in the resume portfolio.

Next: ECOS/manual-RSS provenance and derived attribution, then runnable local
demo and final integration/cleanup audit. Fresh official rights evidence is in
`/tmp/mimir-20261025-rights/`; no right is inferred from a provider label alone.

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
