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

## Current Loop — ECOS / MANUAL-RSS SOURCE PROVENANCE

Branch `codex/mimir-source-provenance-20261025`, based on main `3d777bc`
(PR #17 doc-health CI `40107271983` passed; main tree equals reviewed `9afc8e1`).
Seven original boundary regressions and five Important review findings have
reproducing tests and fixes. Source/config/payload/attribution propagation and
current documentation are implemented. Final scoped units: 680 passed; partial
source coverage 94%, mypy84/Ruff/diff-check pass. Astra and independent quality
reviews found no Critical/Important issues. Do not merge before required remote
CI passes.

Astra design review chose a bounded distinction: custom ECOS and every manual
RSS require target-specific usage evidence; code-owned SEC discovery routes
snapshot their actual origin but remain rights-unverified. Legacy source-aware
results cannot silently gain evidence; unrelated per-signal buckets remain
usable. The canonical contract and research limits live in
`docs/reference/config/sources.md` §4.4. Research and local logs are under
`/tmp/mimir-20261025-{rights,provenance}/`, with the research manifest copied
to resume evidence.

Continue final relevant unit/type/lint/docs/review gates, then commit, required
CI and main integration. Finish the actual CLI demo and private my-cloud
verification afterward, then branch/resource cleanup and final evidence audit.
Provider billing showed 9.9 MB / 3 TB with zero estimated overage, but its last
aggregation is not real-time and hard blocking is unconfirmed. SSH through
`my-cloud` to TCP 22 did not establish (SYN_SENT); asked for the current path.
The owned Orca terminal was closed with confirmed PTY termination. No VM lock,
workload or local HTTP service is owned. Temporary browser login tabs/server were stopped. No new VM deployment is claimed.

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
