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

## Current Loop — DOCTOR-MACRO-SINGLE-SCAN

Per-series macro freshness computes latest record dates in one dataset scan,
preserving cadence and diagnostic ordering. Focused doctor/dashboard tests
pass (41), as does independent spec/quality review. Final full suite: 689 passed;
production coverage 97%, Ruff and strict mypy pass. CI/main integration pending.

Previous CLI date loop merged in PR #13 at `1f8e23c`; CI run `39984146712`
passed in 32 seconds, and main matches reviewed head `442c8f1`.

Remaining work stays in `BACKLOG.md`: provenance/attribution across raw and
derived data, report accessibility/demo, cadence regression, and docs truth.
Research evidence is retained locally; ECOS provider terms alone do not grant
rights to every third-party series or authorize old stored data.

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
