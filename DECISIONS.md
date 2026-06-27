# Decisions

This file records durable loop-level decisions. Canonical domain tech specs live
in `docs/decisions/tech-spec/README.md`.

## 2026-06-28 — LLM-SIGNAL-WEIGHT-DEFERRAL-RECHECK

Decision: keep one-off LLM signal weight YAML exposure deferred.

Reason:

- Built-in signal weights are still code constants:
  `price_momentum=1.0`, `filing_event=0.8`, `news_volume=0.5`,
  `macro_regime=0.3`, and `llm_sentiment=0.8`.
- `build_signals()` only passes `llm_sentiment` the existing behavior knobs:
  classifier, headline cap, and news aliases. It does not pass a config-derived
  weight.
- `SourcesConfig` exposes the paid LLM signal toggle and headline cap, not
  signal-weight tuning.
- `docs/reference/analysis/scoring.md` documents weight as a multiplier whose
  current values are code constants and backtest calibration targets.
- Adding a single LLM-only weight knob would make an inconsistent tuning
  surface. If operators need tuning, it should be a unified signal-weight tuning
  design across all built-in signals.

Rejected:

- Adding a one-off LLM weight setting now. It is a config surface expansion
  without a current backtest-driven requirement.

## 2026-06-28 — CAPTURED-INDEX-DEFERRAL-RECHECK

Decision: keep the captured-date persistent index deferred.

Reason:

- `DataReader.read_captured_window()` already builds a per-reader in-memory
  captured-date index and reuses it until `JsonlStore.revision` changes.
- `DataReader._captured_date_index()` already logs `records/days/elapsed_ms`
  at DEBUG level, so operators can observe the scan size and rebuild cost.
- `tests/analysis/test_reader.py::test_captured_index_rebuild_logs_scan_scale`
  keeps that measurement hook covered.
- The persistent index design requires evidence that the in-memory rebuild has
  become a rebuild bottleneck. The repo has no current measurement proving that
  threshold has been crossed.
- An on-disk index would add schema, rebuild command, stale-index fallback, and
  cache invalidation behavior before it is justified.

Rejected:

- Promoting a bounded storage implementation now. The existing design document
  is enough until measurements show `records/days/elapsed_ms` costs threatening
  runtime budgets.

## 2026-06-28 — RSS-PROVIDER-POLICY-RECHECK

Decision: keep generic provider RSS discovery deferred, and promote only the
SEC official-source watchlist company filing feed slice to a Draft tech spec.

Reason:

- SEC documents Company Search RSS feeds and Filing Type filtering, so this
  slice can reuse Mimir's existing SEC company filing feed resolver.
- SEC fair-access guidance requires efficient requests, request moderation, and
  declared automated tooling. An opt-in default-false setting keeps request
  volume explicit.
- SEC publishes `company_tickers.json` but does not guarantee accuracy or scope,
  so the draft keeps the existing local mapping and fail-loud ambiguity policy.
- SEC-external provider discovery, HTML RSS link crawling, and vendor URL
  pattern inference still need provider-specific policy and ToS review.

Sources:

- SEC RSS Feeds:
  https://www.sec.gov/about/rss-feeds
- SEC Developer Resources:
  https://www.sec.gov/about/developer-resources
- SEC Webmaster FAQ:
  https://www.sec.gov/about/webmaster-frequently-asked-questions
- SEC `company_tickers.json`:
  https://www.sec.gov/files/company_tickers.json

Rejected:

- Implementing watchlist-based feed generation immediately. The backlog item was
  a provider-policy recheck, and a draft spec is the smallest safe product step.
- Generic live discovery. It would guess or crawl provider surfaces outside the
  verified SEC official-source boundary.

## 2026-06-28 — ENTRYPOINT-CAST-TYPE-CLEANUP

Decision: remove legacy `importlib.metadata.entry_points()` mapping fallbacks
from source and analysis plugin builders.

Reason:

- Mimir requires Python `>=3.14`, where `entry_points(group=...)` is the
  supported direct selection API.
- The fallback existed only to support older entry-point return shapes and was
  the last avoidable builder `cast()` surface.
- Existing plugin loader tests already cover name ordering, bad entry points,
  configured plugin inclusion, and default no-entry-point paths.

Source:

- Python docs, `importlib.metadata` entry points:
  https://docs.python.org/3/library/importlib.metadata.html#entry-points

Rejected:

- Keeping the compatibility branch as harmless. It targets unsupported Python
  versions and keeps static typing debt in two hot extension seams.

## 2026-06-28 — NORMALIZE-PAYLOAD-TYPE-CLEANUP

Decision: parse payloads explicitly in `normalize()` before constructing
`Record`, while keeping `Record`'s before-validator for JSONL deserialization.

Reason:

- `parse_payload()` is already the single dataset payload dispatch function.
- Explicit parsing makes the normalize boundary match the static `Record.payload`
  type and removes the local `type: ignore[arg-type]`.
- `Record` still accepts dict payloads from persisted JSONL, so storage
  deserialization behavior is unchanged.

Rejected:

- Adding a second helper around `Record` construction. The existing
  `parse_payload()` call is enough.

## 2026-06-28 — STOOQ-FLOAT-PARSER-TYPE-CLEANUP

Decision: remove the Stooq parser `type: ignore[arg-type]` by splitting the
`None` check from string sentinel handling.

Reason:

- `_f()` only needs to accept `None`, empty string, `N/D`, or a numeric string.
- `if value is None or value in ("", "N/D")` gives mypy enough information to
  prove `float(value)` receives a string.
- A helper or broader parser abstraction would add code without improving the
  source contract.

Rejected:

- Keeping the ignore as harmless debt; a one-line narrowing removes it and keeps
  strict typing cleaner.

## 2026-06-28 — DECISIONS-FOLLOWUP-DOC-TRUTH

Decision: once a follow-up loop is complete, remove the stale follow-up from
the earlier decision instead of leaving it as historical current-state text.

Reason:

- `DECISIONS.md` records durable rationale, but a `Follow-up:` block reads as
  active work.
- `WORKFLOW-CONCURRENCY-QUEUE` now has its own decision entry and verification
  evidence.
- Keeping the old follow-up in `PROJECT-STATE-ENTRYPOINTS` made the root state
  docs contradict themselves.

Rejected:

- Leaving the old follow-up for historical context. Git history already
  preserves it, and the newer workflow decision now carries the durable
  rationale.

## 2026-06-28 — BACKLOG-NOTES-DOC-TRUTH

Decision: completed backlog items should keep verification and rationale in
`WORKLOG.md` and `DECISIONS.md`, not as item-specific pre-implementation
warnings in `BACKLOG.md` Notes.

Reason:

- `BACKLOG.md` is the active queue and lightweight policy surface.
- Once `WORKFLOW-CONCURRENCY-QUEUE` moved to Done, the old note saying it still
  needed a RED guard became stale current-state wording.
- A generic evidence rule preserves the useful process constraint without
  implying completed work is still pending.

Rejected:

- Keeping a workflow-specific warning in Notes after completion, because it
  contradicts Done state and duplicates evidence already recorded in
  `WORKLOG.md`.

## 2026-06-28 — WORKFLOW-CONCURRENCY-QUEUE

Decision: set workflow-level `concurrency.queue: max` in the reusable scheduled
pipeline while keeping `cancel-in-progress: false`.

Reason:

- Mimir's hourly/daily/weekly/monthly schedulers all call `_pipeline.yml`, which
  uses one `collect` concurrency group.
- GitHub's default concurrency queue keeps only one pending run in a group.
  Later pending runs can replace earlier pending runs before they collect data.
- `queue: max` keeps up to 100 pending runs. That matches Mimir's data
  collection goal better than silently replacing scheduled runs.

Sources:

- GitHub Docs, control workflow/job concurrency:
  https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
- GitHub Docs, workflow syntax:
  https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub Docs, Actions limits:
  https://docs.github.com/en/actions/reference/limits

Rejected:

- `cancel-in-progress: true` remains off because GitHub documents that it cannot
  be combined with `queue: max`, and canceling in-progress collection would risk
  data gaps.

## 2026-06-28 — PROJECT-STATE-ENTRYPOINTS

Decision: add root project-state entrypoints as pointers, not a second planning
database.

Reason:

- The user requested `PLAN.md`, `BACKLOG.md`, `WORKLOG.md`, and `DECISIONS.md`
  as continuation sources.
- The repo already has canonical detail in `docs/IMPROVEMENTS.md`,
  `docs/architecture/improvement-catalog.md`,
  `docs/decisions/tech-spec/README.md`, and `docs/superpowers/plans/`.
- Thin root docs satisfy continuation needs while avoiding copied state that
  will drift.

External research recorded before implementation:

- GitHub Docs documents `concurrency.queue: max` for workflow/job concurrency:
  https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
- GitHub Docs workflow syntax also covers concurrency behavior:
  https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Finding: default queueing keeps one pending run in a concurrency group, while
  `queue: max` queues up to 100 pending runs. GitHub documents that
  `queue: max` cannot be used with `cancel-in-progress: true`.
