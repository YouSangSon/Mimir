# Analysis Signal Specs Injection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public `build_signals(..., specs=...)` seam so tests and embedded callers can inject external analysis signal specs without entry point packaging.

**Architecture:** Keep built-in signals on `BUILTIN_SIGNAL_SPECS` and treat `specs` as external/plugin specs only. `specs=None` preserves current entry point behavior; any provided `specs` tuple skips entry point reads and still requires `analysis.plugins.<signal_id>` opt-in. Duplicate ids are validated across built-ins and injected plugin specs.

**Tech Stack:** Python 3.14, pytest, `SignalSpec`, `SourcesConfig.analysis_plugin_settings`, existing analysis builder plugin warnings.

## Global Constraints

- Do not touch, stage, remove, or rewrite the pre-existing untracked `uv.lock`.
- Runtime write scope is `mimir/analysis/builder.py` and `tests/analysis/test_builder.py`.
- Documentation write scope is `docs/decisions/tech-spec/analysis/AN5_analysis_signal_specs_injection_tech_spec_2026_06_25.md`, `docs/decisions/tech-spec/README.md`, `docs/reference/config/sources.md`, `docs/architecture/extensibility/README.md`, `docs/architecture/improvement-catalog.md`, `tests/test_readme_docs.py`, `README.md`, `README.ko.md`, and `README.zh.md`.
- `specs` on `build_signals()` means external/plugin signal specs only; it must not replace built-in signals.
- Built-in signals must continue to come from `BUILTIN_SIGNAL_SPECS` and appear before plugin signals.
- When `specs is None`, preserve existing entry point discovery behavior: default path does not read entry points, configured plugin path reads `mimir.analysis_signals`.
- When `specs` is provided, do not read entry points.
- Injected plugin specs must still require `analysis.plugins.<signal_id>` config before their factories run.
- Explicit `specs=()` with non-empty `analysis.plugins` must still warn for unmatched plugin config.
- Validate duplicate ids across `(*BUILTIN_SIGNAL_SPECS, *plugin_specs)` before building plugin specs.
- Do not change `Signal`, `SignalResult`, scorer math, engine behavior, source collection, plugin sandbox policy, LLM enablement, retry policy, network behavior, or storage layout.

---

### Task 1: Public `build_signals()` Specs Injection

**Files:**
- Modify: `tests/analysis/test_builder.py`
- Modify: `mimir/analysis/builder.py`
- Modify: `docs/decisions/tech-spec/analysis/AN5_analysis_signal_specs_injection_tech_spec_2026_06_25.md`
- Modify: `docs/decisions/tech-spec/README.md`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `tests/test_readme_docs.py`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`

**Interfaces:**
- Consumes: `SignalSpec(id: str, factory: Callable[[Settings, SourcesConfig], Signal], ...)`
- Produces: `build_signals(config=None, settings=None, *, classifier=None, specs=None) -> list[Signal]`

- [ ] **Step 1: Write failing public injection test**

Add this test near the existing plugin builder tests in `tests/analysis/test_builder.py`:

```python
def test_build_signals_accepts_injected_plugin_specs_after_builtins(monkeypatch):
    def fail_entry_points(*args, **kwargs):
        raise AssertionError("entry points should not be read when specs are injected")

    monkeypatch.setattr(
        "mimir.analysis.builder.importlib.metadata.entry_points",
        fail_entry_points,
    )
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    cfg = SourcesConfig(analysis_plugin_settings={"plugin_quality": {"enabled": True}})

    signals = build_signals(cfg, specs=(spec,))

    assert [signal.id for signal in signals] == [
        "filing_event",
        "news_volume",
        "price_momentum",
        "macro_regime",
        "plugin_quality",
    ]
```

- [ ] **Step 2: Verify RED for public injection**

Run:

```bash
uv run pytest tests/analysis/test_builder.py::test_build_signals_accepts_injected_plugin_specs_after_builtins -q
```

Expected: FAIL with `TypeError: build_signals() got an unexpected keyword argument 'specs'`.

- [ ] **Step 3: Write failing entry point bypass test**

Add this test:

```python
def test_build_signals_with_injected_specs_does_not_read_entry_points(monkeypatch):
    def fail_entry_points(*args, **kwargs):
        raise AssertionError("entry points should not be read when specs are injected")

    monkeypatch.setattr(
        "mimir.analysis.builder.importlib.metadata.entry_points",
        fail_entry_points,
    )
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())
    cfg = SourcesConfig(analysis_plugin_settings={"plugin_quality": {"enabled": True}})

    signals = build_signals(cfg, specs=(spec,))

    assert "plugin_quality" in _ids(signals)
```

- [ ] **Step 4: Verify RED for entry point bypass**

Run:

```bash
uv run pytest tests/analysis/test_builder.py::test_build_signals_with_injected_specs_does_not_read_entry_points -q
```

Expected: FAIL with `TypeError: build_signals() got an unexpected keyword argument 'specs'`.

- [ ] **Step 5: Write failing opt-in guard test**

Add this test:

```python
def test_build_signals_injected_specs_still_require_analysis_plugin_config(monkeypatch):
    def fail_entry_points(*args, **kwargs):
        raise AssertionError("entry points should not be read when specs are injected")

    monkeypatch.setattr(
        "mimir.analysis.builder.importlib.metadata.entry_points",
        fail_entry_points,
    )
    spec = SignalSpec("plugin_quality", lambda settings, cfg: _FakeSignal())

    signals = build_signals(specs=(spec,))

    assert _ids(signals) == BASE_SIGNAL_IDS
```

- [ ] **Step 6: Verify RED for opt-in guard**

Run:

```bash
uv run pytest tests/analysis/test_builder.py::test_build_signals_injected_specs_still_require_analysis_plugin_config -q
```

Expected: FAIL with `TypeError: build_signals() got an unexpected keyword argument 'specs'`.

- [ ] **Step 7: Write failing duplicate built-in id test**

Add this test:

```python
def test_build_signals_injected_duplicate_builtin_signal_id_raises():
    spec = SignalSpec("news_volume", lambda settings, cfg: _FakeSignal())
    cfg = SourcesConfig(analysis_plugin_settings={"news_volume": {}})

    with pytest.raises(ValueError, match="duplicate signal id"):
        build_signals(cfg, specs=(spec,))
```

- [ ] **Step 8: Verify RED for duplicate built-in id**

Run:

```bash
uv run pytest tests/analysis/test_builder.py::test_build_signals_injected_duplicate_builtin_signal_id_raises -q
```

Expected: FAIL with `TypeError: build_signals() got an unexpected keyword argument 'specs'`.

- [ ] **Step 9: Write failing explicit empty specs warning test**

Add this test:

```python
def test_build_signals_empty_injected_specs_warns_for_unmatched_plugin_config(caplog):
    cfg = SourcesConfig(analysis_plugin_settings={"missing_signal": {"enabled": True}})

    with caplog.at_level(logging.WARNING):
        signals = build_signals(cfg, specs=())

    assert _ids(signals) == BASE_SIGNAL_IDS
    assert "analysis plugin config 'missing_signal' has no matching signal spec" in " ".join(
        r.message for r in caplog.records
    )
```

- [ ] **Step 10: Verify RED for explicit empty specs warning**

Run:

```bash
uv run pytest tests/analysis/test_builder.py::test_build_signals_empty_injected_specs_warns_for_unmatched_plugin_config -q
```

Expected: FAIL with `TypeError: build_signals() got an unexpected keyword argument 'specs'`.

- [ ] **Step 11: Implement minimal builder API**

Modify `mimir/analysis/builder.py`:

```python
def build_signals(
    config: SourcesConfig | None = None,
    settings: Settings | None = None,
    *,
    classifier: HeadlineClassifier | None = None,
    specs: Sequence[SignalSpec] | None = None,
) -> list[Signal]:
```

Replace the plugin entry point branch with:

```python
    if specs is None:
        plugin_specs = _load_entry_point_signal_specs() if cfg.analysis_plugin_settings else ()
    else:
        plugin_specs = tuple(specs)
    if cfg.analysis_plugin_settings or plugin_specs:
        _validate_unique_signal_ids((*BUILTIN_SIGNAL_SPECS, *plugin_specs))
        signals.extend(_build_signals_from_specs(settings, cfg, plugin_specs))
```

- [ ] **Step 12: Verify GREEN for builder tests**

Run:

```bash
uv run pytest tests/analysis/test_builder.py -q
```

Expected: all builder tests pass.

- [ ] **Step 13: Update docs and docs guards**

Update `docs/decisions/tech-spec/analysis/AN5_analysis_signal_specs_injection_tech_spec_2026_06_25.md` status from `Draft` to `Implemented`.

Update `docs/decisions/tech-spec/README.md` analysis table with:

```markdown
| [AN5-ANALYSIS-SIGNAL-SPECS-INJECTION](analysis/AN5_analysis_signal_specs_injection_tech_spec_2026_06_25.md) | `build_signals(..., specs=...)`로 entry point 없이 외부 signal specs를 직접 주입 |
```

Update `docs/reference/config/sources.md` section 3.3 to state:

```markdown
테스트나 임베디드 호출자는 `build_signals(..., specs=(SignalSpec(...),))`로 외부 plugin specs를 직접 주입할 수 있다. 이 경우 entry point discovery는 건너뛰지만, 주입된 spec도 `analysis.plugins.<signal_id>` 설정이 있어야 build된다. `specs`는 built-in replacement가 아니라 외부 plugin spec 목록이다.
```

Update `docs/architecture/extensibility/README.md` section 4.4 with the same contract:

```markdown
Entry point packaging 없이 실행하는 테스트·임베디드 host는 `build_signals(..., specs=...)`에 `SignalSpec` tuple을 넘길 수 있다. 이 direct injection path는 entry point를 읽지 않고, built-in signal 뒤에 configured injected plugin signal만 붙인다.
```

Update `tests/test_readme_docs.py`:

```python
LATEST_COMPLETED_IDS = (
    "AN5-ANALYSIS-SIGNAL-SPECS-INJECTION",
    "AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION",
    ...
)
```

```python
    "AN5-ANALYSIS-SIGNAL-SPECS-INJECTION": Path(
        "docs/decisions/tech-spec/analysis/"
        "AN5_analysis_signal_specs_injection_tech_spec_2026_06_25.md"
    ),
```

Update `docs/architecture/improvement-catalog.md`:

- Add `AN5-ANALYSIS-SIGNAL-SPECS-INJECTION` to the status line.
- Add an implemented row after AN4 in the summary table.
- Add a subsection after AN4 explaining the direct injection seam.
- Add AN5 to the sequencing list and conclusion.

Update README test counts from `620` to the new collected count after adding five builder tests. Expected new count: `625`. Update all three README files' badge and test table rows.

- [ ] **Step 14: Run targeted verification**

Run:

```bash
uv run pytest tests/analysis/test_builder.py tests/test_readme_docs.py -q
```

Expected: all selected tests pass.

- [ ] **Step 15: Run full gates**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: full suite passes, ruff passes, mypy passes, diff check passes.

- [ ] **Step 16: Commit implementation**

Stage exact files only:

```bash
git add mimir/analysis/builder.py tests/analysis/test_builder.py docs/decisions/tech-spec/analysis/AN5_analysis_signal_specs_injection_tech_spec_2026_06_25.md docs/decisions/tech-spec/README.md docs/reference/config/sources.md docs/architecture/extensibility/README.md docs/architecture/improvement-catalog.md tests/test_readme_docs.py README.md README.ko.md README.zh.md
git commit -m "feat(analysis): inject signal specs through build_signals"
```
