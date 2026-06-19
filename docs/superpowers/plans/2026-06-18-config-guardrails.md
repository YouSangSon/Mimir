# Config Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject malformed local operator config before it corrupts watchlist symbols or enables unsafe paid LLM headline volumes.

**Architecture:** Keep source and analysis behavior unchanged for valid configs. Add schema validation at the config boundary, then make CLI entry points report friendly config errors instead of raw exceptions or silent character-level symbol corruption.

**Tech Stack:** Python 3.14, PyYAML, pydantic v2, argparse CLIs, pytest, ruff, mypy.

## Global Constraints

- Do not add external network calls, provider discovery, SEC mapping downloads, or paid LLM calls.
- Do not change JSONL storage layout, record serialization, or existing `idempotency_key` formats.
- Valid existing configs must keep their behavior.
- Malformed `watchlist.yaml` must fail loudly and include the file path in the error surface.
- `llm_sentiment_max_headlines` must remain off-by-default with `llm_sentiment_enabled: false`.
- The maximum paid LLM headline cap is `50`; valid values are integers from `1` through `50`.
- Follow TDD: add the failing regression first, run it to verify RED, then implement.

---

### Task 1: Watchlist Schema Validation

**Files:**
- Modify: `mimir/config.py`
- Modify: `mimir/collect.py`
- Modify: `mimir/analyze.py`
- Modify: `mimir/run.py`
- Modify: `mimir/backfill.py`
- Modify: `mimir/dashboard.py`
- Modify: `mimir/history.py`
- Modify: `mimir/doctor/doctor_cli.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_collect.py`

**Interfaces:**
- Consumes: `config/watchlist.yaml` loaded by `load_yaml(path)`.
- Produces: `load_watchlist(config_dir: Path) -> dict[str, list[str]]`.
- Produces: `WatchlistConfigError(ValueError)`.
- Produces: `report_invalid_watchlist(exc: WatchlistConfigError) -> int`.

- [x] **Step 1: Write failing watchlist model tests**

Add these imports to `tests/test_config.py`:

```python
from mimir.config import WatchlistConfigError
```

Add these tests:

```python
def test_load_watchlist_rejects_scalar_market_value(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text("us: AAPL\nkr: []\n", encoding="utf-8")

    with pytest.raises(WatchlistConfigError) as exc_info:
        load_watchlist(tmp_path)

    message = str(exc_info.value)
    assert "watchlist.yaml" in message
    assert "us" in message


def test_load_watchlist_rejects_non_mapping_top_level(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text("- AAPL\n", encoding="utf-8")

    with pytest.raises(WatchlistConfigError) as exc_info:
        load_watchlist(tmp_path)

    assert "watchlist.yaml" in str(exc_info.value)


def test_load_watchlist_rejects_non_string_symbol(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text("us: [123]\nkr: []\n", encoding="utf-8")

    with pytest.raises(WatchlistConfigError) as exc_info:
        load_watchlist(tmp_path)

    assert "watchlist.yaml" in str(exc_info.value)


def test_load_watchlist_strips_symbols_and_rejects_blank_symbol(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text(
        "us:\n  - ' AAPL '\nkr:\n  - '   '\n",
        encoding="utf-8",
    )

    with pytest.raises(WatchlistConfigError) as exc_info:
        load_watchlist(tmp_path)

    assert "watchlist.yaml" in str(exc_info.value)
```

Update `test_load_watchlist_returns_lists` so it also proves whitespace is stripped:

```python
def test_load_watchlist_returns_lists(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text("us:\n  - ' AAPL '\nkr: []\n", encoding="utf-8")
    assert load_watchlist(tmp_path) == {"us": ["AAPL"], "kr": []}
```

- [x] **Step 2: Run RED watchlist tests**

Run:

```bash
uv run pytest tests/test_config.py::test_load_watchlist_rejects_scalar_market_value tests/test_config.py::test_load_watchlist_rejects_non_mapping_top_level tests/test_config.py::test_load_watchlist_rejects_non_string_symbol tests/test_config.py::test_load_watchlist_strips_symbols_and_rejects_blank_symbol -q
```

Expected: FAIL because `WatchlistConfigError` does not exist and scalar `us: AAPL` currently becomes `["A", "A", "P", "L"]`.

- [x] **Step 3: Implement pydantic-backed watchlist validation**

In `mimir/config.py`, import:

```python
from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError, field_validator
```

Add:

```python
class WatchlistConfigError(ValueError):
    """The configured watchlist.yaml could not be used."""


class _WatchlistConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    us: list[StrictStr] = Field(default_factory=list)
    kr: list[StrictStr] = Field(default_factory=list)

    @field_validator("us", "kr")
    @classmethod
    def _normalize_symbols(cls, value: list[str]) -> list[str]:
        symbols = [symbol.strip() for symbol in value]
        if any(not symbol for symbol in symbols):
            raise ValueError("watchlist symbols must not be blank")
        return symbols
```

Replace `load_watchlist()` with:

```python
def load_watchlist(config_dir: Path = DEFAULT_CONFIG_DIR) -> dict[str, list[str]]:
    path = config_dir / "watchlist.yaml"
    try:
        cfg = _WatchlistConfig.model_validate(load_yaml(path))
    except ValidationError as exc:
        raise WatchlistConfigError(f"{path}: {exc}") from exc
    return cfg.model_dump()
```

Add:

```python
def report_invalid_watchlist(exc: WatchlistConfigError) -> int:
    print(f"[mimir] invalid watchlist.yaml: {exc}", file=sys.stderr)
    return 1
```

- [x] **Step 4: Run GREEN watchlist tests**

Run:

```bash
uv run pytest tests/test_config.py -q
```

Expected: all config tests pass.

- [x] **Step 5: Add CLI friendly-error regression**

In `tests/test_collect.py`, add:

```python
def test_collect_cli_reports_invalid_watchlist_yaml(tmp_path, capsys):
    (tmp_path / "watchlist.yaml").write_text("us: AAPL\nkr: []\n", encoding="utf-8")

    code = collect_main(["--cadence", "daily", "--config-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 1
    assert "[mimir] invalid watchlist.yaml:" in captured.err
    assert str(tmp_path / "watchlist.yaml") in captured.err
```

Use the existing import style in that file for the CLI `main` function.

- [x] **Step 6: Run RED CLI regression**

Run:

```bash
uv run pytest tests/test_collect.py::test_collect_cli_reports_invalid_watchlist_yaml -q
```

Expected: FAIL because `collect` currently lets watchlist validation escape or does not report the watchlist-specific prefix.

- [x] **Step 7: Catch watchlist errors in CLI entry points**

Update each main function that calls `load_watchlist()` to import `WatchlistConfigError` and `report_invalid_watchlist`.

Use this pattern:

```python
try:
    watchlist = load_watchlist(config_dir)
except WatchlistConfigError as exc:
    return report_invalid_watchlist(exc)
```

Then pass `watchlist=watchlist` into the existing run function.

Apply it in:

- `mimir/collect.py`
- `mimir/analyze.py`
- `mimir/run.py`
- `mimir/backfill.py`
- `mimir/dashboard.py`
- `mimir/history.py` only when `--symbol` is absent
- `mimir/doctor/doctor_cli.py`

- [x] **Step 8: Run focused verification**

Run:

```bash
uv run pytest tests/test_config.py tests/test_collect.py tests/doctor/test_cli.py tests/test_run.py tests/test_backfill.py tests/test_dashboard_cli.py tests/test_history.py -q
uv run ruff check mimir/config.py mimir/collect.py mimir/analyze.py mimir/run.py mimir/backfill.py mimir/dashboard.py mimir/history.py mimir/doctor/doctor_cli.py tests/test_config.py tests/test_collect.py
uv run mypy mimir
```

Expected: all focused tests pass, ruff passes, mypy passes.

- [x] **Step 9: Commit**

Commit with:

```bash
git add mimir/config.py mimir/collect.py mimir/analyze.py mimir/run.py mimir/backfill.py mimir/dashboard.py mimir/history.py mimir/doctor/doctor_cli.py tests/test_config.py tests/test_collect.py
git commit -m "fix(config): validate watchlist schema"
```

---

### Task 2: LLM Headline Cap Bounds

**Files:**
- Modify: `mimir/sources/config.py`
- Modify: `tests/sources/test_config.py`

**Interfaces:**
- Consumes: top-level `llm_sentiment_max_headlines` from `sources.yaml`.
- Produces: pydantic validation that allows only integer values from `1` through `50`.
- Preserves: default `llm_sentiment_enabled: false` and default `llm_sentiment_max_headlines: 50`.

- [x] **Step 1: Write failing cap-bound tests**

Add to `tests/sources/test_config.py`:

```python
@pytest.mark.parametrize("bad_cap", [0, -1, 51])
def test_llm_sentiment_max_headlines_rejects_unsafe_bounds(bad_cap: int):
    with pytest.raises(ValidationError):
        parse_sources_config({"llm_sentiment_max_headlines": bad_cap})


@pytest.mark.parametrize("good_cap", [1, 50])
def test_llm_sentiment_max_headlines_accepts_safe_bounds(good_cap: int):
    cfg = parse_sources_config({"llm_sentiment_max_headlines": good_cap})

    assert cfg.llm_sentiment_max_headlines == good_cap


def test_sources_config_direct_model_rejects_unsafe_llm_cap():
    with pytest.raises(ValidationError):
        SourcesConfig(llm_sentiment_max_headlines=0)
```

- [x] **Step 2: Run RED cap tests**

Run:

```bash
uv run pytest tests/sources/test_config.py::test_llm_sentiment_max_headlines_rejects_unsafe_bounds tests/sources/test_config.py::test_sources_config_direct_model_rejects_unsafe_llm_cap -q
```

Expected: FAIL because nonpositive and overly large values are currently accepted.

- [x] **Step 3: Add pydantic bounds**

In `mimir/sources/config.py`, change both `SourcesConfig` and `_TopLevelSourcesConfig` fields to:

```python
llm_sentiment_max_headlines: int = Field(default=50, ge=1, le=50)
```

- [x] **Step 4: Run GREEN cap tests**

Run:

```bash
uv run pytest tests/sources/test_config.py -q
```

Expected: all source config tests pass.

- [x] **Step 5: Run focused verification**

Run:

```bash
uv run pytest tests/sources/test_config.py tests/analysis/test_builder.py tests/analysis/signals/test_llm_sentiment.py -q
uv run ruff check mimir/sources/config.py tests/sources/test_config.py
uv run mypy mimir
```

Expected: all focused tests pass, ruff passes, mypy passes.

- [x] **Step 6: Commit**

Commit with:

```bash
git add mimir/sources/config.py tests/sources/test_config.py
git commit -m "fix(config): bound LLM headline cap"
```

---

### Task 3: Config Guardrails Documentation

**Files:**
- Create: `docs/reference/config/watchlist.md`
- Create: `docs/decisions/tech-spec/config/CFG3_config_guardrails_tech_spec_2026_06_18.md`
- Create: `docs/_internal/skill-outputs/jira-ticket/CFG3-config-guardrails.md`
- Create: `docs/_internal/skill-outputs/commit/CFG3_COMMIT_20260618.md`
- Create: `docs/decisions/tech-spec/README.md`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/roadmap.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `tests/test_readme_docs.py`

**Interfaces:**
- Documents the as-built behavior from Tasks 1 and 2.
- Adds a documentation-navigation guard for README Further Reading links.
- Does not change runtime code.

- [x] **Step 1: Add README navigation guard tests**

In `tests/test_readme_docs.py`, add constants:

```python
README_REQUIRED_LINKS = (
    "docs/architecture/improvement-catalog.md",
    "docs/decisions/tech-spec/README.md",
    "docs/reference/config/watchlist.md",
)
```

Add:

```python
def test_readmes_link_current_decision_and_config_docs():
    for path in README_PATHS:
        text = path.read_text(encoding="utf-8")
        for link in README_REQUIRED_LINKS:
            assert link in text, f"{path} missing {link}"
```

- [x] **Step 2: Run RED README navigation test**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_readmes_link_current_decision_and_config_docs -q
```

Expected: FAIL because the README Further Reading tables do not yet link the improvement catalog, tech-spec index, or watchlist config reference.

- [x] **Step 3: Generate and update Korean-first docs**

Write all new generated documents in Korean. Keep code identifiers and file paths in English.

Required document content:

- `docs/reference/config/watchlist.md`: explain valid `watchlist.yaml`, default empty watchlist when file is absent, allowed `us`/`kr` keys, list-of-string requirement, whitespace stripping, blank rejection, and friendly CLI error prefix.
- `docs/reference/config/sources.md`: update `llm_sentiment_max_headlines` row to state valid range `1` through `50`; add invalid examples for `0` and `51`.
- `docs/decisions/tech-spec/config/CFG3_config_guardrails_tech_spec_2026_06_18.md`: explain watchlist corruption risk, LLM cap cost risk, schema design, CLI error handling, tests, rollout, security/cost impact.
- `docs/_internal/skill-outputs/jira-ticket/CFG3-config-guardrails.md`: problem/solution/acceptance tests/deploy verification.
- `docs/_internal/skill-outputs/commit/CFG3_COMMIT_20260618.md`: provenance and commit summary for the two code commits plus docs follow-up.
- `docs/decisions/tech-spec/README.md`: index current tech specs grouped by domain (`backfill`, `config`, `docs`, `doctor`, `sources`, `storage`) with one-line purpose.

Update existing docs:

- `docs/architecture/roadmap.md`: replace wording that says every spec lives under `docs/superpowers/specs/`; say newer decision specs may live under `docs/decisions/tech-spec/`.
- `docs/architecture/extensibility/README.md`: add optional `ticker_cik_map_path: company_tickers.json` to the SEC RSS YAML example.
- `docs/architecture/improvement-catalog.md`: add `CFG3-CONFIG-GUARDRAILS` to status, table, config section, sequence, and conclusion.
- `docs/IMPROVEMENTS.md`: add completed item for watchlist schema and LLM headline cap guardrails.
- README 3종 Further Reading: add improvement catalog, tech-spec index, and watchlist config reference.

- [x] **Step 4: Run docs verification**

Run:

```bash
uv run pytest --collect-only -q
uv run pytest tests/test_readme_docs.py -q
uv run ruff check .
uv run mypy mimir
git diff --check
```

Expected: all commands pass.

- [x] **Step 5: Commit**

Commit with:

```bash
git add README.md README.ko.md README.zh.md tests/test_readme_docs.py docs/reference/config/watchlist.md docs/reference/config/sources.md docs/decisions/tech-spec/config/CFG3_config_guardrails_tech_spec_2026_06_18.md docs/_internal/skill-outputs/jira-ticket/CFG3-config-guardrails.md docs/_internal/skill-outputs/commit/CFG3_COMMIT_20260618.md docs/decisions/tech-spec/README.md docs/architecture/roadmap.md docs/architecture/extensibility/README.md docs/architecture/improvement-catalog.md docs/IMPROVEMENTS.md docs/superpowers/plans/2026-06-18-config-guardrails.md
git commit -m "docs(config): document config guardrails"
```
