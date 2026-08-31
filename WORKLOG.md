# Work Log

## 2026-08-31 — FRED-TERMS-SAFETY-BOUNDARY (MAIN INTEGRATION)

- Pinned `origin/main` at `9668d072a3bcf6ae22a339d8e934a5ec6117448f`;
  it was an ancestor of reviewed head
  `981f963676f58af639cfc0277dc14f39da5456b1` (`0 behind / 111 ahead`).
- Opened [PR #10](https://github.com/YouSangSon/Mimir/pull/10). GitHub reported
  the PR `MERGEABLE` / `CLEAN`; `ci / test` passed in 33 seconds at
  [run 33358537038 / job 99385242683](https://github.com/YouSangSon/Mimir/actions/runs/33358537038/job/99385242683).
- Squash-merged PR #10 to `main` as
  `06997d8ece316b3f00017d937050f6236eddd56f`. After fetching, the
  `origin/main` tree `26498c6e8b78971d1f3b4b2ddcfb3f6a3cf589ba` exactly matched the
  reviewed PR-head tree.
- No live-money action, credential change, data/report mutation, deployment,
  or provider request was performed. User-owned `CLAUDE.md`,
  `docs/superpowers/handoffs/`, and `uv.lock` remained untracked and unstaged.
- Current loop integration gates are closed. The finite next candidates remain
  `ECOS-PROVENANCE-RIGHTS-BOUNDARY` and `MANUAL-RSS-LEGAL-OWNERSHIP`.

## 2026-08-31 — FRED-TERMS-SAFETY-BOUNDARY (FINAL LOCAL GATES)

Goal: measure the complete implementation tree, consolidate it into one final
implementation commit, preserve user-owned artifacts, and leave integration
and remote ownership with the controller.

Verification:

- `uv run pytest -q` — `662 passed in 10.73s`.
- `COVERAGE_FILE=.superpowers/sdd/2026-08-31-fred-terms-safety-boundary/coverage-data uv run coverage run -m pytest` — `662 passed in 11.42s`; `coverage report --fail-under=80` — `8447` statements, `134` missed, `98%` (gate `80%`). The existing README EN/KO/ZH value was already `98%`, so no README was changed; each README keeps the exact `662` count in its badge and table.
- `uv run ruff check .` — `All checks passed!`; `uv run mypy mimir` — `Success: no issues found in 83 source files`; `git diff --check` — passed.
- `uv run pytest --collect-only -q | tail -1` — `662 tests collected in 0.53s`; exact dated-history invariant `git diff --exit-code HEAD -- docs/superpowers/plans docs/superpowers/specs docs/decisions/tech-spec` returned no diff.
- Explicit runtime/config/workflow/sample-env/current-doc/state scan found no executable FRED activation. The whitespace-tolerant multiline positional `SourceSpec("fred", ...)` registration scan also returned no match; allowed remaining hits are removal/terms notices, negative guards, decisions/worklog, or dated history.
- Credential-value scan of changed files in `f87895a..HEAD` returned no match without printing any candidate value.
- Cleanup: no Mimir pytest/coverage process, Podman container, or Kind cluster remains. The only coverage file outside the plan workspace is the pre-existing ignored `.coverage` (`Jun 18 14:51:54 2026`, `77824` bytes); the measured `coverage-data` is ignored under this SDD workspace. `data/` and `reports/` have no tracked or local files and are unchanged. `CLAUDE.md`, `docs/superpowers/handoffs/`, and `uv.lock` remain untracked and unstaged.

Review update:

- Final merge-review scoped re-review: APPROVE. The Important meta-less-plugin
  backfill preflight defect is addressed, the ECOS/KR fixture Minor is
  addressed, and no Critical or Important finding remains.

Consolidation:

- Plan checkpoint `f87895a` remains separate. One final implementation commit,
  `fix(sources): remove incompatible FRED integration`, covers reviewed range
  `f87895a..this implementation commit` after the approved correction wave.
- The approved wave reran focused backfill, full backfill, signals, doctor,
  ECOS-preservation, full pytest, isolated coverage, Ruff, mypy, docs,
  diff-check, and dated-history gates. Exact output is in the ignored final
  merge-review fix report.
- `CLAUDE.md`, `docs/superpowers/handoffs/`, and `uv.lock` remain user-owned
  untracked files and are not staged.

Pending:

- Controller-owned integration verification, PR, remote CI, and main merge
  remain pending. This phase performs no push or remote mutation.

## 2026-08-31 — FRED-TERMS-SAFETY-BOUNDARY (CURRENT DOCS)

Goal: align current operator and architecture documentation with the removed
FRED runtime while preserving dated plans, specs, and tech-spec history.

Changes:

- Added one current-surface guard covering adapter/runtime/config/workflow/env
  absence, trilingual removal notices with both official terms URLs, and an
  explicit active-doc list that excludes dated history.
- Updated README EN/KO/ZH to six built-in sources, ECOS-only built-in macro
  support, accurate throttler/`Registry` responsibilities, manual-RSS operator
  responsibility, written-permission re-enable conditions, and existing-data
  stop/identify/quarantine/approval handling.
- Updated current config, storage, extensibility, roadmap, catalog, improvement,
  decision, and backlog state. `FRED-TERMS-SAFETY-BOUNDARY` is Done.
  `ECOS-PROVENANCE-RIGHTS-BOUNDARY` must verify built-in/custom-series
  provenance, authoring institution, terms, commercial-use rights, attribution,
  and derived-output obligations. `MANUAL-RSS-LEGAL-OWNERSHIP` must inventory
  every manual URL, record owner/terms/decision/evidence date, reject
  unverifiable URLs, and guard configured URLs against provenance records.
- No tracked or local data/report artifact was deleted. Protected dated history
  and user-owned untracked files were not modified.

Verification:

- RED: `uv run pytest tests/test_readme_docs.py::test_current_docs_expose_no_builtin_fred_path -q` — failed on `README.md missing removal notice`, `1 failed in 0.18s`.
- `uv run pytest --collect-only -q | tail -1` — `662 tests collected in 0.61s`; README EN/KO/ZH badge and table counts updated to 662, coverage left at 98% pending Task 5.
- `uv run pytest tests/test_readme_docs.py -q` — `36 passed in 1.50s`.
- `uv run pytest -q` — `662 passed in 12.47s`.
- `uv run ruff check tests/test_readme_docs.py` — passed.
- `git diff --check` — passed.
- `git diff --exit-code HEAD -- docs/superpowers/plans docs/superpowers/specs docs/decisions/tech-spec` — passed with no diff.
- Explicit active-surface scan found no executable key/config/import/spec/backfill claim; remaining current FRED hits are removal/supersession notices only.
- Credential-pattern scan of Task 4 files returned no matches.

Review:

- EN/KO/ZH notices carry the same removal, two-source, permission, series-owner,
  obligations, and existing-data meanings.
- Current docs no longer instruct activation; dated plans/specs/tech specs remain
  untouched historical evidence.
- Final coverage, full Ruff, mypy, cleanup, independent reviews, and the final
  implementation commit/PR gates remain pending for Task 5.

Fix round 1 (post-review):

- Removed every unsupported ECOS legal-clearance conclusion. Current surfaces now
  state only that runtime support remains while built-in/custom-series
  provenance, authoring institution, controlling terms, commercial-use rights,
  attribution, and derived-output obligations await
  `ECOS-PROVENANCE-RIGHTS-BOUNDARY` verification.
- Strengthened the one current-doc guard to detect whitespace-tolerant positional
  `SourceSpec("fred", ...)` registration and retired import/key/settings/config/
  payload/workflow/env fragments across runtime plus README/reference/roadmap/
  catalog/improvement/backlog/decision/worklog/gate/plan surfaces. Dated
  plans/specs/tech specs remain excluded.
- Guarded EN/KO/ZH component phrases for both terms URLs,
  attribution-insufficient, written permission and series-owner rights,
  stop/identify/quarantine, and operator-approved deletion/rebuild. A later
  re-review found that this did not independently lock the explicit re-enable
  condition or downstream notice/terms/privacy/citation obligations.
- Redefined `MANUAL-RSS-LEGAL-OWNERSHIP`: operator responsibility wording is
  completed context; the unsolved result is a URL inventory with owner, terms,
  permission/commercial-use decision, evidence date, rejection of unverifiable
  URLs, and a configured-URL-to-provenance-record guard.
- RED after guard strengthening: focused test failed because roadmap lacked the
  finite boundary IDs, `1 failed in 0.22s`.
- GREEN: focused guard `1 passed in 0.17s`; docs suite `36 passed in 3.71s`;
  full suite `662 passed in 18.21s`; collect-only `662 tests collected in 0.52s`.
- Final-tree rerun after state evidence updates: docs `36 passed in 1.03s`, full
  suite `662 passed in 12.38s`, collect-only `662 tests collected in 0.64s`.
- `uv run ruff check tests/test_readme_docs.py`, `git diff --check`, exact dated
  history invariant, executable activation scan (including positional
  registration), unsupported ECOS-claim scan, and credential-pattern scan all
  passed with no matches where absence was expected.

Fix round 2 (post-re-review):

- Corrected round 1 evidence: the guard had preserved the permission and
  series-rights words but had not independently locked their explicit
  re-enable-only-after relationship or the downstream notice/terms/privacy/
  citation obligations.
- Added two exact assertions per README: the language-specific re-enable
  condition and the complete applicable-obligations phrase. Existing README
  prose required no translation changes.
- Restored-checkout rerun:
  `uv run pytest tests/test_readme_docs.py::test_current_docs_expose_no_builtin_fred_path -q`
  — `1 passed in 0.25s`.
- `uv run pytest tests/test_readme_docs.py -q` — `36 passed in 1.98s`.
- `uv run pytest -q` — `662 passed in 12.85s`.
- `uv run pytest --collect-only -q | tail -1` — `662 tests collected in 0.40s`.
- `uv run ruff check tests/test_readme_docs.py`, `git diff --check`, and the
  exact dated-history invariant passed. Active-surface activation, positional
  registration, unsupported ECOS-rights conclusion, and credential-pattern
  scans returned no matches.
- Final tracked-tree rerun: focused guard `1 passed in 0.03s`, docs suite
  `36 passed in 1.14s`, full suite `662 passed in 9.56s`, collect-only
  `662 tests collected in 0.37s`; Ruff, diff, history, active-surface,
  positional-registration, and credential scans passed.

## 2026-06-29 — CAPTURED-INDEX-MEASUREMENT-RECHECK

Goal: recheck whether current `DataReader._captured_date_index` measurement
evidence proves `read_captured_window()` rebuild cost has crossed the
persistent-index threshold.

Plan: `docs/superpowers/plans/2026-06-29-captured-index-measurement-recheck.md`

Research:

- `DataReader.read_captured_window()` still routes through
  `_captured_date_index()` and filters the in-memory captured-date buckets.
- `_captured_date_index()` still scans `JsonlStore.read_all(dataset)` once per
  dataset per `DataReader` while the store revision is unchanged, groups records
  by `captured_at.date()`, and logs `records/days/elapsed_ms`.
- `tests/analysis/test_reader.py` still covers rebuild logging, one scan reused
  across multiple captured windows, and cache invalidation after store changes.
- Local `data/` has 0 JSONL files, so this checkout has no measured corpus that
  proves rebuild cost crossed the persistent-index threshold.

Post-loop audit:

- `SOURCE-LEGALITY-ATTRIBUTION`: FRED API terms require a prominent
  non-endorsement notice and preserve series-owner rights; ECOS terms require
  source attribution, while `docs/reference/config/sources.md` accepts manual
  RSS URLs that the operator must verify. Official evidence:
  <https://fred.stlouisfed.org/docs/api/terms_of_use.html> and
  <https://ecos.bok.or.kr/api/#/AuthKeyApply>.
- `CONFIG-YAML-SYNTAX-ERROR-BOUNDARY`: `mimir/config.py` calls
  `yaml.safe_load()` outside the existing typed config-error boundaries.
- `CLI-DATE-ARGUMENT-BOUNDARY`: six CLI modules call `date.fromisoformat()`
  after argparse instead of using its native `type` validation.
- `REPORT-HTML-MOBILE-A11Y`: the static report renderers lack viewport metadata,
  responsive table containment, and scoped historical-table headers.
- `DOCTOR-MACRO-SINGLE-SCAN`: `mimir/doctor/checks.py` performs an initial macro
  scan and then repeats full reads for per-series freshness.
- `DELIVERY-CADENCE-CONTRACT`: delivery supports every `Cadence` value, but its
  behavioral tests currently exercise only `daily`.
- `CURRENT-HEALTH-DOC-TRUTH`: the audited stale set is limited to the exact
  coverage, fixed file-size, exhaustive catalog, and GitHub commit-back claims.

Verification:

- `uv run pytest tests/analysis/test_reader.py::test_captured_index_rebuild_logs_scan_scale tests/analysis/test_reader.py::test_read_captured_window_reuses_one_dataset_scan_for_multiple_windows tests/test_readme_docs.py::test_captured_date_persistent_index_recheck_keeps_measurement_based_deferral -q` — 3 passed
- `uv run pytest tests/test_readme_docs.py -q` — 35 passed
- `uv run pytest --collect-only -q | tail -1` — 668 tests collected
- `uv run pytest -q` — 668 passed
- `uv run coverage run -m pytest` plus `coverage report --fail-under=80` —
  668 passed, total coverage 98%
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched files found no real secrets; matches were existing
  `MIMIR_SEC_USER_AGENT` and WORKLOG placeholder/env-name wording.

Agent card:

- Owner: Codex
- State: verify -> review -> commit
- Merge gate: focused captured-index guards, docs suite, collect-only count,
  full pytest, ruff, mypy, diff-check, secrets scan, and review pass.

Review:

- Spec review: approved after bounding the docs-truth candidate, restoring
  priority order, and recording a candidate-to-evidence map.
- Quality review: approved after correcting the dataset-scoped cache wording
  and preserving the official FRED/ECOS evidence URLs.

Result:

- Persistent captured-date indexing remains deferred.
- No production code changed.
- A post-loop code, UI, docs, and official-source audit found stronger work than
  another signal-weight deferral recheck, so `BACKLOG.md` now queues
  `SOURCE-LEGALITY-ATTRIBUTION` first and preserves the other verified gaps.

## 2026-06-29 — POST-RSS-DOCS-IMPLEMENTATION-SCAN

Goal: run a fresh docs/implementation consistency scan after the generic RSS
discovery boundary recheck and queue the next evidence-backed item.

Plan: `docs/superpowers/plans/2026-06-29-post-rss-docs-implementation-scan.md`

Scan:

- Current-state stale-claim search across README, root state docs,
  `docs/IMPROVEMENTS.md`, `docs/architecture`, `docs/reference`, and
  `tests/test_readme_docs.py` found no contradictory current-state claim. Hits
  were docs-health guard literals, true deferred/future boundaries, or dated
  decision context.
- Test-count search found current README EN/KO/ZH `668 passing` claims and the
  docs guard regexes only; `uv run pytest --collect-only -q | tail -1`
  confirmed `668 tests collected`.
- `uv run pytest tests/test_pyproject_scripts.py -q` kept CLI script metadata
  and source entry points in sync.
- `uv run pytest tests/test_readme_docs.py::test_readme_links_all_reference_docs -q`
  kept README reference links backed by existing files.
- RSS boundary claims still match the resolver and builder contracts: static
  catalog ids, explicit manual RSS feeds, and official SEC helpers only.
- GitHub Actions `concurrency.queue: max` was checked against official GitHub
  docs and remains supported with `cancel-in-progress: false`:
  https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency

Next queue:

- `CAPTURED-INDEX-MEASUREMENT-RECHECK`: live catalog evidence says the
  persistent captured-date/partition index is still deferred until
  `DataReader._captured_date_index` measurements show rebuild cost crossing the
  bottleneck threshold. The measurement hook exists, but this scan found no
  current measurement proving the threshold has been crossed.

Verification:

- `uv run pytest tests/test_pyproject_scripts.py -q` — 3 passed
- `uv run pytest tests/test_readme_docs.py::test_readme_links_all_reference_docs -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 35 passed
- `uv run pytest --collect-only -q | tail -1` — 668 tests collected
- `uv run pytest -q` — 668 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched files found no real secrets; the only match was
  existing WORKLOG placeholder/env-name wording.

Agent card:

- Owner: Codex
- State: verify -> review -> commit
- Merge gate: docs suite, collect-only count, full pytest, ruff, mypy,
  diff-check, secrets scan, and review pass.

Review:

- Spec reviewer approved with no Critical, Important, or Minor findings.
- Quality reviewer approved with no Critical, Important, or Minor findings.

Result:

- No production code changed.
- No `DECISIONS.md` entry was added because the scan only queued the next
  evidence-backed item and did not change durable scope.

## 2026-06-28 — GENERIC-RSS-DISCOVERY-BOUNDARY-RECHECK

Goal: recheck the remaining generic provider RSS discovery boundary after R1o
and either keep it deferred with evidence or plan one official-source slice.

Plan: `docs/superpowers/plans/2026-06-28-generic-rss-discovery-boundary-recheck.md`

Research:

- Current code only supports static catalog ids, explicit manual RSS feeds, and
  official SEC helper paths. `resolve_rss_feeds()` does not do generic live
  discovery, SEC 외 provider discovery, HTML RSS link crawling, or vendor URL
  pattern inference.
- SEC official-source RSS coverage is already represented by the existing
  R1f/R1g/R1h/R1i-R1o decisions.
- Stooq official pages were not a clean static RSS promotion candidate because
  the public pages returned browser-verification behavior during research.
- FRED/St. Louis Fed has official RSS material, but compatibility evidence was
  not strong enough to promote a Mimir source slice in this loop.
- Finnhub, DART/OpenDART, ECOS, and Naver remain API/auth surfaces rather than
  keyless static RSS catalog candidates; pykrx/KRX remains GRAY/scraping-related.
- Deferred scope remains: generic live discovery, SEC 외 provider discovery,
  HTML RSS link crawling, vendor URL pattern inference.

TDD:

- RED: `uv run pytest tests/test_readme_docs.py::test_generic_rss_discovery_recheck_keeps_policy_boundary_deferred -q`
  failed because current docs did not yet record
  `GENERIC-RSS-DISCOVERY-BOUNDARY-RECHECK`.

Verification:

- `uv run pytest tests/test_readme_docs.py::test_generic_rss_discovery_recheck_keeps_policy_boundary_deferred -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 35 passed
- `uv run pytest --collect-only -q | tail -1` — 668 tests collected
- `uv run pytest -q` — 668 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched tracked files found no real secrets; matches were
  limited to existing config, CI, test, and placeholder names.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused docs guard, docs suite, collect-only count, full pytest,
  ruff, mypy, diff-check, secrets scan, and review pass.

Review:

- Spec reviewer approved with no Critical, Important, or Minor findings.
- Quality reviewer found one Important docs-guard weakness and one Minor
  worklog evidence gap; both were addressed and re-review approved.

Result:

- Generic RSS discovery remains deferred.
- No production code changed.
- `BACKLOG.md` now queues a fresh docs/implementation consistency scan.

## 2026-06-28 — R1O-SEC-WATCHLIST-FILING-FEEDS-RECHECK

Goal: recheck the R1o SEC watchlist filing feeds Draft spec and promote only
the smallest official-source slice if current contracts support it.

Plan: `docs/superpowers/plans/2026-06-28-r1o-sec-watchlist-filing-feeds-recheck.md`

Research:

- SEC RSS Feeds documents Company Search RSS/Atom output and Filing Type
  filtering.
- SEC Developer Resources and Webmaster FAQ require efficient automated access,
  request moderation, and a declared User-Agent/contact.
- SEC `company_tickers.json` is an official mapping source but still stays a
  local/operator-managed lookup unless the existing off-by-default refresh prep
  is enabled.
- Existing Mimir contracts already had `SecCompanyFilingFeed`,
  `resolve_rss_feeds()`, local ticker-to-CIK mapping, duplicate feed rejection,
  and `collect`/`backfill` watchlist loading.

TDD:

- RED: config focused tests failed because `SecWatchlistCompanyFilings` did not
  exist.
- RED: builder focused tests failed because `build_sources()` had no
  `watchlist` keyword argument.

Verification:

- `uv run pytest tests/sources/test_config.py::test_rss_sec_watchlist_company_filings_defaults_disabled_when_present tests/sources/test_config.py::test_rss_sec_watchlist_company_filings_parse_enabled_options -q` — 2 passed
- `uv run pytest tests/core/test_builder.py::test_build_sources_does_not_generate_sec_watchlist_feeds_by_default tests/core/test_builder.py::test_build_sources_generates_sec_watchlist_company_filing_feeds -q` — 2 passed
- `uv run pytest tests/test_collect.py::test_collect_cli_uses_watchlist_for_sec_watchlist_filing_feeds tests/test_backfill.py::test_main_uses_watchlist_for_sec_watchlist_filing_feeds -q` — 2 passed
- `uv run pytest tests/core/test_builder.py::test_build_sources_rejects_duplicate_manual_and_watchlist_sec_feed -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py::test_r1o_sec_watchlist_filing_feeds_recheck_promotes_implemented_slice -q` — 1 passed
- `uv run pytest tests/core/test_builder.py::test_build_sources_wraps_invalid_watchlist_sec_form tests/core/test_builder.py::test_build_sources_wraps_invalid_watchlist_sec_ticker tests/core/test_builder.py::test_build_sources_generates_sec_watchlist_company_filing_feeds tests/core/test_builder.py::test_build_sources_rejects_duplicate_manual_and_watchlist_sec_feed -q` — 4 passed
- `uv run pytest tests/sources/test_config.py tests/core/test_builder.py tests/test_collect.py tests/test_backfill.py tests/test_readme_docs.py -q` — 167 passed
- `uv run pytest --collect-only -q | tail -1` — 667 tests collected
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- `uv run pytest -q` — 667 passed
- Secrets scan on touched files found only placeholder/config wording such as
  `STOOQ_API_KEY`, `ANTHROPIC_API_KEY`, `.env`, GitHub Secrets wording, test
  keys, and field names.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused source/config/docs guards, related suite, collect-only
  count, full pytest, ruff, mypy, diff-check, secrets scan, and review pass.

Review:

- Spec reviewer approved with no Critical, Important, or Minor findings.
- Quality reviewer found no Critical or Important issues. Its Minor note about
  blank SEC form validation through the watchlist path was addressed with
  `test_build_sources_wraps_invalid_watchlist_sec_form`; re-review approved.

Result:

- `sources.rss.sec.watchlist_company_filings` is implemented as default-false
  opt-in config.
- Enabled config generates SEC Company Search filing feeds only from
  `watchlist.yaml` `us` symbols.
- Generated selections reuse `SecCompanyFilingFeed`, existing local
  ticker-to-CIK mapping/refresh, duplicate feed rejection, and RSS source
  User-Agent behavior.
- Generic provider discovery, SEC-external provider discovery, HTML RSS
  crawling, and vendor URL inference remain deferred.
- `BACKLOG.md` now queues the remaining generic provider RSS discovery boundary
  recheck.

## 2026-06-28 — DOCS-IMPLEMENTATION-CONSISTENCY-SCAN

Goal: run a fresh docs/implementation consistency scan after the deferred-item
rechecks and queue the next evidence-backed cleanup.

Plan: `docs/superpowers/plans/2026-06-28-docs-implementation-consistency-scan.md`

Research:

- README EN/KO/ZH links to key architecture and reference docs are present and
  the target files exist.
- Old fixed test counts remain only in historical worklog/plan material except
  for three live improvement-catalog summary rows.
- `docs/architecture/improvement-catalog.md` already says latest verification is
  tracked by the README test badge and docs health guard, so row-level static
  test counts are redundant.

TDD:

- RED: `uv run pytest tests/test_readme_docs.py::test_improvement_catalog_does_not_pin_static_test_counts -q`
  failed on `코드 + 테스트(144)` in the live catalog summary.

Verification:

- `uv run pytest tests/test_readme_docs.py::test_improvement_catalog_does_not_pin_static_test_counts -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 34 passed
- `uv run pytest --collect-only -q | tail -1` — 658 tests collected
- `uv run pytest -q` — 658 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched files found only existing placeholder/config wording,
  GitHub Secrets wording, and worklog review-gate text.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused docs guard, docs suite, collect-only count, full pytest,
  ruff, mypy, diff-check, secrets scan, and review pass.

Review:

- Quality reviewer found no Critical or Important issues. Its Minor note about
  replacing pending worklog wording was addressed before commit.

Result:

- Static historical test counts were removed from the live improvement-catalog
  summary rows.
- `BACKLOG.md` now queues the R1o SEC watchlist filing feeds Draft spec recheck.

## 2026-06-28 — D3-TRANSLATION-DEFERRAL-RECHECK

Goal: recheck the D3 internal spec/roadmap translation deferral against the
current README/reference-doc language split.

Plan: `docs/superpowers/plans/2026-06-28-d3-translation-deferral-recheck.md`

Research:

- Root README files keep English/Korean/Chinese language switchers and localized
  Further Reading sections.
- The README Further Reading sections link into detailed docs under `docs/`,
  including reference docs that are currently Korean-first.
- `docs/superpowers/plans/2026-06-23-runtime-config-doc-truth.md` records the
  policy: project docs under `docs/` are Korean-first while identifiers and file
  paths stay English.
- The internal spec/plan/tech-spec set is over 100 Markdown files, so wholesale
  translation would create a stale-translation maintenance surface.

TDD:

- RED: `uv run pytest tests/test_readme_docs.py::test_d3_translation_deferral_recheck_keeps_readmes_trilingual_and_docs_korean_first -q`
  failed because root project docs did not yet record
  `D3-TRANSLATION-DEFERRAL-RECHECK`.

Verification:

- `uv run pytest tests/test_readme_docs.py::test_d3_translation_deferral_recheck_keeps_readmes_trilingual_and_docs_korean_first -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 33 passed
- `uv run pytest --collect-only -q | tail -1` — 657 tests collected
- `uv run pytest -q` — 657 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched files found only existing placeholder/config wording,
  GitHub Secrets wording, and worklog review-gate text.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused docs guard, docs suite, collect-only count, full pytest,
  ruff, mypy, diff-check, secrets scan, and review pass.

Review:

- Spec reviewer found no Critical issues. Its Important notes were addressed by
  adding README language-boundary notes and replacing an exact internal-doc count
  with `100+`.
- Quality reviewer found no Critical issues. Its Important note about the
  post-review plan-file edit was addressed by including the plan file in the
  exact commit list.

Result:

- Broad internal spec/roadmap translation remains deferred.
- The current contract is trilingual root README navigation plus Korean-first
  detailed docs under `docs/`.
- Any future translation should be a bounded reference-doc translation slice
  backed by user or contributor evidence.

## 2026-06-28 — LLM-SIGNAL-WEIGHT-DEFERRAL-RECHECK

Goal: recheck the LLM signal weight YAML exposure deferral and promote tuning
only if current repo evidence supports a unified signal-weight tuning spec.

Plan: `docs/superpowers/plans/2026-06-28-llm-signal-weight-deferral-recheck.md`

Research:

- Built-in signal modules still use code constants for weights:
  `price_momentum=1.0`, `filing_event=0.8`, `news_volume=0.5`,
  `macro_regime=0.3`, and `llm_sentiment=0.8`.
- `build_signals()` does not pass a config-derived weight to
  `LlmSentimentSignal`; the existing LLM knobs are enablement, headline cap,
  classifier injection, and aliases.
- `SourcesConfig` and `_TopLevelSourcesConfig` expose `llm_sentiment_enabled`
  and `llm_sentiment_max_headlines`, not signal-weight tuning.
- `docs/reference/analysis/scoring.md` already documents weights as code
  constants and backtest calibration targets rather than user YAML.

TDD:

- RED: `uv run pytest tests/test_readme_docs.py::test_llm_signal_weight_yaml_deferral_recheck_keeps_unified_weight_tuning_deferred -q`
  first failed on a test assumption about `LlmSentimentSignal`; after correcting
  the guard to match the constructor-default contract, it failed because root
  project docs did not yet record `LLM-SIGNAL-WEIGHT-DEFERRAL-RECHECK`.

Verification:

- `uv run pytest tests/test_readme_docs.py::test_llm_signal_weight_yaml_deferral_recheck_keeps_unified_weight_tuning_deferred -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 32 passed
- `uv run pytest --collect-only -q | tail -1` — 656 tests collected
- `uv run pytest -q` — 656 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched files found only placeholders, GitHub Secrets wording,
  docs references, and existing worklog mentions.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused docs guard, docs suite, collect-only count, full pytest,
  ruff, mypy, diff-check, secrets scan, and review pass.

Review:

- Spec reviewer found no Critical or Important issues. Its Minor note about
  named-key string guards was addressed by also checking the parsed
  `SourcesConfig` field declarations for weight fields.
- Quality reviewer found no Critical, Important, or Minor issues.

Result:

- One-off LLM signal weight YAML exposure remains deferred.
- Built-in signal weights stay code constants and any future operator tuning
  should be designed as unified signal-weight tuning across all signals.
- `BACKLOG.md` now queues the D3 internal spec/roadmap translation deferral
  recheck next.
- README EN/KO/ZH test counts updated to 656.

## 2026-06-28 — CAPTURED-INDEX-DEFERRAL-RECHECK

Goal: recheck the captured-date persistent index deferral and promote storage
work only if current repo evidence shows the in-memory rebuild has become a
rebuild bottleneck.

Plan: `docs/superpowers/plans/2026-06-28-captured-index-deferral-recheck.md`

Research:

- `mimir/storage/reader.py` already builds a per-reader captured-date
  in-memory index and invalidates it on `JsonlStore.revision`.
- The rebuild path logs `records/days/elapsed_ms` at DEBUG level, which is the
  measurement hook needed before deciding whether an on-disk index is worth the
  extra schema and stale-index behavior.
- `tests/analysis/test_reader.py::test_captured_index_rebuild_logs_scan_scale`
  asserts one rebuild log with record/day scale fields.
- `docs/superpowers/specs/2026-06-19-captured-date-persistent-index-design.md`
  remains a design-only, unimplemented spec that says to build only after
  measurements prove the rebuild bottleneck.

TDD:

- RED: `uv run pytest tests/test_readme_docs.py::test_captured_date_persistent_index_recheck_keeps_measurement_based_deferral -q`
  failed because root project docs did not yet record
  `CAPTURED-INDEX-DEFERRAL-RECHECK`.

Verification:

- `uv run pytest tests/test_readme_docs.py::test_captured_date_persistent_index_recheck_keeps_measurement_based_deferral -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 31 passed
- `uv run pytest --collect-only -q | tail -1` — 655 tests collected
- `uv run pytest -q` — 655 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched files found only placeholders, GitHub Secrets wording,
  public docs references, and existing worklog mentions.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused docs guard, docs suite, collect-only count, full pytest,
  ruff, mypy, diff-check, secrets scan, and review pass.

Review:

- Spec reviewer found no Critical or Important issues and accepted the
  measurement-based deferral contract.
- Quality reviewer found no Critical or Important issues. Two Minor guard
  precision concerns were addressed by making the test rely on the existing
  runtime log-scale test and by checking the captured-index rows/sections in
  current docs instead of broad file-wide terms.

Result:

- Captured-date persistent index remains deferred.
- Existing C2a in-memory cache and `records/days/elapsed_ms` measurement logs
  remain the unblock evidence path.
- `BACKLOG.md` now queues the LLM signal weight YAML exposure deferral recheck
  next.
- README EN/KO/ZH test counts updated to 655.

## 2026-06-28 — RSS-PROVIDER-POLICY-RECHECK

Goal: recheck the deferred RSS discovery/provider-policy backlog item and
promote only a legal, official-source slice if current evidence supports it.

Plan: `docs/superpowers/plans/2026-06-28-rss-provider-policy-recheck.md`

Research:

- SEC RSS Feeds documents that EDGAR Company Search results can be captured as
  RSS feeds and filtered by filing type.
- SEC Developer Resources and Webmaster FAQ document efficient scripting,
  request moderation, declared User-Agent headers, and a 10 requests/sec maximum
  access-rate guideline.
- SEC Webmaster FAQ lists `company_tickers.json` for ticker/CIK/company-name
  associations but says SEC does not guarantee accuracy or scope.
- Existing Mimir code already implements `sources.rss.sec.company_filings`,
  ticker input, local `company_tickers.json` lookup, and off-by-default mapping
  refresh. Generic provider discovery remains outside the verified SEC boundary.

TDD:

- RED: `uv run pytest tests/test_readme_docs.py::test_rss_provider_policy_recheck_promotes_only_sec_watchlist_spec -q`
  failed because the R1o draft tech spec did not exist.

Verification:

- `uv run pytest tests/test_readme_docs.py::test_rss_provider_policy_recheck_promotes_only_sec_watchlist_spec -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 30 passed
- `uv run pytest --collect-only -q | tail -1` — 654 tests collected
- `uv run pytest -q` — 654 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched files found only placeholders, public SEC URLs, and
  existing docs/test references.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused docs guard, docs suite, collect-only count, full pytest,
  ruff, mypy, diff-check, secrets scan, and review pass.

Review:

- Spec reviewer found no Critical or Important issues; a Minor citation-guard
  concern was resolved by requiring the R1o spec and `DECISIONS.md` to keep the
  official SEC source names and URLs.
- Quality reviewer found one P2 stale-current-doc issue in
  `docs/architecture/extensibility/README.md`; the doc now points watchlist SEC
  feed generation to the R1o Draft spec, and the guard scans current docs for
  stale deferred wording.
- Re-review approved with no remaining findings.

Result:

- Generic provider RSS discovery remains deferred.
- `R1o-SEC-WATCHLIST-FILING-FEEDS` is a Draft tech spec for an SEC-only,
  default-false, opt-in watchlist company filing feed generation slice.
- `BACKLOG.md` now queues captured-date persistent index deferral recheck next.
- README EN/KO/ZH test counts updated to 654.

## 2026-06-28 — ENTRYPOINT-CAST-TYPE-CLEANUP

Goal: remove remaining avoidable `cast()` calls from plugin entry-point loaders
without changing source or analysis plugin discovery semantics.

Plan: `docs/superpowers/plans/2026-06-28-entrypoint-cast-type-cleanup.md`

Research:

- Code audit found the remaining builder casts only inside legacy
  `importlib.metadata.entry_points()` mapping fallbacks.
- `pyproject.toml` requires Python `>=3.14`, so Mimir does not need old
  entry-point dictionary compatibility.
- Python's official `importlib.metadata` docs document direct
  `entry_points(group=...)` selection, matching the existing tests'
  monkeypatch contract.

TDD:

- RED: `uv run pytest tests/core/test_builder.py::test_source_entry_point_loader_does_not_keep_legacy_cast tests/analysis/test_builder.py::test_signal_entry_point_loader_does_not_keep_legacy_cast -q`
  failed because both loaders still contained `cast(...)`.

Verification:

- `uv run pytest tests/core/test_builder.py::test_source_entry_point_loader_does_not_keep_legacy_cast tests/analysis/test_builder.py::test_signal_entry_point_loader_does_not_keep_legacy_cast -q` — 2 passed
- `uv run pytest tests/core/test_builder.py tests/analysis/test_builder.py -q` — 77 passed
- `uv run mypy mimir/core/builder.py mimir/analysis/builder.py` — passed
- `uv run pytest --collect-only -q | tail -1` — 653 tests collected
- `uv run pytest tests/test_readme_docs.py -q` — passed
- `uv run pytest -q` — passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused entry-point cast guards, core/analysis builder suites,
  docs suite, collect-only count, full pytest, ruff, mypy, diff-check, and
  review pass.

Result:

- Source and analysis entry-point loaders now call
  `importlib.metadata.entry_points(group=...)` directly.
- Legacy mapping fallback imports and casts were removed.
- README EN/KO/ZH test counts updated to 653.
- Backlog reordered to the deferred RSS discovery/provider-policy evidence
  scan.

## 2026-06-28 — NORMALIZE-PAYLOAD-TYPE-CLEANUP

Goal: remove payload-boundary `type: ignore` comments without changing payload
validation or storage semantics.

Plan: `docs/superpowers/plans/2026-06-28-normalize-payload-type-cleanup.md`

Research:

- `normalize()` passed a raw payload dict into `Record` and relied on the
  `Record` before-validator to parse it, which worked at runtime but required a
  local `type: ignore[arg-type]`.
- `parse_payload()` already owns dataset-specific payload dispatch, so
  `normalize()` can call it before `Record` construction.
- `parse_payload()` still needs one `cast(Payload, ...)` because pydantic's
  `model_validate()` return type is wider than the validated union.

TDD:

- RED: `uv run pytest tests/core/test_normalize.py::test_payload_boundary_does_not_need_type_ignore_comments -q`
  failed while `normalize.py`, `payloads.py`, and the invalid-object test still
  contained local `type: ignore` comments.

Verification:

- `uv run pytest tests/core/test_normalize.py::test_payload_boundary_does_not_need_type_ignore_comments -q` — 1 passed
- `uv run pytest tests/core/test_normalize.py -q` — 4 passed
- `uv run pytest tests/core/test_payloads.py -q` — 35 passed
- `uv run pytest tests/test_readme_docs.py -q` — 29 passed
- `uv run pytest --collect-only -q | tail -1` — 651 tests collected
- `uv run pytest -q` — 651 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused payload-boundary guard, normalize tests, payload tests,
  docs suite, collect-only count, full pytest, ruff, mypy, diff-check, and
  review pass.
- Review note: quality review flagged the source-text guard as intentionally
  narrow and brittle; keep it scoped to this debt-removal guard only.

Result:

- `normalize()` now passes `parse_payload(meta.dataset, raw.payload)` into
  `Record`.
- `parse_payload()` uses `cast(Payload, model.model_validate(data))` instead of
  a local return-value ignore.
- The intentionally invalid normalize test uses `cast(RawRecord, Bad())`.
- README EN/KO/ZH test counts updated to 651.

## 2026-06-28 — STOOQ-FLOAT-PARSER-TYPE-CLEANUP

Goal: remove a local `type: ignore[arg-type]` from the Stooq numeric parser
without changing Stooq CSV semantics.

Plan: `docs/superpowers/plans/2026-06-28-stooq-float-parser-type-cleanup.md`

Research:

- Code audit found `mimir/sources/stooq.py::_f()` used `# type: ignore[arg-type]`
  because the `None` and string sentinel check did not narrow cleanly for mypy.
- Existing Stooq parser behavior already treated optional `N/D` fields as
  missing values; the loop needed coverage plus a smaller narrowing expression.

TDD:

- RED: `uv run pytest tests/sources/test_stooq.py::test_stooq_parser_does_not_need_arg_type_ignore -q`
  failed because the local ignore was still present.
- Characterization: `uv run pytest tests/sources/test_stooq.py::test_stooq_optional_numeric_nd_values_parse_as_none -q`
  passed before the implementation change, confirming existing `N/D` behavior.

Verification:

- `uv run pytest tests/sources/test_stooq.py::test_stooq_parser_does_not_need_arg_type_ignore -q` — 1 passed
- `uv run pytest tests/sources/test_stooq.py::test_stooq_optional_numeric_nd_values_parse_as_none -q` — 1 passed
- `uv run pytest tests/sources/test_stooq.py -q` — 5 passed
- `uv run pytest tests/test_readme_docs.py -q` — 29 passed
- `uv run pytest --collect-only -q | tail -1` — 650 tests collected
- `uv run pytest -q` — 650 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused Stooq tests, Stooq suite, docs suite, collect-only count,
  full pytest, ruff, mypy, diff-check, and review pass.

Result:

- `_f()` now narrows `None` separately before `float(value)`.
- Stooq optional numeric `N/D` and empty fields are covered.
- README EN/KO/ZH test counts updated to 650.

## 2026-06-28 — DECISIONS-FOLLOWUP-DOC-TRUTH

Goal: remove stale `PROJECT-STATE-ENTRYPOINTS` follow-up text after the workflow
queue loop completed.

Plan: `docs/superpowers/plans/2026-06-28-decisions-followup-doc-truth.md`

Research:

- Docs-truth scan found `DECISIONS.md` still saying
  `WORKFLOW-CONCURRENCY-QUEUE` should be a separate loop with a workflow guard.
- `WORKFLOW-CONCURRENCY-QUEUE` was already completed in `244aa72`.

TDD:

- RED: `uv run pytest tests/test_readme_docs.py::test_project_state_decision_does_not_keep_completed_workflow_followup -q`
  failed because the stale follow-up remained in `DECISIONS.md`.

Verification:

- `uv run pytest tests/test_readme_docs.py::test_project_state_decision_does_not_keep_completed_workflow_followup -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 29 passed
- `uv run pytest --collect-only -q | tail -1` — 648 tests collected
- `uv run pytest -q` — 648 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused docs guard, docs suite, collect-only count, full pytest,
  ruff, mypy, diff-check, and review pass.

Result:

- Removed stale workflow-queue follow-up from the project-state decision.
- `PLAN.md` points at `DECISIONS-FOLLOWUP-DOC-TRUTH`.
- `BACKLOG.md` Done records both completed root-state cleanup loops.
- README EN/KO/ZH test counts updated to 648.

## 2026-06-28 — BACKLOG-NOTES-DOC-TRUTH

Goal: stop `BACKLOG.md` Notes from describing completed workflow-queue work as
if it still needs a pre-implementation guard.

Plan: `docs/superpowers/plans/2026-06-28-backlog-notes-doc-truth.md`

Research:

- Repo scan found `WORKFLOW-CONCURRENCY-QUEUE` in `BACKLOG.md` Done while Notes
  still said it needed its own RED workflow guard before changing YAML.
- The workflow guard and YAML change were already committed in `244aa72`.

TDD:

- RED: `uv run pytest tests/test_readme_docs.py::test_backlog_notes_do_not_treat_completed_workflow_queue_as_pending -q`
  failed on the stale Notes wording.

Verification:

- `uv run pytest tests/test_readme_docs.py::test_backlog_notes_do_not_treat_completed_workflow_queue_as_pending -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 28 passed
- `uv run pytest --collect-only -q | tail -1` — 647 tests collected
- `uv run pytest -q` — 647 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched files found only placeholders, docs references, and
  existing test strings.

Review:

- Initial spec review flagged unrelated untracked continuation files; corrected
  review scoped to intended commit files approved with no findings.
- Quality review found one Minor guard-strength concern; the guard now also
  rejects item-specific `WORKFLOW-CONCURRENCY-QUEUE` Notes after Done.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused docs guard, docs suite, collect-only count, full pytest,
  ruff, mypy, diff-check, and review pass.

Result:

- `BACKLOG.md` Notes now use a generic completed-item evidence rule.
- `PLAN.md` points at `BACKLOG-NOTES-DOC-TRUTH`.
- README EN/KO/ZH test counts updated to 647.

## 2026-06-28 — WORKFLOW-CONCURRENCY-QUEUE

Goal: preserve all pending scheduled collection runs by queueing the reusable
pipeline's shared `collect` concurrency group.

Plan: `docs/superpowers/plans/2026-06-28-workflow-concurrency-queue.md`

Research:

- GitHub Docs documents workflow/job concurrency queueing and `queue: max`.
- GitHub Docs says `queue: max` queues up to 100 pending runs and cannot be
  combined with `cancel-in-progress: true`.
- Mimir already used `concurrency.group: collect` and
  `cancel-in-progress: false`, but without a queue policy GitHub keeps only one
  pending run by default.

TDD:

- RED: `uv run pytest tests/test_workflows.py::test_reusable_pipeline_queues_pending_collect_runs -q`
  failed because `_pipeline.yml` had no `queue: max`.

Verification:

- `uv run pytest tests/test_workflows.py::test_reusable_pipeline_queues_pending_collect_runs -q` — 1 passed
- `uv run pytest tests/test_workflows.py -q` — 4 passed
- `uv run pytest tests/test_readme_docs.py -q` — 27 passed
- `uv run pytest --collect-only -q | tail -1` — 646 tests collected
- `uv run pytest -q` — 646 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed
- Secrets scan on touched files found only placeholders and existing GitHub
  Actions `secrets.*` references.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused workflow guard, workflow test file, docs guard, full
  pytest, ruff, mypy, and diff-check pass.

Result:

- `_pipeline.yml` now sets `concurrency.queue: max` with
  `cancel-in-progress: false`.
- README EN/KO/ZH test counts updated to 646.
- Spec review approved with no findings.
- Quality reviewer did not return before commit; controller gates passed.

## 2026-06-28 — PROJECT-STATE-ENTRYPOINTS

Goal: make root repo documents the starting point for continuation without
duplicating the canonical docs under `docs/`.

Plan: `docs/superpowers/plans/2026-06-28-project-state-entrypoints.md`

Research:

- Repo inspection found no root `PLAN.md`, `BACKLOG.md`, `WORKLOG.md`, or
  `DECISIONS.md`.
- Existing canonical state already lives in `docs/IMPROVEMENTS.md`,
  `docs/architecture/improvement-catalog.md`,
  `docs/decisions/tech-spec/README.md`, `docs/superpowers/plans/`, git history,
  and committed project docs.

TDD:

- RED: `uv run pytest tests/test_readme_docs.py::test_root_project_state_entrypoints_link_canonical_sources -q`
  failed because `PLAN.md` was missing.

Verification:

- `uv run pytest tests/test_readme_docs.py::test_root_project_state_entrypoints_link_canonical_sources -q` — 1 passed
- `uv run pytest tests/test_readme_docs.py -q` — 27 passed
- `uv run pytest --collect-only -q | tail -1` — 645 tests collected
- `uv run pytest -q` — 645 passed
- `uv run ruff check .` — passed
- `uv run mypy mimir` — passed
- `git diff --check` — passed

Review:

- Spec review found that root entrypoints initially referenced local scratch
  state; fixed by keeping root docs pointed at tracked docs and git history only.

Agent card:

- Owner: Codex
- State: review -> commit
- Merge gate: focused docs test, docs test suite, full pytest, ruff, mypy, and
  diff-check pass.

Result:

- Root project-state entrypoints added as pointers to canonical docs.
- README EN/KO/ZH test counts updated to 645.
- Backlog reordered so `WORKFLOW-CONCURRENCY-QUEUE` is next.
