# Delivery Gates

This is the current evidence ledger. `GOAL.md` is stable; `PLAN.md` names the
active loop; dated detail stays in `WORKLOG.md` and `DECISIONS.md`.

## Global

- Source terms and provenance must be verified from current official sources.
- Official terms incompatible with the intended built-in use fail closed before
  that source's network or data writes. Existing GRAY-source policy is preserved.
- Trust-boundary validation, error handling, and accessibility are not optional.
- Focused tests must prove RED then GREEN for changed behavior.
- Full pytest, coverage `>=80%`, Ruff, mypy, docs guards, diff-check, secrets
  scan, independent spec review, and independent quality review must pass.
- Stage and commit only loop-owned files. Never push, deploy, publish, change
  credentials, or perform live-money actions without explicit approval.
- Preserve user-owned untracked files and clean only processes or temporary
  resources created by this loop.

## Current Loop — FRED-TERMS-SAFETY-BOUNDARY

| Gate | State | Evidence |
|---|---|---|
| Official terms | PASS | FRED Services Terms API prohibitions `(k)`/`(l)` and the cumulative API terms were checked on 2026-08-31: <https://fred.stlouisfed.org/legal/terms/> and <https://fred.stlouisfed.org/docs/api/terms_of_use.html> |
| Contract decision | PASS | The JSONL collect/backfill/analysis path is incompatible with the current storage prohibition; attribution alone is insufficient |
| Local data preflight | PASS | `git ls-files data reports` and local `find data reports -type f` returned no files; no user data deletion is authorized or needed |
| Detailed design and plan | PASS | Placeholder/diff checks passed; independent contract review found no remaining Critical or Important issue |
| TDD RED | PENDING | Builder/config/collect/backfill/stored-payload negative guards |
| Minimal implementation | PENDING | Remove the built-in adapter, activation/config paths, FRED payload branch, and current support claims |
| Focused GREEN | PENDING | Safety boundary, config, builder, payload, backfill, and docs guards |
| Full local gates | PENDING | pytest, coverage, Ruff, mypy, docs, diff, secrets, cleanup |
| Independent reviews | PENDING | No unresolved Critical or Important finding |
| Exact local commit | PENDING | No push; preserve `CLAUDE.md`, `docs/superpowers/handoffs/`, and `uv.lock` |
