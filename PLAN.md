# Project Plan

This file is the root resume point for active work. It intentionally stays
small; detailed plans live under `docs/superpowers/plans/`.

## Active Goal

User stop deadline: **2026-10-25 05:15:14 KST** (2026-10-24 20:15:14 UTC).
Background timer: functions cell `178` replaces terminated cell `81`. At the
absolute deadline, pause this same Goal whether active or blocked; do not reset
the clock on continuation or pause a replacement/completed Goal. The guard
self-checks passed. Stop new work, preserve the resume point and report paused.

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

## Current Loop — VM AUTHENTICATION / RUNTIME VERIFICATION

Implementation and portfolio checkpoint are integrated. PR18 and PR19 both
passed required CI (746 tests, production97%). Latest main1146307 tree equals
reviewed fd2e268; source/tests/runtime config remain identical to implementation
main410c876. The finite code queue is closed. Current local branch is
`codex/mimir-vm-verification-20261025`; this VM unit is not complete.

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
`my-cloud` SSH connection to TCP22 stayed SYN_SENT. The existing provider
server105 Web Console Access dialog is now confirmed open, but requires SSH
credentials. The user was asked to authenticate directly in the provider UI or
supply another SSH route. No credentials were submitted by the agent; the
provider tab is left as an authentication handoff. Guest resource/lock/current-
version/backup/runtime readiness remains unverified. Do not deploy until these
checks and the shared lock pass.

Owned local HTTP/browser/SSH resources are stopped; no VM lock or workload was
created. Merged cadence/doc-health/provenance/portfolio branches were audited and removed;
historical main, unmerged macro-policy branch and this VM verification branch are
preserved. The three original user-owned untracked artifacts remain unstaged.

When the connection path is available, check current guest services, memory,
disk, OOM and lock; use a bounded private synthetic CLI smoke, verify exact
source/artifact/runtime mapping, then stop owned resources and finish the Goal
review. Without that evidence the VM gate and whole Goal remain incomplete.
The same authenticated-VM-access blocker was confirmed in three consecutive
Goal turns, including a fresh live UI check of the same authentication dialog.
All other required implementation/CI/demo gates are closed; no independent
project work remains. Resume requires user login in the prepared console or a
working authorized SSH route. The Goal is not complete. The scheduled stop
deadline above still applies even while blocked.

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
