# Macro Series Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 거시 경제 시리즈의 기본 수집 목록, 분석용 rate-series 목록, doctor freshness cadence를 한 모듈에서 관리한다.

**Architecture:** `mimir/core/macro_series.py`를 새 단일 진실원으로 둔다. FRED/ECOS source defaults, `MacroRegimeSignal`, doctor expectations, `sources.yaml` 분석 설정이 이 모듈이나 `SourcesConfig`를 통해 같은 메타데이터를 사용한다.

**Tech Stack:** Python 3.14, pydantic config validation, pytest, ruff, mypy.

---

### Task 1: Macro Series Metadata Module

**Files:**
- Create: `mimir/core/macro_series.py`
- Modify: `mimir/sources/fred.py`
- Modify: `mimir/sources/ecos.py`
- Modify: `mimir/doctor/expectations.py`
- Test: `tests/core/test_macro_series.py`

- [x] **Step 1: Write failing tests**

```python
from mimir.core.source import Cadence
from mimir.core.macro_series import (
    default_ecos_series_specs,
    default_fred_series,
    default_macro_rate_series,
    macro_series_cadences,
)
from mimir.doctor.expectations import MACRO_SERIES_CADENCE
from mimir.sources.ecos import DEFAULT_SERIES as ECOS_DEFAULT_SERIES
from mimir.sources.fred import DEFAULT_SERIES as FRED_DEFAULT_SERIES


def test_default_source_series_come_from_macro_metadata():
    assert FRED_DEFAULT_SERIES == default_fred_series()
    assert [(s.stat_code, s.cycle, s.item_code) for s in ECOS_DEFAULT_SERIES] == [
        (s.stat_code, s.cycle, s.item_code) for s in default_ecos_series_specs()
    ]


def test_doctor_cadence_comes_from_macro_metadata():
    assert MACRO_SERIES_CADENCE == macro_series_cadences()
    assert MACRO_SERIES_CADENCE["DGS10"] is Cadence.DAILY
    assert MACRO_SERIES_CADENCE["FEDFUNDS"] is Cadence.MONTHLY


def test_default_rate_series_excludes_non_rate_macro_series():
    rate_series = set(default_macro_rate_series())
    assert {"DGS10", "FEDFUNDS", "722Y001.0101000"} <= rate_series
    assert "CPIAUCSL" not in rate_series
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_macro_series.py -q`

Expected: FAIL because `mimir.core.macro_series` does not exist yet.

- [x] **Step 3: Add metadata module and rewire defaults**

Create `mimir/core/macro_series.py` with frozen dataclasses for `EcosSeriesSpec` and `MacroSeriesMeta`. Export `default_fred_series()`, `default_ecos_series_specs()`, `default_macro_rate_series()`, and `macro_series_cadences()`.

Update `mimir/sources/fred.py` to set `DEFAULT_SERIES = default_fred_series()`.

Update `mimir/sources/ecos.py` to build `DEFAULT_SERIES` from `default_ecos_series_specs()`.

Update `mimir/doctor/expectations.py` to set `MACRO_SERIES_CADENCE = macro_series_cadences()`.

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_macro_series.py -q`

Expected: PASS.

### Task 2: Configurable Macro Regime Rate Series

**Files:**
- Modify: `mimir/sources/config.py`
- Modify: `mimir/analysis/signals/macro_regime.py`
- Modify: `mimir/analysis/builder.py`
- Test: `tests/sources/test_config.py`
- Test: `tests/analysis/signals/test_signals.py`
- Test: `tests/analysis/test_builder.py`

- [x] **Step 1: Write failing tests**

```python
def test_analysis_macro_regime_rate_series_parses_from_config():
    cfg = parse_sources_config({"analysis": {"macro_regime": {"rate_series": ["T10Y2Y"]}}})
    assert cfg.macro_regime_rate_series == ["T10Y2Y"]


def test_analysis_macro_regime_typo_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config({"analysis": {"macro_regime": {"rate_seriez": ["T10Y2Y"]}}})
```

```python
def test_macro_regime_uses_configured_rate_series(tmp_path: Path):
    def _macro_for(series_id: str, value: float) -> dict:
        return {"series_id": series_id, "value": value, "period": "2026-01-15"}

    recs = [
        _rec(Dataset.MACRO, "T10Y2Y", 1, _macro_for("T10Y2Y", 0.5)),
        _rec(Dataset.MACRO, "T10Y2Y", 20, _macro_for("T10Y2Y", 0.8)),
    ]
    default = MacroRegimeSignal().evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    configured = MacroRegimeSignal(rate_series=["T10Y2Y"]).evaluate(
        "AAPL", Market.US, AS_OF, _reader(tmp_path, recs)
    )
    assert default is None
    assert configured is not None
    assert configured.direction is SignalDirection.BEARISH
```

```python
def test_build_signals_passes_macro_rate_series_config(tmp_path: Path):
    cfg = SourcesConfig(macro_regime_rate_series=["T10Y2Y"])
    macro = next(s for s in build_signals(cfg) if s.id == "macro_regime")
    assert isinstance(macro, MacroRegimeSignal)
    recs = [
        _rec(Dataset.MACRO, "T10Y2Y", 1, _macro_for("T10Y2Y", 0.5)),
        _rec(Dataset.MACRO, "T10Y2Y", 20, _macro_for("T10Y2Y", 0.8)),
    ]
    result = macro.evaluate("AAPL", Market.US, AS_OF, _reader(tmp_path, recs))
    assert result is not None
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest \
  tests/sources/test_config.py::test_analysis_macro_regime_rate_series_parses_from_config \
  tests/sources/test_config.py::test_analysis_macro_regime_typo_raises_validation_error \
  tests/analysis/signals/test_signals.py::test_macro_regime_uses_configured_rate_series \
  tests/analysis/test_builder.py::test_build_signals_passes_macro_rate_series_config \
  -q
```

Expected: FAIL because the config field and `MacroRegimeSignal(rate_series=...)` constructor do not exist.

- [x] **Step 3: Implement minimal config and signal wiring**

Add `macro_regime_rate_series: list[str] | None = None` to `SourcesConfig`.

Add validated nested blocks `_AnalysisBlock` and `_MacroRegimeBlock` so `analysis.macro_regime.rate_series` accepts a list of strings and rejects typo keys.

Update `MacroRegimeSignal.__init__(rate_series=None)` to use `default_macro_rate_series()` when omitted and the configured set when provided.

Update `build_signals()` to construct `MacroRegimeSignal(rate_series=cfg.macro_regime_rate_series)`.

- [x] **Step 4: Run tests to verify they pass**

Run the same focused pytest command from Step 2.

Expected: PASS.

### Task 3: Documentation and Verification

**Files:**
- Modify: `config/sources.yaml`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/IMPROVEMENTS.md`
- Create: `docs/superpowers/specs/2026-06-16-macro-series-registry-design.md`

- [x] **Step 1: Update config reference**

Document:

```yaml
analysis:
  macro_regime:
    rate_series: ["DGS10", "FEDFUNDS", "722Y001.0101000"]
```

Explain that `sources.fred/ecos.series` controls collection, while `analysis.macro_regime.rate_series` controls which collected macro series can influence the market-wide macro signal.

- [x] **Step 2: Update architecture docs**

Move A2 from “future debt” to implemented. Keep A3 as future debt.

- [x] **Step 3: Run full verification**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy mimir
.venv/bin/coverage run -m pytest
.venv/bin/coverage report --fail-under=80
```

Expected: ruff passes, mypy passes, pytest passes, coverage stays at or above 80%.

---

## Self-Review

- Spec coverage: A2 duplication is removed for default source series, macro signal rate-series defaults, and doctor macro cadence. User-configured analysis rate-series is explicit under `analysis.macro_regime.rate_series`.
- Placeholder scan: no `TBD`, `TODO`, or “similar to” steps remain.
- Non-goal: A3 source registration is not implemented. `build_sources` can keep its current `if settings.X_api_key` ladder.
