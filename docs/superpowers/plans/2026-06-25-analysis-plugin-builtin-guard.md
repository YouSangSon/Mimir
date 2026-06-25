# Analysis Plugin Built-in Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `analysis.plugins` warn clearly when a user targets a built-in analysis signal instead of an external plugin signal.

**Architecture:** Reuse the source builder's warning shape, but keep analysis builder's conservative plugin discovery policy. The change is limited to warning classification and documentation; signal construction and scoring stay unchanged.

**Tech Stack:** Python 3.14, pytest `caplog`, Mimir analysis builder, pydantic `SourcesConfig`, docs health tests.

## Global Constraints

- Preserve built-in signal order: `filing_event`, `news_volume`, `price_momentum`, `macro_regime`.
- Preserve `llm_sentiment_enabled: false` as the default.
- Do not import `anthropic` on default paths.
- Do not read entry points when `analysis.plugins` is empty.
- Do not add network calls, retries, storage schema, or cache.
- Keep `analysis.plugins` external-plugin-only.
- `uv.lock` is a pre-existing untracked file and must not be edited, staged, or removed.

---

## File Structure

- Modify `mimir/analysis/builder.py`: classify built-in analysis signal ids before generic unmatched plugin warning.
- Modify `tests/analysis/test_builder.py`: add focused caplog tests for configurable built-in and `llm_sentiment` misuse.
- Modify `docs/reference/config/sources.md`: state that built-in signals do not read `analysis.plugins` and list the right keys.
- Modify `docs/architecture/extensibility/README.md`: mirror the trust/namespace warning in the extension guide.
- Modify `docs/architecture/improvement-catalog.md`: record AN3 as implemented.
- Modify `docs/decisions/tech-spec/README.md`: add AN3.
- Modify `README.md`, `README.ko.md`, `README.zh.md`: update collected test count after adding tests.
- Modify `tests/test_readme_docs.py`: add AN3 to latest completed ids and completed tech spec status guard after implementation.

## Task 1: Built-in Analysis Plugin Warning Guard

**Files:**
- Modify: `mimir/analysis/builder.py`
- Modify: `tests/analysis/test_builder.py`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/decisions/tech-spec/README.md`
- Modify: `docs/decisions/tech-spec/analysis/AN3_analysis_plugin_builtin_guard_tech_spec_2026_06_25.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `tests/test_readme_docs.py`

**Interfaces:**
- Consumes: `SourcesConfig.analysis_plugin_settings`
- Consumes: `_warn_for_unmatched_analysis_plugin_settings(config, specs)`
- Produces: warning for built-in signal ids before generic missing plugin warning

- [ ] **Step 1: Add RED tests for built-in misuse**

Add these tests near `test_builder_warns_for_unmatched_analysis_plugin_config` in `tests/analysis/test_builder.py`:

```python
def test_builder_warns_when_analysis_plugin_namespace_targets_configurable_builtin_signal(
    caplog,
):
    cfg = SourcesConfig(analysis_plugin_settings={"news_volume": {"enabled": True}})

    with caplog.at_level(logging.WARNING):
        signals = _build_signals_from_specs(Settings.from_env({}), cfg, ())

    assert signals == []
    messages = " ".join(r.message for r in caplog.records)
    assert "analysis plugin config 'news_volume' targets built-in signal 'news_volume'" in messages
    assert "use analysis.news instead" in messages
    assert "has no matching signal spec" not in messages


def test_builder_warns_when_analysis_plugin_namespace_targets_llm_sentiment(caplog):
    cfg = SourcesConfig(analysis_plugin_settings={"llm_sentiment": {"enabled": True}})

    with caplog.at_level(logging.WARNING):
        signals = _build_signals_from_specs(Settings.from_env({}), cfg, ())

    assert signals == []
    messages = " ".join(r.message for r in caplog.records)
    assert "analysis plugin config 'llm_sentiment' targets built-in signal 'llm_sentiment'" in messages
    assert "use llm_sentiment_enabled instead" in messages
    assert "has no matching signal spec" not in messages
```

- [ ] **Step 2: Run RED**

Run:

```bash
uv run pytest \
  tests/analysis/test_builder.py::test_builder_warns_when_analysis_plugin_namespace_targets_configurable_builtin_signal \
  tests/analysis/test_builder.py::test_builder_warns_when_analysis_plugin_namespace_targets_llm_sentiment \
  -q
```

Expected: FAIL because the current builder emits only the generic unmatched plugin warning.

- [ ] **Step 3: Implement built-in signal warning classification**

In `mimir/analysis/builder.py`, add constants after `BUILTIN_SIGNAL_SPECS`:

```python
BUILTIN_SIGNAL_CONFIG_HINTS = {
    "news_volume": "analysis.news instead",
    "macro_regime": "analysis.macro_regime instead",
    "llm_sentiment": "llm_sentiment_enabled instead",
}
BUILTIN_ANALYSIS_SIGNAL_IDS = {
    *(spec.id for spec in BUILTIN_SIGNAL_SPECS),
    "llm_sentiment",
}
```

Then update `_warn_for_unmatched_analysis_plugin_settings()`:

```python
    for signal_id in sorted(config.analysis_plugin_settings):
        if signal_id in BUILTIN_ANALYSIS_SIGNAL_IDS:
            if signal_id in BUILTIN_SIGNAL_CONFIG_HINTS:
                logger.warning(
                    "analysis plugin config '%s' targets built-in signal '%s'; use %s",
                    signal_id,
                    signal_id,
                    BUILTIN_SIGNAL_CONFIG_HINTS[signal_id],
                )
            else:
                logger.warning(
                    "analysis plugin config '%s' targets built-in signal '%s'; "
                    "built-in signals do not read analysis.plugins",
                    signal_id,
                    signal_id,
                )
        elif signal_id not in signal_ids:
            logger.warning(
                "analysis plugin config '%s' has no matching signal spec",
                signal_id,
            )
```

- [ ] **Step 4: Run GREEN for builder tests**

Run:

```bash
uv run pytest tests/analysis/test_builder.py -q
```

Expected: PASS.

- [ ] **Step 5: Update docs**

In `docs/reference/config/sources.md` §3.3, add that `analysis.plugins` is external-plugin-only and built-in signals use their documented keys (`analysis.news`, `analysis.macro_regime`, `llm_sentiment_enabled`).

In `docs/architecture/extensibility/README.md` §4.4, add the same namespace warning near the plugin config example.

In `docs/architecture/improvement-catalog.md`, add AN3 in the summary table, analysis section, roadmap map, and conclusion.

In `docs/decisions/tech-spec/README.md`, add the AN3 spec under `analysis`.

Mark the AN3 tech spec status `Implemented`.

- [ ] **Step 6: Update docs health metadata**

After adding two builder tests, update README test count from `614` to `616` in all README badge/table entries.

In `tests/test_readme_docs.py`, add `AN3-ANALYSIS-PLUGIN-BUILTIN-GUARD` to `LATEST_COMPLETED_IDS` and `LATEST_COMPLETED_TECH_SPECS`.

- [ ] **Step 7: Run verification gates**

Run:

```bash
uv run pytest tests/analysis/test_builder.py -q
uv run pytest tests/test_readme_docs.py -q
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: all pass.

- [ ] **Step 8: Commit and update progress**

Append to `.git/sdd/progress.md`:

```text
AN3-ANALYSIS-PLUGIN-BUILTIN-GUARD: complete (commit <hash>, review clean, RED/GREEN built-in plugin warning tests, 616 full tests/ruff/mypy/diff check)
```

Commit only intended files. Do not stage `uv.lock`.

```bash
git add \
  mimir/analysis/builder.py \
  tests/analysis/test_builder.py \
  docs/reference/config/sources.md \
  docs/architecture/extensibility/README.md \
  docs/architecture/improvement-catalog.md \
  docs/decisions/tech-spec/README.md \
  docs/decisions/tech-spec/analysis/AN3_analysis_plugin_builtin_guard_tech_spec_2026_06_25.md \
  docs/superpowers/plans/2026-06-25-analysis-plugin-builtin-guard.md \
  README.md README.ko.md README.zh.md \
  tests/test_readme_docs.py
git commit -m "fix(analysis): clarify built-in signal plugin config warnings"
```

## Self-Review

- Spec coverage: AN3 goals map to Task 1 steps 1-8.
- Placeholder scan: no unresolved placeholders.
- Type consistency: warning constants use existing `SignalSpec.id` strings and `SourcesConfig.analysis_plugin_settings`.
