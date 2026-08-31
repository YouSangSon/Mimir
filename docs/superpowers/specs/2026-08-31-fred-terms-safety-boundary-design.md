# FRED Terms Safety Boundary Design

> **Status:** Reviewed — accepted for local implementation
> **Date:** 2026-08-31
> **Owner:** `FRED-TERMS-SAFETY-BOUNDARY`

## 1. Problem

Mimir's built-in `FredSource` calls the FRED API, normalizes observations, and
stores them in the versioned JSONL pipeline. `mimir.backfill` independently
persists the same content, and macro analysis can consume both newly collected
and previously stored FRED-shaped payloads.

The current FRED Services Terms include the API and prohibit API use connected
to software/ML development and to storing, caching, archiving, or incorporating
FRED content in a database or other medium. The separate API terms also include
the St. Louis Fed website legal terms. Adding attribution therefore does not
make Mimir's persistent FRED path acceptable.

Official evidence checked on 2026-08-31:

- <https://fred.stlouisfed.org/legal/terms/>
- <https://fred.stlouisfed.org/docs/api/terms_of_use.html>

The two documents do not state which has priority or grant Mimir an exception.
The safe boundary is cumulative application and fail-closed removal.

## 2. Decision

Remove FRED as a built-in Mimir source. Collection, backfill, configuration,
credential wiring, typed payload acceptance, default macro analysis, and current
operator documentation must no longer provide an executable FRED path.

This is removal, not a hidden toggle:

- `FRED_API_KEY` alone does nothing.
- `sources.fred` is rejected by the existing `extra="forbid"` config boundary.
- Normal collection may still write its empty manifest/status output, but it
  performs no FRED request and writes no FRED macro data.
- `mimir backfill --source fred` fails as unknown/unavailable before network,
  manifest, or data writes.
- Legacy FRED-shaped macro payloads fail typed payload validation instead of
  flowing into analysis.
- The existing generic macro pipeline and ECOS source remain.

## 3. Scope

### Remove executable support

- Delete `mimir/sources/fred.py` and its adapter tests.
- Remove the FRED import and `SourceSpec` from `mimir/core/builder.py`.
- Remove `fred_api_key` and `FRED_API_KEY` loading from `mimir/settings.py`.
- Remove `sources.fred` and `fred_series` from `mimir/sources/config.py`.
- Remove FRED defaults from `mimir/core/macro_series.py`.
- Remove `FredMacroPayload` from `mimir/core/payloads.py`; macro payloads become
  ECOS-only until another rights-compatible source is designed.
- Remove workflow, `.env.example`, and `config/sources.yaml` activation wiring.

### Correct current documentation

Current README EN/KO/ZH, operator references, roadmap, extensibility guide,
storage reference, improvement catalog, and root state must say FRED is
unsupported because current terms conflict with persistent collection. They
must also stop claiming that `legal_status` is enforced by the throttler:
throttling enforces only `rate_limit`, while `Registry` filters GRAY sources.

Dated plans, prior decisions, and historical specs remain unchanged evidence of
what was implemented at that time. Active docs guards may continue checking
their internal historical completeness, but no current runtime or operator
surface may treat their old FRED capability as an available feature.

### Preserve data and external state

The current checkout has no tracked or local `data/` or `reports/` files. This
loop does not search external clones, delete user data, remove a GitHub secret,
or mutate a remote repository. Operators with prior FRED-derived JSONL must stop
using it, identify it, and then either delete it under an explicitly approved
destructive plan or retain it only after obtaining applicable rights. Temporary
quarantine is an interim safety step, not final remediation.

## 4. Re-enable Conditions

FRED support remains absent unless all of these are available:

1. Written permission from the Federal Reserve Bank of St. Louis covering the
   intended API, storage, software, analysis, redistribution, and publication
   paths under the then-current terms.
2. Rights and citation review for every configured series and its owner.
3. The exact required non-endorsement notice, API terms link/user contract, and
   privacy obligations required for the actual deployment surface.
4. A new design and tests that encode those permissions and provenance.

## 5. Non-goals

- Do not replace FRED with a new US macro provider in this loop.
- Do not weaken typed payload validation to keep legacy FRED JSONL readable.
- Do not implement ECOS provenance or custom-series rights in this loop; queue
  it as the next source-legality slice.
- Do not add a new feature flag, deprecation layer, or compatibility adapter.

## 6. Acceptance Contract

1. Built-in source specs, settings, config, workflow, and sample env contain no
   executable FRED activation path.
2. A legacy key cannot build or call a FRED source.
3. A legacy `sources.fred` block raises `ValidationError`.
4. Normal collect performs no FRED request/data write, and FRED backfill fails
   before network and storage mutation.
5. A stored FRED-shaped macro record raises `PayloadSchemaError`; ECOS macro payloads
   still validate and reach the existing macro/doctor paths.
6. Current docs in all three README languages describe the removal and link the
   official terms; dated history remains untouched.
7. Focused tests, all repository tests, coverage `>=80%`, Ruff, mypy, docs
   guards, diff-check, secrets scan, and two independent reviews pass.
