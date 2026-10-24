# Project Plan

This file is the root resume point for active work. It intentionally stays
small; detailed plans live under `docs/superpowers/plans/`.

## Active Goal

User stop deadline: **2026-10-25 05:15:14 KST** (2026-10-24 20:15:14 UTC).
Background timer: functions cell `81`. At deadline, stop new work, safely clean
owned resources, save the resume point and report paused status.

Finish a usable, verified portfolio version of Mimir's existing S1–S4 pipeline.
The latest 2026-10-25 user request supersedes older execution limits and
continues the existing Goal scope. Commit/push/PR/main merge remain authorized.
Local checks must be lightweight, relevant and sequential; do not launch heavy
integration stacks. Required free remote CI stays mandatory. Use only existing
my-cloud for the requested minimal VM verification, after current resource,
shared-lock, billing-traffic and recovery checks. No paid execution, credential
changes, workflow reactivation, public demo or new cloud resources are authorized.
Preserve the existing GRAY-source policy and user-owned files.

Completion requires the finite `BACKLOG.md` queue, a runnable local demo with
real CLI/report success and failure flows, required local/review/CI gates,
main integration, verified branch/resource cleanup, and evidence under the
existing resume `자료수집` structure. S5 trading, paid LLM execution, generic
RSS discovery, and new cloud infrastructure remain outside this goal.

- Original loop contract: `GOAL.md`
- Current delivery evidence: `GATES.md`
- Decisions and work evidence: `DECISIONS.md`, `WORKLOG.md`

## Current Loop — PORTFOLIO / RUNTIME VERIFICATION

Source provenance merged through PR18 after CI40113216793 passed746 tests,
production coverage97%, mypy84/Ruff. Main410c876 tree equals reviewed c7c5453.
The finite code queue is closed; no new feature scope is needed.

Actual installed CLI demo passed16 checks with synthetic data: insight8,
historical1, evaluation buckets3; invalid date/YAML/missing evidence and empty
store paths verified. Browser375/1280px, source preservation, keyboard table
scroll and report link verified. No paid LLM or external delivery was called.
Evidence is under resume `자료수집/2026-10-25/mimir-portfolio/`; root README
there maps problems, decisions, PRs, measured facts and limits. The source
contract remains `docs/reference/config/sources.md` §4.4.

Remaining required gate: private my-cloud runtime verification. Provider display
showed9.9MB/3TB and zero estimated overage, with last aggregation2026-10-24
13:07:39 (timezone unspecified); hard overage blocking is unconfirmed. The
`my-cloud` SSH connection to TCP22 stayed SYN_SENT. Asked for the current
connection path. Guest resource/lock/current-version/backup/runtime readiness
cannot be claimed. Do not deploy until these checks and the shared lock pass.

Owned local HTTP/browser/SSH resources are stopped; no VM lock or workload was
created. Merged cadence/doc-health/provenance branches were audited and removed;
historical main, unmerged macro-policy branch and this verification branch are
preserved. Only the three original user-owned untracked artifacts remain.

When the connection path is available, check current guest services, memory,
disk, OOM and lock; use a bounded private synthetic CLI smoke, verify exact
source/artifact/runtime mapping, then stop owned resources and finish the Goal
review. Without that evidence the VM gate and whole Goal remain incomplete.
The scheduled stop deadline above still applies.

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
