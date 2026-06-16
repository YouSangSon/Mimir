# Source Plugin Entry Points Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 외부 Python package가 Mimir source를 `mimir.sources` entry point로 등록할 수 있게 한다.

**Architecture:** `mimir/core/builder.py`에 entry-point loader를 추가하고, `build_sources()`가 built-in `SourceSpec` 뒤에 plugin `SourceSpec`을 붙인다. Broken plugin load는 warning 후 skip하고, 잘못된 object type과 source id 충돌은 fail-fast로 실패시킨다.

**Tech Stack:** Python 3.14, `importlib.metadata`, pytest monkeypatch, ruff, mypy.

---

### Task 1: Entry-Point Loader

**Files:**
- Modify: `mimir/core/builder.py`
- Modify: `tests/core/test_builder.py`

- [x] **Step 1: Write failing single-spec loader test**

Add a fake entry point class and a test:

```python
from mimir.core.source import Cadence, Dataset, LegalStatus, Market, RateLimit, SourceMeta


class _FakeEntryPoint:
    def __init__(self, name, value):
        self.name = name
        self._value = value

    def load(self):
        return self._value


class _PluginSource:
    meta = SourceMeta(
        id="plugin_news",
        market=Market.GLOBAL,
        dataset=Dataset.NEWS,
        cadence=Cadence.HOURLY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1.0),
    )

    def fetch(self, ctx):
        return []


def test_load_entry_point_source_specs_accepts_single_spec(monkeypatch):
    spec = SourceSpec("plugin_news", lambda settings, cfg: _PluginSource())
    monkeypatch.setattr(
        "mimir.core.builder.importlib.metadata.entry_points",
        lambda group=None: [_FakeEntryPoint("plugin_news", spec)]
        if group == "mimir.sources"
        else [],
    )

    assert _load_entry_point_source_specs() == (spec,)
```

Run:

```bash
uv run pytest tests/core/test_builder.py::test_load_entry_point_source_specs_accepts_single_spec -q
```

Expected: FAIL because `_load_entry_point_source_specs` does not exist.

- [x] **Step 2: Implement minimal loader**

Add:

```python
SOURCE_ENTRY_POINT_GROUP = "mimir.sources"
```

Implement `_entry_points_for_group(group)` and `_load_entry_point_source_specs(group=SOURCE_ENTRY_POINT_GROUP)`. The loader accepts a direct `SourceSpec` or a sequence of `SourceSpec` objects.

- [x] **Step 3: Run loader test**

```bash
uv run pytest tests/core/test_builder.py::test_load_entry_point_source_specs_accepts_single_spec -q
```

Expected: PASS.

### Task 2: Build Sources Integration

**Files:**
- Modify: `mimir/core/builder.py`
- Modify: `tests/core/test_builder.py`

- [x] **Step 1: Write failing build integration test**

Add:

```python
def test_build_sources_includes_entry_point_sources_after_builtins(monkeypatch):
    spec = SourceSpec("plugin_news", lambda settings, cfg: _PluginSource())
    monkeypatch.setattr(
        "mimir.core.builder.importlib.metadata.entry_points",
        lambda group=None: [_FakeEntryPoint("plugin_news", spec)]
        if group == "mimir.sources"
        else [],
    )
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)

    sources = build_sources(Settings.from_env({}))

    assert [s.meta.id for s in sources] == ["sec_edgar", "rss", "plugin_news"]
```

Run:

```bash
uv run pytest tests/core/test_builder.py::test_build_sources_includes_entry_point_sources_after_builtins -q
```

Expected: FAIL because `build_sources()` still uses only built-ins.

- [x] **Step 2: Wire loader into build_sources**

Change:

```python
specs = (*BUILTIN_SOURCE_SPECS, *_load_entry_point_source_specs())
return _build_sources_from_specs(settings, cfg, specs)
```

- [x] **Step 3: Run builder tests**

```bash
uv run pytest tests/core/test_builder.py -q
```

Expected: PASS.

### Task 3: Failure Policy Tests

**Files:**
- Modify: `tests/core/test_builder.py`
- Modify: `mimir/core/builder.py`

- [x] **Step 1: Add sequence loading test**

Test that one entry point can load `(spec_a, spec_b)`.

- [x] **Step 2: Add broken plugin warning test**

Test that a load/call failure logs `skipping source plugin`.

- [x] **Step 3: Add duplicate id test**

Test that plugin `SourceSpec("rss", ...)` raises `ValueError`.

- [x] **Step 4: Add name/type/mismatch tests**

Test entry point name mismatch for a single spec, wrong object type, and plugin factory meta id mismatch.

- [x] **Step 5: Run focused tests**

```bash
uv run pytest tests/core/test_builder.py -q
```

Expected: PASS.

### Task 4: Documentation And Verification

**Files:**
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Create: `docs/superpowers/specs/2026-06-16-source-entry-points-design.md`
- Create: `docs/superpowers/plans/2026-06-16-source-entry-points.md`

- [x] **Step 1: Update docs**

Document `mimir.sources` entry points, plugin return shape, and failure policy.

- [x] **Step 2: Mark spec and plan checkboxes**

After verification, update acceptance checkboxes and plan status.

- [x] **Step 3: Run full verification**

```bash
uv run ruff check .
uv run mypy mimir
uv run coverage run -m pytest
uv run coverage report --fail-under=80
git diff --check
```

Expected: all commands exit 0. Final run: 397 tests passed, total coverage 97%.

- [x] **Step 4: Commit**

```bash
git add mimir tests docs README.md README.ko.md README.zh.md
git commit -m "feat: add source plugin entry points"
```
