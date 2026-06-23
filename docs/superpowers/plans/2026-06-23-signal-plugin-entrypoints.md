# Signal Plugin Entry Points Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 외부 Python package가 Mimir repo 수정 없이 분석 시그널을 추가할 수 있도록 `mimir.analysis_signals` entry point와 `analysis.plugins.<signal_id>` 설정 namespace를 추가한다.

**Architecture:** Source plugin의 `SourceSpec` 패턴을 분석 시그널에 맞게 좁혀 적용한다. 내장 signal은 `BUILTIN_SIGNAL_SPECS`로 정리하고, 외부 signal은 설치만으로 자동 실행하지 않고 `analysis.plugins.<signal_id>` 설정이 있을 때만 생성한다. `AnalysisEngine`, `score()`, JSONL 저장 레이아웃, `SignalResult` schema는 바꾸지 않는다.

**Tech Stack:** Python 3.14, pydantic v2, importlib.metadata entry points, pytest, ruff, mypy.

## Global Constraints

- Preserve `build_signals()` no-args behavior: exactly `filing_event`, `news_volume`, `price_momentum`, `macro_regime`.
- Preserve the default no-`anthropic` import invariant.
- Do not change `AnalysisEngine`, `score()`, `Insight`, `SignalResult`, JSONL partition layout, or `idempotency_key` format.
- Do not expose signal weight YAML tuning.
- Do not auto-enable signal plugins just because a package is installed. A plugin signal requires `analysis.plugins.<signal_id>` config.
- Use entry point group name exactly `mimir.analysis_signals`.
- Keep `sources.plugins` source-only. Add signal plugin settings under `analysis.plugins`.
- Plugin code is trusted in-process code; document that Mimir does not sandbox it.
- Follow TDD: add failing tests and verify RED before production code changes.

---

### Task 1: Analysis Plugin Config Namespace

**Files:**
- Modify: `mimir/sources/config.py`
- Modify: `tests/sources/test_config.py`

**Interfaces:**
- Produces: `SourcesConfig.analysis_plugin_settings: dict[str, dict[str, Any]]`
- Produces: `SourcesConfig.analysis_plugin_config(signal_id: str) -> dict[str, Any]`
- Produces: `SourcesConfig.parse_analysis_plugin_config(signal_id: str, model: type[PluginConfig]) -> PluginConfig`
- Changes parser: `analysis.plugins.<signal_id>` is accepted only when each plugin block is a mapping.

- [ ] **Step 1: Write failing config tests**

Add these tests near the existing plugin config tests in `tests/sources/test_config.py`:

```python
def test_analysis_plugins_namespace_parses_mapping():
    cfg = parse_sources_config(
        {
            "analysis": {
                "plugins": {
                    "acme_quality": {"threshold": 0.7, "symbols": ["AAPL"]},
                }
            }
        }
    )

    assert cfg.analysis_plugin_settings == {
        "acme_quality": {"threshold": 0.7, "symbols": ["AAPL"]}
    }


def test_analysis_plugins_namespace_rejects_non_mapping_plugin_config():
    with pytest.raises(ValidationError):
        parse_sources_config({"analysis": {"plugins": {"acme_quality": "enabled"}}})


def test_analysis_plugin_config_returns_copy_and_empty_default():
    cfg = SourcesConfig(analysis_plugin_settings={"acme_quality": {"threshold": 0.7}})

    plugin_cfg = cfg.analysis_plugin_config("acme_quality")
    plugin_cfg["threshold"] = 0.1

    assert cfg.analysis_plugin_config("acme_quality") == {"threshold": 0.7}
    assert cfg.analysis_plugin_config("missing") == {}


def test_parse_analysis_plugin_config_validates_with_pydantic_model():
    class AcmeSignalConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")
        threshold: float

    cfg = SourcesConfig(analysis_plugin_settings={"acme_quality": {"threshold": 0.7}})

    parsed = cfg.parse_analysis_plugin_config("acme_quality", AcmeSignalConfig)

    assert parsed.threshold == 0.7


def test_parse_analysis_plugin_config_rejects_plugin_schema_drift():
    class AcmeSignalConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")
        threshold: float

    cfg = SourcesConfig(
        analysis_plugin_settings={"acme_quality": {"threshold": 0.7, "threshhold": 0.1}}
    )

    with pytest.raises(ValidationError):
        cfg.parse_analysis_plugin_config("acme_quality", AcmeSignalConfig)
```

If `BaseModel`, `ConfigDict`, or `ValidationError` are missing from the file imports, import them from pydantic.

- [ ] **Step 2: Run RED config tests**

Run:

```bash
uv run pytest \
  tests/sources/test_config.py::test_analysis_plugins_namespace_parses_mapping \
  tests/sources/test_config.py::test_analysis_plugins_namespace_rejects_non_mapping_plugin_config \
  tests/sources/test_config.py::test_analysis_plugin_config_returns_copy_and_empty_default \
  tests/sources/test_config.py::test_parse_analysis_plugin_config_validates_with_pydantic_model \
  tests/sources/test_config.py::test_parse_analysis_plugin_config_rejects_plugin_schema_drift \
  -q
```

Expected: FAIL because `analysis.plugins` and analysis plugin helpers do not exist.

- [ ] **Step 3: Implement namespace and helpers**

In `mimir/sources/config.py`, add to `SourcesConfig`:

```python
analysis_plugin_settings: dict[str, dict[str, Any]] = Field(default_factory=dict)

def analysis_plugin_config(self, signal_id: str) -> dict[str, Any]:
    """Return a copy of the analysis plugin config block for ``signal_id``."""
    return dict(self.analysis_plugin_settings.get(signal_id, {}))

def parse_analysis_plugin_config(
    self, signal_id: str, model: type[PluginConfig]
) -> PluginConfig:
    """Validate an analysis plugin config block with the plugin-owned model."""
    return model.model_validate(self.analysis_plugin_config(signal_id))
```

Add `plugins` to `_AnalysisBlock`:

```python
plugins: dict[str, dict[str, Any]] | None = None
```

In `_source_config_from_top_level()`, pass:

```python
analysis_plugin_settings=(
    top_level.analysis.plugins if top_level.analysis and top_level.analysis.plugins else {}
),
```

- [ ] **Step 4: Run GREEN config tests**

Run the same command from Step 2. Expected: PASS.

- [ ] **Step 5: Run config file suite and commit**

Run:

```bash
uv run pytest tests/sources/test_config.py -q
uv run ruff check mimir/sources/config.py tests/sources/test_config.py
uv run mypy mimir
git diff --check
```

Commit:

```bash
git add mimir/sources/config.py tests/sources/test_config.py
git commit -m "feat(config): add analysis plugin settings namespace"
```

---

### Task 2: SignalSpec Entry Point Loader and Builder Wiring

**Files:**
- Modify: `mimir/analysis/builder.py`
- Modify: `tests/analysis/test_builder.py`

**Interfaces:**
- Produces: `SIGNAL_ENTRY_POINT_GROUP = "mimir.analysis_signals"`
- Produces: `SignalSpec`
- Produces: `BUILTIN_SIGNAL_SPECS`
- Produces: `_load_entry_point_signal_specs(group=SIGNAL_ENTRY_POINT_GROUP) -> tuple[SignalSpec, ...]`
- Produces: `load_signal_specs(group=SIGNAL_ENTRY_POINT_GROUP) -> tuple[SignalSpec, ...]`
- Produces: `_build_signals_from_specs(settings, config, specs) -> list[Signal]`
- Changes: `build_signals()` builds built-ins through specs, appends configured plugin signals after built-ins, and keeps existing LLM branch.

- [ ] **Step 1: Add failing builder tests**

Add helper classes/functions to `tests/analysis/test_builder.py`:

```python
import logging
from pydantic import BaseModel, ConfigDict

from mimir.analysis.builder import (
    BUILTIN_SIGNAL_SPECS,
    SignalSpec,
    _build_signals_from_specs,
    _load_entry_point_signal_specs,
    load_signal_specs,
)
from mimir.analysis.signals.base import SignalResult


class _FakeSignal:
    id = "plugin_quality"

    def evaluate(self, symbol, market, as_of, reader):
        return SignalResult(
            signal=self.id,
            direction=SignalDirection.NEUTRAL,
            strength=0.5,
            confidence=0.5,
            reason="plugin quality signal",
        )


class _OtherFakeSignal:
    id = "plugin_macro_quality"

    def evaluate(self, symbol, market, as_of, reader):
        return None


class _MismatchedSignal:
    id = "plugin_quality"

    def evaluate(self, symbol, market, as_of, reader):
        return None


class _FakeEntryPoint:
    def __init__(self, name, value=None, error: Exception | None = None):
        self.name = name
        self._value = value
        self._error = error

    def load(self):
        if self._error:
            raise self._error
        return self._value


def _patch_signal_entry_points(monkeypatch, entry_points):
    monkeypatch.setattr(
        "mimir.analysis.builder.importlib.metadata.entry_points",
        lambda group=None: entry_points if group == "mimir.analysis_signals" else [],
    )
```

Add tests:

```python
def test_builtin_signal_specs_keep_existing_order():
    assert [spec.id for spec in BUILTIN_SIGNAL_SPECS] == [
        "filing_event",
        "news_volume",
        "price_momentum",
        "macro_regime",
    ]


def test_load_entry_point_signal_specs_accepts_single_spec(monkeypatch):
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("plugin_quality", spec)])

    assert _load_entry_point_signal_specs() == (spec,)


def test_load_entry_point_signal_specs_accepts_sequence(monkeypatch):
    quality = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    macro_quality = SignalSpec(
        "plugin_macro_quality", lambda settings, cfg: _OtherFakeSignal()
    )
    _patch_signal_entry_points(
        monkeypatch, [_FakeEntryPoint("plugin_bundle", (quality, macro_quality))]
    )

    assert _load_entry_point_signal_specs() == (quality, macro_quality)


def test_entry_point_signal_specs_are_loaded_in_name_order(monkeypatch):
    alpha = SignalSpec("alpha_signal", lambda settings, cfg: _FakeSignal())
    zulu = SignalSpec("zulu_signal", lambda settings, cfg: _OtherFakeSignal())
    _patch_signal_entry_points(
        monkeypatch,
        [_FakeEntryPoint("zulu_signal", zulu), _FakeEntryPoint("alpha_signal", alpha)],
    )

    assert [spec.id for spec in _load_entry_point_signal_specs()] == [
        "alpha_signal",
        "zulu_signal",
    ]


def test_load_signal_specs_appends_entry_point_signals(monkeypatch):
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("plugin_quality", spec)])

    signal_ids = [loaded.id for loaded in load_signal_specs()]

    assert signal_ids == [
        "filing_event",
        "news_volume",
        "price_momentum",
        "macro_regime",
        "plugin_quality",
    ]


def test_entry_point_signal_spec_id_must_match_entry_point_name(monkeypatch):
    spec = SignalSpec("plugin_b", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("plugin_a", spec)])

    with pytest.raises(ValueError, match="entry point 'plugin_a' loaded signal spec 'plugin_b'"):
        _load_entry_point_signal_specs()


def test_broken_entry_point_signal_spec_is_skipped_and_logged(monkeypatch, caplog):
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("broken", error=RuntimeError("boom"))])

    with caplog.at_level(logging.WARNING):
        assert _load_entry_point_signal_specs() == ()

    assert "skipping analysis signal plugin 'broken'" in " ".join(
        r.message for r in caplog.records
    )


def test_entry_point_signal_wrong_object_type_raises_value_error(monkeypatch):
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("bad", object())])

    with pytest.raises(ValueError, match="entry point 'bad' must load SignalSpec"):
        _load_entry_point_signal_specs()


def test_unconfigured_plugin_signal_is_not_built(monkeypatch):
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("plugin_quality", spec)])

    signals = build_signals()

    assert "plugin_quality" not in _ids(signals)


def test_default_path_does_not_read_signal_entry_points(monkeypatch):
    def fail_entry_points(*args, **kwargs):
        raise AssertionError("entry points should not be read without analysis.plugins config")

    monkeypatch.setattr(
        "mimir.analysis.builder.importlib.metadata.entry_points",
        fail_entry_points,
    )

    signals = build_signals()

    assert _ids(signals) == [
        "filing_event",
        "news_volume",
        "price_momentum",
        "macro_regime",
    ]


def test_build_signals_includes_configured_plugin_signals_after_builtins(monkeypatch):
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("plugin_quality", spec)])
    cfg = SourcesConfig(analysis_plugin_settings={"plugin_quality": {"enabled": True}})

    signals = build_signals(cfg)

    assert [signal.id for signal in signals] == [
        "filing_event",
        "news_volume",
        "price_momentum",
        "macro_regime",
        "plugin_quality",
    ]


def test_entry_point_duplicate_builtin_signal_id_raises_value_error(monkeypatch):
    spec = SignalSpec("news_volume", lambda settings, cfg: _FakeSignal())
    _patch_signal_entry_points(monkeypatch, [_FakeEntryPoint("news_volume", spec)])

    with pytest.raises(ValueError, match="duplicate signal id"):
        build_signals(SourcesConfig(analysis_plugin_settings={"news_volume": {}}))


def test_plugin_signal_id_mismatch_raises_value_error():
    spec = SignalSpec("plugin_bad", lambda settings, cfg: _MismatchedSignal())
    cfg = SourcesConfig(analysis_plugin_settings={"plugin_bad": {}})

    with pytest.raises(
        ValueError,
        match="signal spec id 'plugin_bad' built signal id 'plugin_quality'",
    ):
        _build_signals_from_specs(Settings.from_env({}), cfg, (spec,))


def test_build_signals_passes_analysis_plugin_namespace_to_factory():
    class PluginConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")
        threshold: float

    class ConfiguredSignal:
        id = "plugin_quality"

        def __init__(self, threshold: float):
            self.threshold = threshold

        def evaluate(self, symbol, market, as_of, reader):
            return None

    def build_plugin(settings, cfg):
        plugin_cfg = cfg.parse_analysis_plugin_config("plugin_quality", PluginConfig)
        return ConfiguredSignal(threshold=plugin_cfg.threshold)

    cfg = SourcesConfig(analysis_plugin_settings={"plugin_quality": {"threshold": 0.7}})
    signals = _build_signals_from_specs(
        Settings.from_env({}), cfg, (SignalSpec("plugin_quality", build_plugin),)
    )

    assert len(signals) == 1
    assert signals[0].threshold == 0.7


def test_builder_warns_for_unmatched_analysis_plugin_config(caplog):
    cfg = SourcesConfig(analysis_plugin_settings={"missing_signal": {"enabled": True}})

    with caplog.at_level(logging.WARNING):
        signals = _build_signals_from_specs(Settings.from_env({}), cfg, ())

    assert signals == []
    assert "analysis plugin config 'missing_signal' has no matching signal spec" in " ".join(
        r.message for r in caplog.records
    )
```

- [ ] **Step 2: Run RED builder tests**

Run:

```bash
uv run pytest tests/analysis/test_builder.py -q
```

Expected: FAIL because `SignalSpec` and loader helpers do not exist.

- [ ] **Step 3: Implement SignalSpec and entry point helpers**

In `mimir/analysis/builder.py`:

- Import `importlib.metadata`, `Callable`, `Iterable`, `Mapping`, `Sequence`, `dataclass`, `cast`.
- Add `SIGNAL_ENTRY_POINT_GROUP = "mimir.analysis_signals"`.
- Add `SignalSpec`.
- Add `_validate_unique_signal_ids()`.
- Add `_entry_points_for_group()` mirroring source builder.
- Add `_signal_specs_from_entry_point()`.
- Add `_load_entry_point_signal_specs()`.
- Add `load_signal_specs()`.

Use error strings from the tests exactly:

```python
ValueError(f"duplicate signal id(s): {joined}")
ValueError(f"entry point {name!r} loaded signal spec {loaded.id!r}")
ValueError(f"entry point {name!r} must load SignalSpec objects")
```

- [ ] **Step 4: Implement `_build_signals_from_specs()` and wire `build_signals()`**

Implementation requirements:

- Built-in specs always build.
- `SignalSpec` does not expose a `builtin` flag. Built-ins are the specs passed from `BUILTIN_SIGNAL_SPECS`; plugin specs are the specs loaded from entry points.
- Plugin entry points are only read when `cfg.analysis_plugin_settings` is non-empty, or when tests/external callers explicitly call `load_signal_specs()` / `_load_entry_point_signal_specs()`.
- Plugin specs only build if `spec.id in cfg.analysis_plugin_settings`.
- Missing secret/module logs warning and skips.
- Built signal `id` mismatch raises `ValueError`.
- `build_signals()` should:
  - initialize `cfg` and `settings`
  - call `_build_signals_from_specs(settings, cfg, BUILTIN_SIGNAL_SPECS)`
  - when `cfg.analysis_plugin_settings` is non-empty, load entry point specs, validate duplicate ids against built-ins, warn for unmatched configured ids, and append matching plugin signals
  - then append `LlmSentimentSignal` using the existing `_llm_sentiment_enabled()` branch.

Keep the local import of `LlmSentimentSignal` unchanged so default path never imports `anthropic`. Also keep the default path from reading signal entry points when no `analysis.plugins` config exists.

- [ ] **Step 5: Run GREEN builder tests**

Run:

```bash
uv run pytest tests/analysis/test_builder.py -q
```

Expected: PASS.

- [ ] **Step 6: Run analysis tests and commit**

Run:

```bash
uv run pytest tests/analysis -q
uv run ruff check mimir/analysis/builder.py tests/analysis/test_builder.py
uv run mypy mimir
git diff --check
```

Commit:

```bash
git add mimir/analysis/builder.py tests/analysis/test_builder.py
git commit -m "feat(analysis): add signal plugin entry points"
```

---

### Task 3: Documentation and Truth Guards

**Files:**
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/decisions/tech-spec/README.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `tests/test_readme_docs.py`

**Interfaces:**
- Documents `mimir.analysis_signals`.
- Documents `analysis.plugins.<signal_id>`.
- Documents trust boundary and off-by-default plugin enablement.
- Adds docs guards for the new tech spec/reference links and latest catalog ID.

- [ ] **Step 1: Write failing docs guards**

In `tests/test_readme_docs.py`:

- Add `"AN1-SIGNAL-PLUGIN-ENTRYPOINTS"` to `LATEST_COMPLETED_IDS`.
- Add `"docs/decisions/tech-spec/analysis/AN1_signal_plugin_entrypoints_tech_spec_2026_06_23.md"` to `README_REQUIRED_LINKS`.
- Add a new test:

```python
def test_signal_plugin_docs_match_extension_contract() -> None:
    docs = (
        Path("docs/architecture/extensibility/README.md"),
        Path("docs/reference/config/sources.md"),
        Path("docs/architecture/improvement-catalog.md"),
    )
    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert "mimir.analysis_signals" in text, f"{path} missing signal entry point"
        assert "analysis.plugins" in text, f"{path} missing analysis plugin namespace"
        assert "sandbox" in text.lower(), f"{path} missing trust boundary"
```

- [ ] **Step 2: Run RED docs tests**

Run:

```bash
uv run pytest \
  tests/test_readme_docs.py::test_signal_plugin_docs_match_extension_contract \
  tests/test_readme_docs.py::test_improvement_catalog_summary_mentions_latest_completed_ids \
  tests/test_readme_docs.py::test_readmes_link_current_decision_and_config_docs \
  -q
```

Expected: FAIL until docs and README links are updated.

- [ ] **Step 3: Update docs**

Update `docs/architecture/extensibility/README.md`:

- Add a row to the extension table for analysis signals.
- Add a section after current analysis signal extension content:
  - `mimir.analysis_signals` entry point example.
  - `analysis.plugins.<signal_id>` config example.
  - plugin loads after built-ins and only when configured.
  - broken import warning, wrong object/duplicate/mismatch failure.
  - trust boundary: in-process, no sandbox, can read settings/config/data.

Update `docs/reference/config/sources.md`:

- Under `analysis:` block, add `analysis.plugins` subsection.
- State `analysis.plugins.<signal_id>` must be a mapping.
- State core validates only mapping; plugin validates schema with `parse_analysis_plugin_config()`.
- State secret values belong in env/GitHub Secrets, not YAML.

Update `docs/architecture/improvement-catalog.md`:

- Add `AN1-SIGNAL-PLUGIN-ENTRYPOINTS` row near A3b/A3c/B2.
- Add status line and conclusion mention.
- Add a short section explaining the new seam.
- Keep `LLM signal weight YAML 노출` in deferred state.

Update `docs/decisions/tech-spec/README.md`:

- Add the AN1 tech spec link.

Update README files:

- Add the AN1 tech spec link near the existing docs/reference links.
- Do not change test counts unless collected count changes.

- [ ] **Step 4: Run GREEN docs tests**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
```

Expected: PASS.

- [ ] **Step 5: Run docs verification and commit**

Run:

```bash
uv run pytest --collect-only -q
uv run ruff check tests/test_readme_docs.py
git diff --check
```

If collected pytest count changed, update the README test badge/table counts in all three README files and rerun `uv run pytest tests/test_readme_docs.py -q`.

Commit:

```bash
git add docs/architecture/extensibility/README.md docs/reference/config/sources.md docs/architecture/improvement-catalog.md docs/decisions/tech-spec/README.md README.md README.ko.md README.zh.md tests/test_readme_docs.py
git commit -m "docs(analysis): document signal plugin extension seam"
```

---

### Task 4: Full Verification and Final Review

**Files:**
- No planned code edits.
- Update: `.git/sdd/progress.md` local ledger after review passes.

- [ ] **Step 1: Run full local gates**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

- [ ] **Step 2: Generate review package**

Run:

```bash
MERGE_BASE=$(git merge-base origin/main HEAD)
/Users/yousang/.codex/superpowers/skills/subagent-driven-development/scripts/review-package "$MERGE_BASE" HEAD
```

- [ ] **Step 3: Request final whole-branch review**

Ask reviewer to verify:

- default `build_signals()` still returns the same built-ins and does not import `anthropic`
- plugin signals require `analysis.plugins.<id>`
- failure policy matches spec
- docs and tests reflect `mimir.analysis_signals`
- no `.superpowers/` files are tracked
- no Critical/Important findings remain

- [ ] **Step 4: Fix findings if needed**

If reviewer returns Critical/Important findings, dispatch one fix worker with the complete finding list, then re-review.

- [ ] **Step 5: Ledger**

After clean final review:

```bash
printf '%s\n' 'AN1-SIGNAL-PLUGIN-ENTRYPOINTS: complete (commits <base>..<head>, full gates 588+ passed/ruff/mypy/diff check, final review clean)' >> .git/sdd/progress.md
```
