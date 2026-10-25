# Delivery Gates

This is the current evidence ledger. `GOAL.md` is stable; `PLAN.md` names the
active loop; dated detail stays in `WORKLOG.md` and `DECISIONS.md`.

## Global

- Source terms and provenance must be verified from current official sources.
- Official terms incompatible with the intended built-in use fail closed before
  that source's network or data writes. Existing GRAY-source policy is preserved.
- Trust-boundary validation, error handling, and accessibility are not optional.
- Focused tests must prove RED then GREEN for changed behavior.
- Required CI runs full pytest and coverage `>=80%`. Current user policy limits
  local execution to relevant lightweight sequential units. Ruff, mypy, docs
  guards, diff-check, secrets scan and independent required review must pass.
- Stage and commit only loop-owned files. Never push, deploy, publish, change
  credentials, or perform live-money actions without explicit approval.
- Preserve user-owned untracked files and clean only processes or temporary
  resources created by this loop.

## Current Loop — PORTFOLIO / RUNTIME VERIFICATION (2026-10-25)

- PR19 문서 CI40114726727: PASS, 746개 테스트·프로덕션97%. main1146307 tree는 리뷰한 fd2e268과 같고 소스·테스트·실행 설정은 구현 main410c876과 같다.
- Actual installed CLI, synthetic/offline data: 16 command checks passed. Prices/news45 each → insights8, historical1, evaluation buckets3. Invalid date exits2; malformed YAML and missing source evidence exit1 without echoing input; failure attempts preserve JSONL hashes. Empty-store report and credential-free Telegram false verified.
- Browser: actual generated dashboard375px, report1280px; no document overflow, unsafe href or console errors. ArrowRight scrolls a named table; index→report link works; stored publisherA survives current configB. Pages visibly label synthetic values; these are not investment results.
- Cleanup: owned SSH terminal PTY terminated, local HTTP59682 exited, browser servers/tabs stopped, viewport reset. Four further merged local/remote branches deleted after exact PR/tree/unique-commit/worktree audit. Historical main, unmerged macro-policy branch and active verification branch remain.
- Durable evidence: resume `자료수집/2026-10-25/mimir-portfolio/{source-provenance,cli-demo,cleanup}/`; no resume push/merge. Temporary demo copies removed only after byte-for-byte evidence verification.
- VM gate: 미통과. 이번 재개에서 TCP22(5.03초 timeout), 실제 Orca alias/config(요청 호스트·port22, proxy 없음), 기존 SSH transport(없음)를 확인했다. 제공사 탭은 다른 browser session이 사용 중이라 제어하지 않았다. 현재 콘솔·청구량·guest 상태는 미검증이다. 인증정보 전송이나 VM 쓰기·배포·잠금·workload는 없었다. 이번 차단 확인은 1회이며 이전 Goal 횟수·마감은 과거 기록이다.

## Previous Loop — ECOS / MANUAL-RSS SOURCE PROVENANCE (2026-10-25)

- Official research: exact default BOK monthly rate only; target-bound structural evidence for custom ECOS/manual RSS. Canonical contract: `docs/reference/config/sources.md` §4.4. Built-in RSS is unverified discovery evidence.
- RED: seven original boundaries; review bypass regressions 8 failed / 1 passed; unrelated legacy bucket scope regression failed.
- Focused GREEN before last scope fix: source/config/payload/builder/catalog 210 passed; actual attribution 8 passed; related analysis/report/CLI 199 passed; final review regressions and render/evaluation units 139 passed.
- Final scoped local units: 680 passed in 9.51s; their `mimir/*` coverage is 94% (partial scope, not the full-suite metric). Strict mypy: 84 source files clean; Ruff/diff-check pass. Independent Astra final re-review and separate quality review found no Critical/Important issues. Full free remote CI PASS: PR18/run40113216793, 746 tests, production97% (3443 statements/87 missed). Main410c876 tree equals reviewed c7c5453.
- VM billing screen: 9.9 MB / 3 TB, estimated overage zero; aggregation time 2026-10-24 13:07:39, timezone unspecified. SSH TCP 22 connection did not establish. Owned terminal confirmed closed; no VM lock or workload acquired.

## Previous Loop — CURRENT-HEALTH-DOC-TRUTH (2026-10-25)

- Doc-only changes: source/test tree equality to `848ff80` reuses its 701-test,
  97% production coverage, strict mypy and Ruff evidence.
- Docs guard: 36 passed; diff-check, source/test equality and independent review pass.
- Initial docs failures preserved completed-ID/health-owner contracts in the corrected text. PR #17 CI `40107271983` passed; main `3d777bc` equals reviewed `9afc8e1`.
- Cadence PR #16: CI `40106816741` passed; main `b902c89` equals reviewed `848ff80`.

## Previous Loop — DELIVERY-CADENCE-CONTRACT (2026-10-25)

- Existing runtime behavior is exercised with one four-cadence parameterized test.
- Focused delivery/digest/pipeline tests: 21 passed. Final full suite: 701 passed;
  production coverage 97%, mypy (83 files), Ruff and diff-check pass.
- Independent read-only spec/quality review: no Important/Critical finding. PR #16 CI `40106816741` passed; main `b902c89` matches reviewed head.
- Report UI PR #15: CI `40106364995` passed; main `70f533b` equals reviewed `bedd244`.

## Previous Loop — REPORT-HTML-MOBILE-A11Y (2026-10-25)

- Prior RED: nine focused accessibility cases; focused GREEN: 53 report tests.
- Independent spec/quality review: no Critical/Important issue.
- Final browser: 48 page/theme/viewport combinations (six populated/empty/error
  pages × dark/light × 320/375/768/1280px) have no document overflow or measured
  text contrast below 4.5:1. Keyboard Tab/focus outline/ArrowRight table scrolling,
  dashboard→status error and index→report→index navigation pass; no console errors.
  Four screenshots were visually inspected; data is explicitly synthetic.
- Final local gates: 698 tests passed; `mimir/*` coverage 97%, strict mypy
  (83 files), Ruff, and diff-check pass. Final logs: `/tmp/mimir-20261025-ui/final-gates/`.
- CI/main integration: PASS — PR #15, CI run `40106364995`, main `70f533b`.

## Previous Loop — DOCTOR-MACRO-SINGLE-SCAN (2026-10-24)

- RED: same findings but four macro reads; GREEN: one macro read.
- Focused doctor/dashboard suite: 41 passed.
- Independent spec/quality review, Ruff and diff-check: PASS.
- Full coverage suite: 689 passed; production `mimir/*` coverage 97% (80% gate).
- Strict mypy: 83 source files clean. PR #14 CI run `39986163175` passed;
  squash main `00b103b` equals reviewed head `ab066da`.

## Previous Loop — CLI-DATE-ARGUMENT-BOUNDARY (2026-10-24)

- RED: 12 invalid date cases fail before the change.
- Focused GREEN: 63 CLI/consumer tests pass.
- Full coverage suite: 688 passed; `mimir/*` coverage 97% (80% gate).
- Ruff, strict mypy (83 files), diff-check, and independent spec/quality review: PASS.
- Installed CLI: invalid date/since exit 2; extended/basic/week ISO inputs exit 0 against an empty local store.
- CI/main: PASS — PR #13, CI run `39984146712`, main `1f8e23c` equals reviewed head `442c8f1`.

## Previous Loop — CONFIG-YAML-SYNTAX-ERROR-BOUNDARY (2026-10-24)

| Gate | State | Evidence |
|---|---|---|
| RED / focused GREEN | PASS | 14 malformed command/file paths failed before the fix; CLI/config tests then passed 30 cases |
| Spec / quality review | PASS | Independent read-only review found no blocking issues; history symbol bypass regression strengthened |
| Final full suite | PASS | `.venv/bin/python -m coverage run -m pytest` with isolated `COVERAGE_FILE`: 676 passed in 37.30s; includes docs guards |
| Coverage | PASS | Total 99%; production `--include='mimir/*'`: 3205 statements, 86 missed, 97%, gate 80% |
| Lint / types | PASS | Ruff clean; `.venv/bin/python -m mypy mimir`: 83 files clean |
| User entry points | PASS | Installed `mimir`, `mimir.collect`, module invocation reject malformed input with exit 1; help exit 0; no output files |
| Diff / secrets / ownership | PASS | Diff-check and scoped credential-pattern scan pass; three pre-existing untracked artifacts preserved |
| CI / main merge | PASS | PR #12 CI run `39981998281` passed; squash merge `2c0bcb9` tree equals reviewed head `0d3b26e` |

Raw local verification logs are retained under `/tmp/mimir-20261024-yaml/`
and copied to the resume evidence directory at delivery. Tests used local
fixtures; no live collection, Telegram delivery, paid LLM, or workflow enabling.

## Previous Loop — FRED-TERMS-SAFETY-BOUNDARY

| Gate | State | Evidence |
|---|---|---|
| Official terms | PASS | FRED Services Terms API prohibitions `(k)`/`(l)` and the cumulative API terms were checked on 2026-08-31: <https://fred.stlouisfed.org/legal/terms/> and <https://fred.stlouisfed.org/docs/api/terms_of_use.html> |
| Contract decision | PASS | The JSONL collect/backfill/analysis path is incompatible with the current storage prohibition; attribution alone is insufficient |
| Local data preflight | PASS | `git ls-files data reports` and local `find data reports -type f` returned no files; no user data deletion is authorized or needed |
| Detailed design and plan | PASS | Placeholder/diff checks passed; independent contract review found no remaining Critical or Important issue |
| TDD RED | PASS | Exact focused RED command produced five expected failures (`5 failed in 4.44s`): builder `AssertionError: assert "fred" not in ...`; config `DID NOT RAISE ValidationError`; collect `assert responses.calls == []` (3 intercepted FRED calls); backfill expected `SystemExit` but reached `FetchError`; stored payload `DID NOT RAISE PayloadSchemaError`. `responses` intercepted the requests; no real network I/O. |
| Minimal implementation | PASS | Deleted the built-in adapter and its builder/settings/config/payload/default-metadata activation paths; existing strict config, unknown-source, ECOS, and `_narrow()` boundaries now fail closed |
| Focused GREEN | PASS | `uv run pytest tests/core/test_macro_series.py tests/core/test_payloads.py tests/storage/test_record_envelope.py tests/core/test_builder.py tests/sources/test_config.py tests/test_collect.py tests/test_backfill.py -q` — `196 passed in 2.05s` |
| Docs TDD RED | PASS | New current-surface guard failed before doc edits on `README.md missing removal notice`: `1 failed in 0.18s` |
| Current docs GREEN | PASS | `uv run pytest tests/test_readme_docs.py -q` — `36 passed in 1.50s`; collect-only reported `662 tests collected in 0.61s`, synced in all three README badges/tables |
| Docs history/safety | PASS | `uv run ruff check tests/test_readme_docs.py`, `git diff --check`, and the exact `git diff --exit-code HEAD -- docs/superpowers/plans docs/superpowers/specs docs/decisions/tech-spec` invariant passed; explicit executable-FRED and credential-pattern scans returned no matches |
| Docs fix round 1 | SUPERSEDED | Round 1 corrected ECOS legal-clearance claims, positional/current-surface coverage, and the manual-RSS evidence boundary. A subsequent re-review found that the trilingual guard still tested permission and series-rights words separately without locking the explicit re-enable condition or downstream notice/terms/privacy/citation obligations. |
| Docs fix round 2 | PASS | The guard independently locks each README's exact re-enable condition and all applicable notice/terms/privacy/citation obligations. Final tracked-tree rerun: focused guard `1 passed in 0.03s`; docs `36 passed in 1.14s`; full suite `662 passed in 9.56s`; count `662 tests collected in 0.37s`; test-file Ruff, diff-check, dated-history invariant, active-surface, and credential scans passed. |
| Full local gates | PASS | `uv run pytest -q` — `662 passed in 10.73s`; isolated coverage run — `662 passed in 11.42s`; `coverage report --fail-under=80` — `8447` statements, `134` missed, `98%`; `uv run ruff check .` and `uv run mypy mimir` passed (`83` source files); `git diff --check` passed |
| Count and dated history | PASS | Collect-only: `662 tests collected in 0.53s`; each README has the exact count in its badge and table (two `662` occurrences each), and coverage remains `98%`; `git diff --exit-code HEAD -- docs/superpowers/plans docs/superpowers/specs docs/decisions/tech-spec` returned no diff |
| Final safety scans | PASS | Explicit runtime/config/workflow/sample-env/current-doc/state scan found no executable activation; multiline positional `SourceSpec("fred", ...)` scan found none. Remaining FRED hits are removal/terms notices, negative guards, decisions/worklog, or dated history. Credential-value scan of `f87895a..HEAD` found no matches and printed no values |
| Final cleanup and ownership | PASS | No Mimir pytest/coverage process, Podman container, or Kind cluster remains; only the pre-existing ignored `.coverage` is outside the isolated plan-workspace `coverage-data`. `data/` and `reports/` have no tracked or local files and are unchanged; protected `CLAUDE.md`, `docs/superpowers/handoffs/`, and `uv.lock` remain untracked and unstaged |
| Independent whole-diff reviews | PASS | Final merge-review scoped re-review: APPROVE. The meta-less-plugin backfill Important and ECOS/KR fixture Minor are addressed; no Critical or Important finding remains |
| Final consolidation | PASS | Separate plan checkpoint `f87895a`; one final implementation commit, `fix(sources): remove incompatible FRED integration`, covers reviewed range `f87895a..this implementation commit` after the approved correction wave |
| Exact local verification commit | PASS | This final implementation commit carries the approved correction wave and its `662`-test, `98%` isolated-coverage, Ruff/mypy, docs/history, and diff-check evidence; no push or remote mutation |
| PR | PASS | [PR #10](https://github.com/YouSangSon/Mimir/pull/10) carried the 111-commit local improvement range from pinned base `9668d07` to reviewed head `981f963`; GitHub reported `MERGEABLE` / `CLEAN` before merge |
| CI | PASS | GitHub Actions `ci / test` completed successfully on PR head `981f963` in 33 seconds: [run 33358537038 / job 99385242683](https://github.com/YouSangSon/Mimir/actions/runs/33358537038/job/99385242683) |
| Main merge | PASS | PR #10 squash-merged at 2026-08-31 13:52 KST as `06997d8`; fetched `origin/main` tree `26498c6e` exactly matched the reviewed PR-head tree |
