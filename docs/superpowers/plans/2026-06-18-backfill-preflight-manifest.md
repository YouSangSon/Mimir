# Backfill Preflight Failure Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record `ok=false` backfill manifest entries when a registered source is unavailable before fetch because a secret or optional package gate skipped it.

**Architecture:** Expose optional static `SourceMeta` on `SourceSpec`, load source specs once in `run_backfill()`, and write a zero-count failure manifest when the requested source id is registered but missing from built sources. Unknown source ids remain argument errors without manifest because the current `RunRecord` schema requires a real cadence.

**Tech Stack:** Python 3.14, dataclasses, pydantic manifest models, pytest, responses, ruff, mypy.

## Global Constraints

- Do not extend the manifest schema in this increment.
- Do not invent a cadence for unknown source ids.
- Do not expose secret values in manifest, logs, docs, or tests.
- Preserve `SystemExit("unknown or unavailable source: <id>")` for unavailable and unknown source ids.
- Manifest `error` for registered unavailable sources should contain the secret/package gate reason without exposing any secret value.
- Keep `SourceSpec(id, factory)` plugin construction backward-compatible.
- Keep untracked `uv.lock` unstaged.

---

## File Map

| File | Responsibility |
| ---- | -------------- |
| `mimir/core/builder.py` | Add optional static source metadata and reusable source-spec loading |
| `mimir/backfill.py` | Write preflight failure manifest for registered unavailable sources |
| `tests/core/test_builder.py` | Lock built-in `SourceSpec.meta` and backward compatibility |
| `tests/test_backfill.py` | RED/GREEN coverage for unavailable registered source and unknown source boundary |
| `README.md`, `README.ko.md`, `README.zh.md` | Clarify backfill manifest boundary and test count |
| `docs/IMPROVEMENTS.md` | Mark BF-PREFLIGHT as completed after implementation |
| `docs/architecture/improvement-catalog.md` | Add BF-PREFLIGHT to robustness catalog and sequence map |
| `docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md` | Mark acceptance criteria complete after verification |

---

### Task 1: Write Failing Preflight Tests

**Files:**
- Modify: `tests/test_backfill.py`
- Modify: `tests/core/test_builder.py`

**Interfaces:**
- Consumes: current `run_backfill()` behavior and `BUILTIN_SOURCE_SPECS`
- Produces: failing tests that define the BF-PREFLIGHT contract

- [x] **Step 1: Add registered-unavailable source test**

Add this test to `tests/test_backfill.py` after `test_backfill_records_failure_manifest_before_reraising`:

```python
def test_backfill_records_unavailable_registered_source_manifest_before_system_exit(
    tmp_path: Path,
):
    data_root = tmp_path / "data"

    with pytest.raises(SystemExit, match="unknown or unavailable source: stooq"):
        run_backfill(
            source_id="stooq",
            since=date(2018, 1, 1),
            env={},
            watchlist={"us": ["AAPL"], "kr": []},
            data_root=data_root,
            now=datetime(2026, 5, 31, tzinfo=UTC),
        )

    latest = Manifest(root=data_root).latest_run()
    assert latest is not None
    assert latest.cadence == "daily"
    result = latest.results[0]
    assert result.source == "stooq"
    assert result.ok is False
    assert result.fetched == 0
    assert result.stored == 0
    assert result.invalid == 0
    assert result.error == "STOOQ_API_KEY is not set"
```

- [x] **Step 2: Add missing optional package test**

Add this test to `tests/test_backfill.py` immediately after the registered-unavailable test:

```python
def test_backfill_records_missing_optional_package_manifest_before_system_exit(
    tmp_path: Path, monkeypatch
):
    data_root = tmp_path / "data"
    monkeypatch.setattr(
        "mimir.core.builder.importlib.util.find_spec",
        lambda name: None if name == "pykrx" else object(),
    )

    with pytest.raises(SystemExit, match="unknown or unavailable source: pykrx"):
        run_backfill(
            source_id="pykrx",
            since=date(2018, 1, 1),
            env={},
            watchlist={"us": [], "kr": ["005930"]},
            data_root=data_root,
            now=datetime(2026, 5, 31, tzinfo=UTC),
        )

    latest = Manifest(root=data_root).latest_run()
    assert latest is not None
    assert latest.cadence == "daily"
    result = latest.results[0]
    assert result.source == "pykrx"
    assert result.ok is False
    assert result.fetched == 0
    assert result.stored == 0
    assert result.invalid == 0
    assert result.error == "package not installed (pip install -e '.[kr]')"
```

- [x] **Step 3: Add unknown source boundary test**

Add this test to `tests/test_backfill.py` immediately after the registered-unavailable test:

```python
def test_backfill_unknown_source_remains_argument_error_without_manifest(tmp_path: Path):
    data_root = tmp_path / "data"

    with pytest.raises(SystemExit, match="unknown or unavailable source: not_a_source"):
        run_backfill(
            source_id="not_a_source",
            since=date(2018, 1, 1),
            env={},
            watchlist={"us": ["AAPL"], "kr": []},
            data_root=data_root,
            now=datetime(2026, 5, 31, tzinfo=UTC),
        )

    assert Manifest(root=data_root).latest_run() is None
```

- [x] **Step 4: Add builder metadata test**

Add this test to `tests/core/test_builder.py` after `test_builtin_source_specs_keep_existing_order`:

```python
def test_builtin_source_specs_expose_static_metadata_for_preflight_manifest():
    metas = {spec.id: spec.meta for spec in BUILTIN_SOURCE_SPECS}

    assert all(meta is not None for meta in metas.values())
    assert metas["stooq"] is not None
    assert metas["stooq"].id == "stooq"
    assert metas["stooq"].cadence == Cadence.DAILY
    assert metas["stooq"].requires_secret == "STOOQ_API_KEY"
```

- [x] **Step 5: Verify RED**

Run:

```bash
uv run pytest \
  tests/test_backfill.py::test_backfill_records_unavailable_registered_source_manifest_before_system_exit \
  tests/test_backfill.py::test_backfill_records_missing_optional_package_manifest_before_system_exit \
  tests/test_backfill.py::test_backfill_unknown_source_remains_argument_error_without_manifest \
  tests/core/test_builder.py::test_builtin_source_specs_expose_static_metadata_for_preflight_manifest \
  -q
```

Expected before implementation:

- registered-unavailable and optional-package tests fail because no manifest exists.
- builder metadata test fails because `SourceSpec` has no `meta` field.
- unknown source boundary test may already pass.

---

### Task 2: Expose Source Metadata and Write Preflight Manifest

**Files:**
- Modify: `mimir/core/builder.py`
- Modify: `mimir/backfill.py`

**Interfaces:**
- Produces: `SourceSpec.meta: SourceMeta | None`
- Produces: `load_source_specs(group: str = SOURCE_ENTRY_POINT_GROUP) -> tuple[SourceSpec, ...]`
- Produces: `build_sources(settings, config=None, *, specs=None)`

- [x] **Step 1: Add metadata to `SourceSpec`**

In `mimir/core/builder.py`, import `SourceMeta` and add the field at the end of the dataclass:

```python
from mimir.core.source import Source, SourceMeta

@dataclass(frozen=True)
class SourceSpec:
    id: str
    factory: Callable[[Settings, SourcesConfig], Source]
    required_secret_attr: str | None = None
    required_secret_name: str | None = None
    required_module: str | None = None
    missing_module_hint: str | None = None
    meta: SourceMeta | None = None
```

- [x] **Step 2: Attach built-in source metadata**

Update every built-in `SourceSpec(...)` with `meta=<SourceClass>.meta`. Example:

```python
SourceSpec(
    "stooq",
    lambda settings, cfg: StooqSource(
        api_key=_required_secret(settings.stooq_api_key, "STOOQ_API_KEY")
    ),
    required_secret_attr="stooq_api_key",
    required_secret_name="STOOQ_API_KEY",
    meta=StooqSource.meta,
)
```

Apply the same pattern for `sec_edgar`, `rss`, `dart`, `fred`, `ecos`, and `pykrx`.

- [x] **Step 3: Add source-spec loading helper and optional build override**

Add this helper below `_load_entry_point_source_specs()`:

```python
def load_source_specs(
    group: str = SOURCE_ENTRY_POINT_GROUP,
) -> tuple[SourceSpec, ...]:
    return (*BUILTIN_SOURCE_SPECS, *_load_entry_point_source_specs(group))
```

Then update `build_sources()`:

```python
def build_sources(
    settings: Settings,
    config: SourcesConfig | None = None,
    *,
    specs: Sequence[SourceSpec] | None = None,
) -> list[Source]:
    if "@" not in settings.sec_user_agent:
        logger.warning(
            "MIMIR_SEC_USER_AGENT has no contact email; SEC EDGAR may return 403. "
            "Set it to e.g. 'Your Name you@example.com'."
        )
    cfg = config or SourcesConfig()
    selected_specs = tuple(specs) if specs is not None else load_source_specs()
    return _build_sources_from_specs(settings, cfg, selected_specs)
```

- [x] **Step 4: Write preflight failure helper in backfill**

In `mimir/backfill.py`, import `Sequence`, `Cadence`, and `SourceSpec/load_source_specs`:

```python
from collections.abc import Mapping, Sequence

from mimir.core.builder import SourceSpec, build_sources, load_source_specs
from mimir.core.source import Cadence, FetchContext
```

Add helpers above `run_backfill()`:

```python
def _source_spec_for_id(specs: Sequence[SourceSpec], source_id: str) -> SourceSpec | None:
    for spec in specs:
        if spec.id == source_id:
            return spec
    return None


def _preflight_unavailable_error(spec: SourceSpec, settings: Settings, source_id: str) -> str:
    if spec.required_secret_attr and not getattr(settings, spec.required_secret_attr):
        return f"{spec.required_secret_name or spec.required_secret_attr} is not set"
    if spec.required_module:
        return spec.missing_module_hint or f"required module {spec.required_module} is not installed"
    return f"unknown or unavailable source: {source_id}"


def _write_failure_manifest(
    manifest: Manifest,
    *,
    now: datetime,
    cadence: Cadence,
    source_id: str,
    fetched: int,
    invalid: int,
    error: str,
) -> None:
    manifest.write(
        now=now,
        cadence=cadence,
        results=[
            SourceResult(
                source=source_id,
                ok=False,
                fetched=fetched,
                invalid=invalid,
                error=error,
            )
        ],
    )
```

- [x] **Step 5: Use helper in `run_backfill()`**

Update the start of `run_backfill()`:

```python
settings = Settings.from_env(env)
config = parse_sources_config(sources_config or {})
manifest = Manifest(root=data_root)
specs = load_source_specs()
sources = {s.meta.id: s for s in build_sources(settings, config, specs=specs)}
if source_id not in sources:
    if (spec := _source_spec_for_id(specs, source_id)) and spec.meta is not None:
        manifest_error = _preflight_unavailable_error(spec, settings, source_id)
        try:
            _write_failure_manifest(
                manifest,
                now=now,
                cadence=spec.meta.cadence,
                source_id=spec.meta.id,
                fetched=0,
                invalid=0,
                error=manifest_error,
            )
        except Exception:
            logger.warning(
                "backfill %s: failed to write preflight failure manifest",
                source_id,
                exc_info=True,
            )
    raise SystemExit(f"unknown or unavailable source: {source_id}")
source = sources[source_id]
store = JsonlStore(root=data_root)
```

Then update runtime failure handling to call `_write_failure_manifest(...)` instead of duplicating `manifest.write(...)`.

- [x] **Step 6: Verify GREEN for focused tests**

Run:

```bash
uv run pytest \
  tests/test_backfill.py::test_backfill_records_unavailable_registered_source_manifest_before_system_exit \
  tests/test_backfill.py::test_backfill_records_missing_optional_package_manifest_before_system_exit \
  tests/test_backfill.py::test_backfill_unknown_source_remains_argument_error_without_manifest \
  tests/core/test_builder.py::test_builtin_source_specs_expose_static_metadata_for_preflight_manifest \
  tests/test_backfill.py::test_backfill_records_failure_manifest_before_reraising \
  tests/test_backfill.py::test_backfill_preserves_original_error_when_failure_manifest_write_fails \
  -q
```

Expected: all selected tests pass.

---

### Task 3: Update Docs and Verify

**Files:**
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md`
- Modify: `docs/superpowers/plans/2026-06-18-backfill-preflight-manifest.md`

**Interfaces:**
- Consumes: final test count and coverage from verification
- Produces: user-facing documentation of unavailable-vs-unknown boundary

- [x] **Step 1: Update README backfill contract**

In all three READMEs, change the backfill paragraph to explain:

- success records `fetched`, `stored`, `invalid`.
- registered source failures record `ok=false` before surfacing the error.
- registered-but-unavailable preflight failures, such as missing API key or optional package, also record `ok=false` with zero counts.
- truly unknown source ids remain argument errors without manifest because cadence is unavailable.

- [x] **Step 2: Update test count after full verification**

Full pytest now reports 499 tests, so the README badges and test table use `499`.

- [x] **Step 3: Update improvement docs**

In `docs/IMPROVEMENTS.md`, add a completed LOW/MEDIUM item:

```markdown
- [x] **backfill preflight failure manifest**: registered source가 secret/package gate 때문에 fetch 전에 제외되면 manifest 없이 `SystemExit`만 남았다. → built-in `SourceSpec`에 static `SourceMeta`를 연결하고, backfill이 registered-but-unavailable source를 `ok=false` manifest로 기록한다. Unknown source id는 cadence를 알 수 없어 argument error로 유지한다.
```

In `docs/architecture/improvement-catalog.md`, add `BF-PREFLIGHT` near `BF-MANIFEST`, and add it to the sequence map and conclusion.

- [x] **Step 4: Mark spec and plan checkboxes**

After verification, mark the spec acceptance criteria and plan tasks complete.

- [x] **Step 5: Run focused and full gates**

Run:

```bash
uv run pytest tests/test_backfill.py tests/core/test_builder.py tests/manifest/test_manifest.py -q
uv run ruff check .
uv run mypy mimir
uv run pytest -q
uv run coverage run -m pytest
uv run coverage report --fail-under=80
git diff --check
```

- [x] **Step 6: Commit locally**

Commit only tracked intended files. Keep `uv.lock` unstaged.

```bash
git add \
  mimir/core/builder.py \
  mimir/backfill.py \
  tests/core/test_builder.py \
  tests/test_backfill.py \
  README.md README.ko.md README.zh.md \
  docs/IMPROVEMENTS.md \
  docs/architecture/improvement-catalog.md \
  docs/superpowers/specs/2026-06-18-backfill-preflight-manifest-design.md \
  docs/superpowers/plans/2026-06-18-backfill-preflight-manifest.md
git commit -m "fix(backfill): record preflight source failures"
```
