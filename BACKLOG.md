# Backlog

This file is the root queue. Canonical detail stays in:

- `docs/IMPROVEMENTS.md`
- `docs/architecture/improvement-catalog.md`

## Priority Policy

1. Stability and bug fixes
2. Testability and verification
3. Extensibility
4. Developer experience
5. Documentation
6. New features

Move a feature higher only when it materially advances Mimir's core purpose:
free, legal public-data collection and investment insight generation.

## Queue

1. `CAPTURED-INDEX-MEASUREMENT-RECHECK` — recheck whether current
   `DataReader._captured_date_index` measurement evidence proves
   `read_captured_window()` rebuild cost has crossed the persistent-index
   threshold; if not, keep the index deferred and queue the next bounded
   docs-truth or verification cleanup.

## Done

- `POST-RSS-DOCS-IMPLEMENTATION-SCAN` — current-state docs, CLI script
  metadata, README reference links, workflow queue claims, RSS boundaries, and
  test-count claims matched implementation; no stronger stale current-state
  doc claim was found.
- `GENERIC-RSS-DISCOVERY-BOUNDARY-RECHECK` — generic live discovery, SEC 외
  provider discovery, HTML RSS link crawling, and vendor URL pattern inference
  remain deferred; current RSS paths stay static catalog ids, explicit manual
  feeds, and official SEC helpers only.
- `R1O-SEC-WATCHLIST-FILING-FEEDS-RECHECK` — `sources.rss.sec.watchlist_company_filings`
  now opt-in generates SEC Company Search filing feeds from watchlist `us`
  symbols while keeping generic provider discovery, HTML RSS crawling, and
  vendor URL inference deferred.
- `DOCS-IMPLEMENTATION-CONSISTENCY-SCAN` — live improvement-catalog rows no
  longer pin stale static test counts; current verification belongs to the
  README test badge and docs health guard.
- `D3-TRANSLATION-DEFERRAL-RECHECK` — broad internal spec/roadmap translation
  stays deferred because root README x3 are trilingual while detailed project
  docs remain Korean-first; any future translation should be a bounded
  reference-doc translation slice with user or contributor evidence.
- `LLM-SIGNAL-WEIGHT-DEFERRAL-RECHECK` — one-off LLM signal weight YAML
  exposure stays deferred because built-in weights remain code constants and
  any user tuning should be a unified signal-weight tuning design across all
  signals.
- `CAPTURED-INDEX-DEFERRAL-RECHECK` — captured-date persistent index stays
  deferred because the C2a in-memory cache and `records/days/elapsed_ms`
  measurement hook exist, but repo evidence does not show a rebuild bottleneck
  crossing the implementation threshold.
- `RSS-PROVIDER-POLICY-RECHECK` — generic provider RSS discovery remains
  deferred, while the SEC-only watchlist company filing feed generation slice is
  promoted to a Draft tech spec as `R1o-SEC-WATCHLIST-FILING-FEEDS`.
- `ENTRYPOINT-CAST-TYPE-CLEANUP` — source and analysis plugin entry-point
  loaders now use Python 3.14 `entry_points(group=...)` directly instead of
  legacy mapping fallback casts.
- `NORMALIZE-PAYLOAD-TYPE-CLEANUP` — normalize now parses payloads before
  `Record` construction and payload dispatch uses a typed cast instead of local
  `type: ignore` comments.
- `STOOQ-FLOAT-PARSER-TYPE-CLEANUP` — Stooq optional numeric CSV fields are
  covered, and `_f()` no longer needs a local `type: ignore[arg-type]`.
- Fresh docs-truth scan — no stronger stale current-state claim remained after
  the backlog/decision follow-up cleanups; deferred items stay in the catalog
  until measurement or policy evidence changes.
- `DECISIONS-FOLLOWUP-DOC-TRUTH` — stale `PROJECT-STATE-ENTRYPOINTS`
  decision follow-up removed after `WORKFLOW-CONCURRENCY-QUEUE` completed.
- `BACKLOG-NOTES-DOC-TRUTH` — `BACKLOG.md` Notes now keep completed-item
  evidence policy generic instead of item-specific pre-implementation warnings.
- `WORKFLOW-CONCURRENCY-QUEUE` — `.github/workflows/_pipeline.yml` now uses
  `concurrency.queue: max` with `cancel-in-progress: false` so scheduled
  collection runs queue in the shared `collect` group.
- `PROJECT-STATE-ENTRYPOINTS` — root `PLAN.md`, `BACKLOG.md`, `WORKLOG.md`,
  and `DECISIONS.md` pointers added so future sessions can resume from repo
  documents plus git history.

## Notes

- `PROJECT-STATE-ENTRYPOINTS` must not duplicate the long backlog/catalog.
- Completed items keep verification evidence in `WORKLOG.md` and decision
  rationale in `DECISIONS.md`; Notes should not keep pre-implementation
  warnings after an item moves to Done.
- Remaining code-level casts are intentional: an invalid-object test double in
  `tests/core/test_normalize.py` and the pydantic payload dispatch boundary in
  `mimir/core/payloads.py`.
