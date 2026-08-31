# FRED Terms Safety Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove every built-in path that can fetch, persist, or analyze FRED API content under the current incompatible terms.

**Architecture:** Fail closed at the source-registration, config, backfill, and typed-payload boundaries. Delete the one built-in adapter and reuse existing Pydantic `extra="forbid"`, unknown-source handling, generic ECOS macro support, and repository verification gates; add no dependency, feature flag, or compatibility layer.

**Tech Stack:** Python 3.14, Pydantic v2, pytest, responses, Ruff, mypy strict, Markdown docs guards.

**Spec:** `docs/superpowers/specs/2026-08-31-fred-terms-safety-boundary-design.md`

## Global Constraints

- Current official terms are authoritative; attribution cannot override a use prohibition.
- No FRED network request or macro data write may occur for a legacy key. Invalid
  config and FRED backfill must fail before any write; normal collect may still
  write its manifest and status output.
- Preserve the ECOS macro path and generic macro analysis interfaces.
- Do not delete user data or mutate remote GitHub settings, secrets, workflow
  runs, or repositories. Local workflow YAML is part of this implementation.
- Preserve user-owned `CLAUDE.md`, `docs/superpowers/handoffs/`, and `uv.lock`.
- Add no dependency or speculative replacement provider.

---

## File Map

### Production and configuration

- Delete: `mimir/sources/fred.py` — incompatible built-in adapter.
- Modify: `mimir/core/builder.py` — remove FRED import/spec/configurable id.
- Modify: `mimir/settings.py` — remove `fred_api_key` environment wiring.
- Modify: `mimir/sources/config.py` — reject legacy `sources.fred` through the existing strict schema.
- Modify: `mimir/core/macro_series.py` — retain only rights-compatible built-in macro metadata.
- Modify: `mimir/core/payloads.py` — reject legacy FRED-shaped macro payloads.
- Modify: `mimir/analysis/signals/macro_regime.py`, `mimir/doctor/checks.py`, `mimir/doctor/expectations.py` — remove current-support comments while preserving generic behavior.
- Modify: `.github/workflows/_pipeline.yml`, `.env.example`, `config/sources.yaml` — remove activation wiring.
- Modify: `scripts/mock_dashboard.py` — replace the retired mock source label.

### Tests

- Delete: `tests/sources/test_fred.py`.
- Modify: `tests/core/test_builder.py` — negative legacy-key registration guard and existing source expectations.
- Modify: `tests/sources/test_config.py` — legacy FRED block rejection guard and ECOS/RSS config expectations.
- Modify: `tests/test_collect.py` — legacy-key no-FRED-network/data guard.
- Modify: `tests/test_backfill.py` — network-free FRED rejection guard; remove retired adapter integration cases.
- Modify: `tests/core/test_payloads.py`, `tests/storage/test_record_envelope.py` — reject stored legacy macro records and retain ECOS serialization.
- Modify: `tests/core/test_macro_series.py`, affected macro/doctor/report fixtures — keep ECOS/generic behavior without current FRED labels.
- Modify: `tests/test_readme_docs.py` — current-surface removal/docs guard and historical-spec supersession.

### Current documentation and state

- Modify: `README.md`, `README.ko.md`, `README.zh.md`.
- Modify: `docs/reference/config/sources.md`, `docs/reference/storage/data-layout.md`.
- Modify: `docs/architecture/extensibility/README.md`, `docs/architecture/roadmap.md`, `docs/architecture/improvement-catalog.md`, `docs/IMPROVEMENTS.md`.
- Modify: `BACKLOG.md`, `DECISIONS.md`, `WORKLOG.md`, `GATES.md`.

## Task 1: Create the Plan Checkpoint

**Files:**
- Create: `GOAL.md`
- Create: `GATES.md`
- Create: `docs/superpowers/specs/2026-08-31-fred-terms-safety-boundary-design.md`
- Create: `docs/superpowers/plans/2026-08-31-fred-terms-safety-boundary.md`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: root active-goal wording, official FRED terms, live production/data preflight.
- Produces: one stable goal, one current gate ledger, one accepted design, and this executable plan.

- [ ] **Step 1: Link the current loop from `PLAN.md`**

Set `## Current Loop` to `FRED-TERMS-SAFETY-BOUNDARY` and link this plan, its
design, `GATES.md`, backlog, worklog, and decisions.

- [ ] **Step 2: Self-review the plan**

Check every acceptance item in the spec has an owning task, run:

```bash
rg -n "T[B]D|T[O]DO|implement la[t]er|<ne[w]|<pat[h]|appropriate erro[r]|similar t[o]" \
  docs/superpowers/plans/2026-08-31-fred-terms-safety-boundary.md
git diff --check
```

Expected: no placeholder match and no whitespace error.

- [ ] **Step 3: Commit only the plan checkpoint**

```bash
git add GOAL.md GATES.md PLAN.md \
  docs/superpowers/specs/2026-08-31-fred-terms-safety-boundary-design.md \
  docs/superpowers/plans/2026-08-31-fred-terms-safety-boundary.md
git commit -m "docs(sources): plan FRED terms safety boundary"
```

Expected: one local commit; user-owned untracked files remain unmodified.

## Task 2: Prove the Safety Boundary RED

**Files:**
- Modify: `tests/core/test_builder.py`
- Modify: `tests/sources/test_config.py`
- Modify: `tests/test_collect.py`
- Modify: `tests/test_backfill.py`
- Modify: `tests/storage/test_record_envelope.py`

**Interfaces:**
- Consumes: `build_sources(Settings)`, `parse_sources_config(raw)`, `run_backfill(...)`, `parse_payload(dataset, data)`.
- Produces: five negative regression guards that fail on the current implementation.

- [ ] **Step 1: Add the builder/config guards**

Add tests equivalent to:

```python
def test_legacy_fred_key_does_not_register_or_build_a_source():
    assert "fred" not in {spec.id for spec in BUILTIN_SOURCE_SPECS}
    sources = build_sources(Settings.from_env({"FRED_API_KEY": "legacy"}))
    assert "fred" not in {source.meta.id for source in sources}


def test_legacy_fred_config_is_rejected():
    with pytest.raises(ValidationError, match="fred"):
        parse_sources_config({"sources": {"fred": {"series": ["DGS10"]}}})
```

- [ ] **Step 2: Add the collect no-FRED-network/data guard**

Use `@responses.activate`, disable the unrelated keyless and GRAY sources, and
allow the expected manifest/status outputs:

```python
@responses.activate
def test_legacy_fred_key_collects_no_fred_data(tmp_path: Path):
    summary = run_collect(
        cadence="daily",
        env={"FRED_API_KEY": "legacy"},
        watchlist={"us": [], "kr": []},
        data_root=tmp_path / "data",
        status_path=tmp_path / "reports/status.html",
        sources_config={
            "gray_enabled": False,
            "disabled_ids": ["sec_edgar", "rss"],
        },
        now=datetime(2026, 8, 31, tzinfo=UTC),
    )
    assert responses.calls == []
    assert all(result.source != "fred" for result in summary.results)
    assert not (tmp_path / "data/macro").exists()
```

- [ ] **Step 3: Add the backfill no-network/no-write guard**

Use `@responses.activate` without registering a FRED response:

```python
@responses.activate
def test_backfill_fred_fails_before_network_or_storage(tmp_path: Path):
    data_root = tmp_path / "data"
    with pytest.raises(SystemExit, match="unknown or unavailable source: fred"):
        run_backfill(
            source_id="fred",
            since=date(2024, 1, 1),
            env={"FRED_API_KEY": "legacy"},
            watchlist={"us": [], "kr": []},
            data_root=data_root,
        )
    assert responses.calls == []
    assert not data_root.exists()
```

- [ ] **Step 4: Add the stored legacy payload rejection guard**

```python
def test_stored_fred_macro_record_is_rejected_before_analysis():
    line = json.dumps(
        {
            "schema_version": 1,
            "source": "fred",
            "dataset": "macro",
            "market": "US",
            "symbol": "DGS10",
            "ts": "2026-01-15T00:00:00Z",
            "captured_at": "2026-01-16T00:00:00Z",
            "idempotency_key": "fred:DGS10:2026-01-15",
            "payload": {
                "series_id": "DGS10",
                "value": 4.5,
                "period": "2026-01-15",
            },
        }
    )
    with pytest.raises(PayloadSchemaError):
        Record.model_validate_json(line)
```

- [ ] **Step 5: Run RED**

```bash
uv run pytest \
  tests/core/test_builder.py::test_legacy_fred_key_does_not_register_or_build_a_source \
  tests/sources/test_config.py::test_legacy_fred_config_is_rejected \
  tests/test_collect.py::test_legacy_fred_key_collects_no_fred_data \
  tests/test_backfill.py::test_backfill_fred_fails_before_network_or_storage \
  tests/storage/test_record_envelope.py::test_stored_fred_macro_record_is_rejected_before_analysis -q
```

Expected: failures prove the current built-in, config, collect, backfill, and
stored-record paths are open. `responses` prevents any real network request.

- [ ] **Step 6: Update `GATES.md`**

Mark `TDD RED` PASS with the exact five failing assertions; leave implementation and GREEN pending.

## Task 3: Remove the Executable FRED Path

**Files:**
- Delete and modify the production/configuration files listed in the File Map.
- Modify the affected unit tests listed in the File Map.

**Interfaces:**
- Consumes: existing Pydantic strict schema, unknown-source `SystemExit`, ECOS macro payload/model, `SourceSpec` table.
- Produces: no built-in FRED source; `MacroPayload = EcosMacroPayload`; ECOS-only default macro metadata.

- [ ] **Step 1: Delete the adapter and registration/credential wiring**

Delete `mimir/sources/fred.py` and remove its import and `SourceSpec`. Remove
`fred_api_key` from `Settings` and the workflow/sample-env key. Remove `fred`
from `CONFIGURABLE_BUILTIN_SOURCE_IDS`.

- [ ] **Step 2: Remove the strict config field**

Delete `fred_series`, `_FredBlock`, `_SourcesBlock.fred`, and the mapping in
`_source_config_from_top_level()`. Do not add a deprecated field: the existing
`extra="forbid"` error is the fail-closed contract.

- [ ] **Step 3: Remove FRED macro defaults and payload acceptance**

Delete `_FRED_SERIES` and `default_fred_series()`. Derive
`DEFAULT_MACRO_RATE_SERIES` and `macro_series_cadences()` from ECOS metadata
only. Delete `FredMacroPayload`, set `MacroPayload = EcosMacroPayload`, map
`Dataset.MACRO` directly to `EcosMacroPayload`, and reuse `_narrow()` in
`macro_payload()`.

- [ ] **Step 4: Repair tests without weakening the boundary**

Delete retired positive FRED adapter/backfill tests. Update builder/config/macro
expectations to ECOS/RSS behavior. Replace current-support FRED fixture labels
in generic orchestrator/doctor/report tests with ECOS or provider-neutral values.
Keep storage overwrite tests; they already prove generic macro last-write-wins.

- [ ] **Step 5: Run focused GREEN**

Run the exact five tests from Task 2 plus:

```bash
uv run pytest tests/core/test_macro_series.py tests/core/test_payloads.py \
  tests/storage/test_record_envelope.py tests/core/test_builder.py \
  tests/sources/test_config.py tests/test_collect.py tests/test_backfill.py -q
```

Expected: all pass with no FRED request registered or issued.

- [ ] **Step 6: Prove the ECOS macro path remains intact**

```bash
uv run pytest tests/sources/test_ecos.py tests/core/test_payloads.py \
  tests/storage/test_record_envelope.py \
  tests/core/test_orchestrator.py::test_macro_sources_overwrite_existing_observations \
  tests/analysis/signals/test_signals.py::test_macro_regime_uses_configured_rate_series \
  tests/doctor/test_engine_matrix.py::test_monthly_ecos_series_not_false_alarmed -q
```

Expected: ECOS fetch/normalization, typed serialization, generic macro revision,
configured macro signal, and monthly doctor cadence all pass. Replace the old
FRED monthly fixture and rename the doctor test to the exact name above.

- [ ] **Step 7: Update `GATES.md`**

Mark `Minimal implementation` and `Focused GREEN` PASS with command evidence.

## Task 4: Correct Current Documentation and Preserve History

**Files:**
- Modify the current docs and state files listed in the File Map.
- Modify: `tests/test_readme_docs.py`

**Interfaces:**
- Consumes: the removed runtime contract and official terms URLs.
- Produces: trilingual operator truth, a durable docs guard, and bounded ECOS/manual-RSS follow-ups.

- [ ] **Step 1: Add a failing current-doc guard**

Add one test that asserts:

- `mimir/sources/fred.py` does not exist.
- builder/settings/config/workflow/sample env contain no executable FRED key,
  import, spec, or config field.
- README EN/KO/ZH each link both official FRED terms and say built-in support is
  removed/unsupported.
- active config/storage/extensibility docs do not instruct operators to enable
  `sources.fred` or `FRED_API_KEY`.
- dated plans/specs remain unchanged and are excluded from active support claims.

Run the new test before doc edits; expected result is FAIL on current claims.

- [ ] **Step 2: Update trilingual README and current operator docs**

Remove FRED from source counts, tables, key instructions, backfill examples,
diagrams, and official-source claims. Add a concise removal note with both
official terms URLs and the written-permission re-enable condition. Correct the
throttler/`legal_status` wording and state that manual RSS URLs remain the
operator's verification responsibility.

- [ ] **Step 3: Update architecture/state history**

Mark current catalog/roadmap summaries as superseded by the 2026-08-31 terms
boundary without rewriting dated plans/specs. Record the decision and worklog,
move `FRED-TERMS-SAFETY-BOUNDARY` to Done, and split the old source-legality
umbrella so `ECOS-PROVENANCE-RIGHTS-BOUNDARY` and
`MANUAL-RSS-LEGAL-OWNERSHIP` are finite next candidates.

- [ ] **Step 4: Refresh the dynamic test count**

Run:

```bash
uv run pytest --collect-only -q | tail -1
```

Replace all test badge/table counts in README EN/KO/ZH with the exact collected
integer. Do not change the coverage percentage until the coverage command has
run on the final tree.

- [ ] **Step 5: Run docs GREEN**

```bash
uv run pytest tests/test_readme_docs.py -q
```

Expected: all docs guards pass and no current surface advertises executable FRED support.

- [ ] **Step 6: Prove dated history is unchanged**

The plan checkpoint is the implementation baseline, so this command permits the
new 2026-08-31 plan/spec already in `HEAD` while rejecting later rewrites:

```bash
git diff --exit-code HEAD -- docs/superpowers/plans docs/superpowers/specs \
  docs/decisions/tech-spec
```

Expected: no diff.

## Task 5: Verify, Review, and Commit

**Files:**
- All loop-owned files from Tasks 2-4.

**Interfaces:**
- Consumes: the complete implementation diff.
- Produces: reviewed local checkpoint and updated gate ledger.

- [ ] **Step 1: Run final repository gates**

```bash
uv run pytest -q
uv run coverage run -m pytest
uv run coverage report --fail-under=80
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: full tests pass, coverage is at least 80%, and static/diff checks pass.
Update the README coverage display only if the final reported integer changed.

- [ ] **Step 2: Run active-surface and secrets scans**

Use an explicit current-surface path list. FRED may remain only in the removal
notice, official terms URLs, negative tests, decisions/worklog, and dated
history. Scan changed files for credential patterns; environment variable names
are placeholders, never secrets.

- [ ] **Step 3: Run independent reviews**

Give the exact dirty diff to a spec reviewer and a quality reviewer. Fix every
Critical and Important finding, rerun affected gates, and record both verdicts
in `WORKLOG.md` and `GATES.md`.

- [ ] **Step 4: Verify cleanup and exact staging**

Confirm no test process, coverage temp file, Podman container, or Kind resource
created by this loop remains. Stage only loop-owned files; inspect cached names,
stat, full diff, diff-check, and status. Preserve all user-owned untracked files.
Re-run the dated-history `git diff --exit-code HEAD` check after staging.

- [ ] **Step 5: Commit locally**

```bash
git commit -m "fix(sources): remove incompatible FRED integration"
```

Expected: one local implementation commit, no push, current `PLAN.md` and
`GATES.md` agree with the committed state.

## Self-Review

- Spec coverage: Tasks 2-4 own all seven acceptance items; Task 5 owns full verification and review.
- Placeholder scan: the plan contains no unresolved implementation placeholder; dynamic test/coverage values are explicitly measured before documentation changes.
- Type consistency: `MacroPayload` remains a valid alias to `EcosMacroPayload`; builder/config/backfill names match current code.
- Ponytail check: deletion plus existing strict/unknown-source boundaries is smaller than a new policy flag or compatibility layer.
