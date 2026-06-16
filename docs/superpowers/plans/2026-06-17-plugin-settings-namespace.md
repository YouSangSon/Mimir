# Source Plugin Settings Namespace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 외부 source plugin이 Mimir core를 fork하지 않고도 `sources.yaml`에서 자기 설정을 안전하게 읽고 검증할 수 있게 한다.

**Architecture:** `sources.plugins.<source_id>` namespace를 `SourcesConfig.plugin_settings`로 보존한다. Core는 raw mapping과 pydantic validation helper만 제공한다. Plugin factory는 `cfg.parse_plugin_config(source_id, Model)`을 호출해 자기 schema를 검증한다.

**Tech Stack:** Python 3.14, pydantic v2, pytest, ruff, mypy.

---

### Task 1: Config Parser And Helper API

**Files:**
- Modify: `mimir/sources/config.py`
- Modify: `tests/sources/test_config.py`

- [x] **Step 1: Write failing namespace parse test**

Add:

```python
def test_sources_plugins_namespace_parses_mapping():
    cfg = parse_sources_config({
        "sources": {"plugins": {"acme_news": {"base_url": "https://x", "limit": 10}}}
    })
    assert cfg.plugin_settings == {"acme_news": {"base_url": "https://x", "limit": 10}}
```

Run:

```bash
uv run pytest tests/sources/test_config.py::test_sources_plugins_namespace_parses_mapping -q
```

Expected: FAIL because `sources.plugins` is currently an unknown `sources:` key.

- [x] **Step 2: Write failing plugin config validation tests**

Add:

```python
test_sources_plugins_namespace_rejects_non_mapping_plugin_config
test_plugin_config_returns_copy_and_empty_default
test_parse_plugin_config_validates_with_pydantic_model
test_parse_plugin_config_rejects_plugin_schema_drift
```

Run the four tests directly.

Expected: FAIL until `SourcesConfig.plugin_settings`, `plugin_config()`, and `parse_plugin_config()` exist.

- [x] **Step 3: Implement parser and helper API**

Update `mimir/sources/config.py`:

- Add `plugin_settings: dict[str, dict[str, Any]] = Field(default_factory=dict)` to `SourcesConfig`.
- Add `plugin_config(source_id)` returning a shallow copy.
- Add `parse_plugin_config(source_id, model)` using pydantic model validation.
- Add `plugins: dict[str, dict[str, Any]] | None = None` to `_SourcesBlock`.
- Map `_SourcesBlock.plugins` into `SourcesConfig.plugin_settings`.

- [x] **Step 4: Run focused config tests**

```bash
uv run pytest tests/sources/test_config.py -q
```

Expected: PASS.

### Task 2: Builder Warnings And Plugin Factory Consumption

**Files:**
- Modify: `mimir/core/builder.py`
- Modify: `tests/core/test_builder.py`

- [x] **Step 1: Write failing plugin factory consumption test**

Add `test_build_sources_passes_plugin_namespace_to_factory`.

The plugin `SourceSpec.factory` should call `cfg.parse_plugin_config("plugin_news", PluginCfg)` and construct a fake source with the parsed setting. Assert the source sees the configured value.

Run:

```bash
uv run pytest tests/core/test_builder.py::test_build_sources_passes_plugin_namespace_to_factory -q
```

Expected: FAIL until `SourcesConfig` exposes plugin config helpers.

- [x] **Step 2: Write failing unmatched namespace warning tests**

Add:

```python
test_builder_warns_for_unmatched_plugin_config
test_builder_warns_when_plugin_namespace_targets_builtin_source
```

Run them directly.

Expected: FAIL until builder checks plugin namespace keys against source specs and built-ins.

- [x] **Step 3: Implement builder warning helper**

Add a small helper in `mimir/core/builder.py`:

- Known source ids are the passed specs.
- Built-in ids are `BUILTIN_SOURCE_SPECS`.
- If `cfg.plugin_settings` contains a built-in id, log warning: use the built-in typed block instead.
- If a plugin config key has no matching source spec id, log warning: no matching source spec.

Call the helper after duplicate source id validation and before source construction.

- [x] **Step 4: Run focused builder tests**

```bash
uv run pytest tests/core/test_builder.py -q
```

Expected: PASS.

### Task 3: Documentation Updates

**Files:**
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `config/sources.yaml`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/superpowers/specs/2026-06-17-plugin-settings-namespace-design.md`
- Modify: `docs/superpowers/plans/2026-06-17-plugin-settings-namespace.md`

- [x] **Step 1: Update operator config docs**

Document:

- `sources.plugins.<source_id>` shape.
- Built-in source config stays under `sources.rss`, `sources.fred`, etc.
- Plugin block values must be mappings.
- Plugin factory owns schema validation with `parse_plugin_config()`.
- Secrets should stay in env vars, not in committed `sources.yaml`.

- [x] **Step 2: Update architecture docs and catalog**

Mark A3c implemented. Move plugin settings namespace out of remaining debt. Keep RSS feed discovery/catalog as the remaining explicit architecture debt.

- [x] **Step 3: Update spec/plan status after verification**

After full verification, mark acceptance criteria and plan checkboxes complete. Update test counts in docs that state them.

### Task 4: Verification, Review, Commit

**Files:** no intended source writes except review fixes.

- [x] **Step 1: Run focused tests**

```bash
uv run pytest tests/sources/test_config.py tests/core/test_builder.py -q
```

- [x] **Step 2: Run quality gates**

```bash
uv run ruff check .
uv run mypy mimir
uv run coverage run -m pytest
uv run coverage report --fail-under=80
git diff --check
```

- [x] **Step 3: Run subagent reviews**

Dispatch spec compliance review first. After it approves, dispatch code quality review.

- [x] **Step 4: Commit**

Commit only tracked intended files. Do not stage unrelated `uv.lock`.

Suggested commit:

```bash
git commit -m "feat: add source plugin config namespace"
```
