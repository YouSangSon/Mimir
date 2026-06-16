# Declarative Source Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the source-builder if-ladder with an internal declarative `SourceSpec` table while preserving every existing source availability and storage contract.

**Architecture:** `build_sources(settings, config)` remains the public composition root. Built-in source construction moves into immutable `SourceSpec` entries that encode secret gates, optional dependency gates, and constructor kwargs. Runtime filtering stays in `mimir/core/registry.py`.

**Tech Stack:** Python 3.14, pydantic, pytest, ruff, mypy, existing Mimir source adapter protocol.

---

## File Structure

- Modify: `mimir/core/builder.py`
  - Add `SourceSpec`, `BUILTIN_SOURCE_SPECS`, duplicate id validation, and spec-driven construction.
  - Preserve SEC User-Agent warning and skip warning messages.
- Modify: `tests/core/test_builder.py`
  - Add RED tests for declarative source specs, duplicate id rejection, optional dependency gate, and SEC warning preservation.
- Create: `docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md`
  - A3 implementation spec.
- Create: `docs/superpowers/plans/2026-06-16-declarative-source-registration.md`
  - This plan.
- Modify: `docs/architecture/improvement-catalog.md`
  - Mark A3 as implemented after code lands.
- Modify: `docs/architecture/extensibility/README.md`
  - Update source extension instructions to use `SourceSpec`.
- Modify: `README.md`, `README.ko.md`, `README.zh.md`
  - Replace builder-if wording with source-spec wording.
- Modify: `docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md`
  - Link §8 to the completed A3 spec.
- Modify: `docs/superpowers/specs/2026-06-16-macro-series-registry-design.md`
  - Convert A3 non-goal wording to historical context.

---

## Task 1: SourceSpec Table and Builder Parity

**Files:**
- Modify: `tests/core/test_builder.py`
- Modify: `mimir/core/builder.py`

- [x] **Step 1: Write failing tests for source spec shape and duplicate ids**

Add tests to `tests/core/test_builder.py`:

```python
import pytest

from mimir.core.builder import BUILTIN_SOURCE_SPECS, SourceSpec, _validate_unique_source_ids
from mimir.sources.sec_edgar import SecEdgarSource


def test_builtin_source_specs_keep_existing_order():
    assert [spec.id for spec in BUILTIN_SOURCE_SPECS] == [
        "sec_edgar",
        "rss",
        "stooq",
        "dart",
        "fred",
        "ecos",
        "pykrx",
    ]


def test_duplicate_source_spec_ids_raise_value_error():
    specs = (
        SourceSpec("sec_edgar", lambda settings, cfg: SecEdgarSource(user_agent=settings.sec_user_agent)),
        SourceSpec("sec_edgar", lambda settings, cfg: SecEdgarSource(user_agent=settings.sec_user_agent)),
    )
    with pytest.raises(ValueError, match="duplicate source id"):
        _validate_unique_source_ids(specs)
```

- [x] **Step 2: Run tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/core/test_builder.py::test_builtin_source_specs_keep_existing_order tests/core/test_builder.py::test_duplicate_source_spec_ids_raise_value_error -q
```

Expected: FAIL because `BUILTIN_SOURCE_SPECS`, `SourceSpec`, and `_validate_unique_source_ids` do not exist yet.

- [x] **Step 3: Add `SourceSpec` and duplicate validation**

In `mimir/core/builder.py`, add:

```python
from dataclasses import dataclass
from collections.abc import Callable, Sequence


@dataclass(frozen=True)
class SourceSpec:
    id: str
    factory: Callable[[Settings, SourcesConfig], Source]
    required_secret_attr: str | None = None
    required_secret_name: str | None = None
    required_module: str | None = None
    missing_module_hint: str | None = None


def _validate_unique_source_ids(specs: Sequence[SourceSpec]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for spec in specs:
        if spec.id in seen:
            duplicates.add(spec.id)
        seen.add(spec.id)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate source id(s): {joined}")
```

- [x] **Step 4: Run tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/core/test_builder.py::test_builtin_source_specs_keep_existing_order tests/core/test_builder.py::test_duplicate_source_spec_ids_raise_value_error -q
```

Expected: PASS after the table exists. If `BUILTIN_SOURCE_SPECS` is not implemented yet, add the table in the next step before expecting full green.

- [x] **Step 5: Write failing tests for optional dependency gate and SEC warning**

Add tests:

```python
def test_builder_skips_pykrx_when_optional_package_missing(monkeypatch, caplog):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    with caplog.at_level(logging.WARNING):
        sources = build_sources(Settings.from_env({}))
    assert "pykrx" not in {s.meta.id for s in sources}
    assert "skipping source 'pykrx'" in " ".join(r.message for r in caplog.records)


def test_builder_includes_pykrx_when_optional_package_is_available(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: object())
    sources = build_sources(Settings.from_env({}))
    assert "pykrx" in {s.meta.id for s in sources}


def test_builder_warns_when_sec_user_agent_has_no_contact_email(caplog):
    with caplog.at_level(logging.WARNING):
        build_sources(Settings.from_env({"MIMIR_SEC_USER_AGENT": "Mimir"}))
    assert "SEC EDGAR may return 403" in " ".join(r.message for r in caplog.records)
```

- [x] **Step 6: Run tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/core/test_builder.py::test_builder_skips_pykrx_when_optional_package_missing tests/core/test_builder.py::test_builder_includes_pykrx_when_optional_package_is_available tests/core/test_builder.py::test_builder_warns_when_sec_user_agent_has_no_contact_email -q
```

Expected: at least the table-driven pykrx inclusion test should fail until `build_sources()` uses the spec gate.

- [x] **Step 7: Replace builder if-ladder with source spec iteration**

Implement `BUILTIN_SOURCE_SPECS` in `mimir/core/builder.py`:

```python
BUILTIN_SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec("sec_edgar", lambda settings, cfg: SecEdgarSource(user_agent=settings.sec_user_agent)),
    SourceSpec("rss", lambda settings, cfg: RssSource(feeds=cfg.rss_feeds)),
    SourceSpec(
        "stooq",
        lambda settings, cfg: StooqSource(api_key=settings.stooq_api_key),
        required_secret_attr="stooq_api_key",
        required_secret_name="STOOQ_API_KEY",
    ),
    SourceSpec(
        "dart",
        lambda settings, cfg: DartSource(api_key=settings.dart_api_key),
        required_secret_attr="dart_api_key",
        required_secret_name="DART_API_KEY",
    ),
    SourceSpec(
        "fred",
        lambda settings, cfg: FredSource(api_key=settings.fred_api_key, series=cfg.fred_series),
        required_secret_attr="fred_api_key",
        required_secret_name="FRED_API_KEY",
    ),
    SourceSpec(
        "ecos",
        lambda settings, cfg: EcosSource(api_key=settings.ecos_api_key, series=cfg.ecos_series),
        required_secret_attr="ecos_api_key",
        required_secret_name="ECOS_API_KEY",
    ),
    SourceSpec(
        "pykrx",
        lambda settings, cfg: PykrxSource(),
        required_module="pykrx",
        missing_module_hint="package not installed (pip install -e '.[kr]')",
    ),
)
```

Then rewrite `build_sources()` to:

```python
def build_sources(settings: Settings, config: SourcesConfig | None = None) -> list[Source]:
    if "@" not in settings.sec_user_agent:
        logger.warning(
            "MIMIR_SEC_USER_AGENT has no contact email; SEC EDGAR may return 403. "
            "Set it to e.g. 'Your Name you@example.com'."
        )
    cfg = config or SourcesConfig()
    return _build_sources_from_specs(settings, cfg, BUILTIN_SOURCE_SPECS)
```

Add helper:

```python
def _build_sources_from_specs(
    settings: Settings, config: SourcesConfig, specs: Sequence[SourceSpec]
) -> list[Source]:
    _validate_unique_source_ids(specs)
    sources: list[Source] = []
    for spec in specs:
        if spec.required_secret_attr and not getattr(settings, spec.required_secret_attr):
            logger.warning("skipping source '%s': %s is not set", spec.id, spec.required_secret_name)
            continue
        if spec.required_module and importlib.util.find_spec(spec.required_module) is None:
            logger.warning("skipping source '%s': %s", spec.id, spec.missing_module_hint)
            continue
        source = spec.factory(settings, config)
        if source.meta.id != spec.id:
            raise ValueError(f"source spec id {spec.id!r} built source id {source.meta.id!r}")
        sources.append(source)
    return sources
```

- [x] **Step 8: Run focused builder tests**

Run:

```bash
.venv/bin/pytest tests/core/test_builder.py -q
```

Expected: all builder tests pass.

- [x] **Step 9: Run focused regression suite**

Run:

```bash
.venv/bin/pytest tests/core/test_builder.py tests/core/test_registry.py tests/doctor/test_engine_matrix.py tests/sources/test_pykrx_source.py tests/test_collect.py tests/test_backfill.py -q
```

Expected: all focused tests pass.

---

## Task 2: Documentation Update for A3 Completion

**Files:**
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `docs/superpowers/specs/2026-06-13-config-driven-extensibility-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-macro-series-registry-design.md`
- Modify: `docs/superpowers/specs/2026-06-16-declarative-source-registration-design.md`
- Modify: `docs/superpowers/plans/2026-06-16-declarative-source-registration.md`

- [x] **Step 1: Update A3 status in the new spec**

After code is green, change the A3 spec status line to:

```markdown
> **상태**: ✅ 구현 완료 (`SourceSpec` built-in source table). 349 테스트 · ruff · mypy · coverage 97% 클린.
```

- [x] **Step 2: Update improvement catalog**

Change the A3 row to implemented and update the A3 section:

```markdown
| **A3** | 선언적 소스 등록 (`SourceSpec` built-in table) | 아키텍처 | README 약속(부분) | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-declarative-source-registration-design.md) |
```

The A3 section must say `build_sources()` now iterates `BUILTIN_SOURCE_SPECS`; entry-point plugins remain future work.

- [x] **Step 3: Update extensibility guide**

Replace the "builder.py 중앙 분기 추가" source-extension step with:

```markdown
3. `mimir/core/builder.py`의 `BUILTIN_SOURCE_SPECS`에 `SourceSpec` 한 줄을 추가한다.
```

Also explain that `Registry` still handles cadence/GRAY/disabled filtering after construction.

- [x] **Step 4: Update README ×3**

In each README, replace wording that says a new source requires builder if-branch registration with wording that says it requires a `SourceSpec` registration entry.

- [x] **Step 5: Update related specs**

In `2026-06-13-config-driven-extensibility-design.md`, replace §8 with a short pointer to the new A3 spec and completed status.

In `2026-06-16-macro-series-registry-design.md`, keep the original non-goal as historical context but say A3 is now completed by the new spec.

- [x] **Step 6: Run stale wording scan**

Run:

```bash
rg -n "A3.*설계|A3.*future|future.*A3|builder 등록|builder 분기|if-사다리|if ladder|지금 설계" README.md README.ko.md README.zh.md docs
```

Expected: remaining hits are either historical context or explicitly say A3 is implemented / entry-point is future.

---

## Task 3: Final Verification and Review

**Files:**
- All touched files

- [x] **Step 1: Run formatting/lint/type gates**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy mimir
git diff --check
```

Expected: all pass.

- [x] **Step 2: Run full coverage gate**

Run:

```bash
.venv/bin/coverage run -m pytest
.venv/bin/coverage report --fail-under=80
```

Expected: all tests pass and coverage is at least 80%.

- [x] **Step 3: Request final code review**

Ask a reviewer to inspect the full branch diff against `main`. The reviewer must check:

- `build_sources()` parity
- optional dependency gates
- duplicate id validation
- doctor expected coverage separation
- docs accuracy

- [x] **Step 4: Address reviewer findings**

Fix Critical/Important findings and rerun the relevant focused tests plus final gates.

- [x] **Step 5: Commit locally**

Run:

```bash
git add -A
git commit -m "feat: add declarative source registration"
```

Do not push unless the user explicitly asks for push/merge for this branch.
