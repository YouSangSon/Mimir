# Runtime Config & Documentation Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 설정을 하나의 typed runtime boundary로 통합하고, SEC ticker CIK map refresh의 orphaned-cache 버그와 문서 drift를 고쳐 Mimir가 더 확장 가능하고 운영 문서가 현재 구현과 일치하게 만든다.

**Architecture:** `sources.yaml`의 top-level runtime 설정(`gray_enabled`, `disabled_ids`, `lang`)을 raw dict가 아니라 검증된 모델에서 읽도록 한다. SEC refresh는 off-by-default best-effort 계약을 지키며, 304가 와도 로컬 cache file이 없으면 collection을 깨지 않는다. 구현된 기능 상태는 reference docs, extensibility guide, tech-spec index, README navigation guard가 서로 맞도록 고정한다.

**Tech Stack:** Python 3.14, pydantic v2, PyYAML, requests, pytest, ruff, mypy.

## Global Constraints

- Do not add default network calls. SEC ticker CIK map refresh remains off by default.
- Do not change JSONL storage layout, `schema_version`, partition paths, or existing `idempotency_key` formats.
- Do not change source plugin entry point behavior, plugin ordering, or `SourceSpec` public constructor fields.
- Do not make `mimir doctor` a scheduled pipeline hard gate.
- Preserve existing CLI exit-code contracts and friendly config error prefixes.
- Preserve `llm_sentiment_enabled: false` and `llm_sentiment_max_headlines` range `1` through `50`.
- Documentation updates are Korean-first for project docs under `docs/`, while code identifiers and file paths stay in English.
- Follow TDD for code behavior changes: add the failing regression first, run it to verify RED, then implement.

---

### Task 1: Typed Runtime Sources Config Boundary

**Files:**
- Modify: `mimir/sources/config.py`
- Modify: `mimir/config.py`
- Modify: `mimir/collect.py`
- Modify: `mimir/run.py`
- Modify: `mimir/deliver.py`
- Modify: `mimir/dashboard.py`
- Modify: `tests/sources/test_config.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_collect.py`
- Modify: `tests/test_run.py`

**Interfaces:**
- Produces: `RuntimeSourcesConfig(BaseModel)` with fields:
  - `source_config: SourcesConfig`
  - `gray_enabled: bool`
  - `disabled_ids: tuple[str, ...]`
  - `lang: str`
- Produces: `parse_runtime_sources_config(raw: dict[str, Any]) -> RuntimeSourcesConfig`
- Preserves: `parse_sources_config(raw) -> SourcesConfig`
- Changes: `load_validated_sources_config(config_dir)` returns `(raw, runtime_config)` instead of `(raw, SourcesConfig)`.

- [ ] **Step 1: Write failing parser tests**

Add imports in `tests/sources/test_config.py`:

```python
from mimir.report.i18n import DEFAULT_LANG
from mimir.sources.config import RuntimeSourcesConfig, parse_runtime_sources_config
```

Add tests near the existing top-level config tests:

```python
def test_parse_runtime_sources_config_keeps_top_level_runtime_fields():
    cfg = parse_runtime_sources_config(
        {
            "gray_enabled": False,
            "disabled_ids": ["rss", "sec_edgar"],
            "lang": "ko",
            "sources": {"fred": {"series": ["DGS10"]}},
        }
    )

    assert cfg.gray_enabled is False
    assert cfg.disabled_ids == ("rss", "sec_edgar")
    assert cfg.lang == "ko"
    assert cfg.source_config.fred_series == ["DGS10"]


def test_parse_runtime_sources_config_normalizes_unknown_lang_to_default():
    cfg = parse_runtime_sources_config({"lang": 'en" onmouseover="alert(1)'})

    assert cfg.lang == DEFAULT_LANG


def test_parse_sources_config_still_returns_source_only_model():
    cfg = parse_sources_config({"gray_enabled": False, "disabled_ids": ["rss"], "lang": "ko"})

    assert isinstance(cfg, SourcesConfig)
    assert not isinstance(cfg, RuntimeSourcesConfig)
```

- [ ] **Step 2: Run RED parser tests**

Run:

```bash
uv run pytest tests/sources/test_config.py::test_parse_runtime_sources_config_keeps_top_level_runtime_fields tests/sources/test_config.py::test_parse_runtime_sources_config_normalizes_unknown_lang_to_default tests/sources/test_config.py::test_parse_sources_config_still_returns_source_only_model -q
```

Expected: FAIL because `RuntimeSourcesConfig` and `parse_runtime_sources_config` do not exist.

- [ ] **Step 3: Implement runtime config model**

In `mimir/sources/config.py`, import:

```python
from mimir.report.i18n import DEFAULT_LANG, normalize_lang
```

Add below `_TopLevelSourcesConfig`:

```python
class RuntimeSourcesConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_config: SourcesConfig = Field(default_factory=SourcesConfig)
    gray_enabled: bool = True
    disabled_ids: tuple[str, ...] = ()
    lang: str = DEFAULT_LANG
```

Refactor the parser body into a helper:

```python
def _source_config_from_top_level(top_level: _TopLevelSourcesConfig) -> SourcesConfig:
    block = top_level.sources or _SourcesBlock()
    news_block = top_level.analysis.news if top_level.analysis and top_level.analysis.news else None
    return SourcesConfig(
        ...
    )
```

Keep the existing `SourcesConfig(...)` field assignments exactly as today, moved into that helper.

Replace `parse_sources_config()` with:

```python
def parse_sources_config(raw: dict[str, Any]) -> SourcesConfig:
    top_level = _TopLevelSourcesConfig.model_validate(raw)
    return _source_config_from_top_level(top_level)
```

Add:

```python
def parse_runtime_sources_config(raw: dict[str, Any]) -> RuntimeSourcesConfig:
    top_level = _TopLevelSourcesConfig.model_validate(raw)
    return RuntimeSourcesConfig(
        source_config=_source_config_from_top_level(top_level),
        gray_enabled=top_level.gray_enabled,
        disabled_ids=tuple(top_level.disabled_ids or ()),
        lang=normalize_lang(top_level.lang),
    )
```

- [ ] **Step 4: Run GREEN parser tests**

Run:

```bash
uv run pytest tests/sources/test_config.py::test_parse_runtime_sources_config_keeps_top_level_runtime_fields tests/sources/test_config.py::test_parse_runtime_sources_config_normalizes_unknown_lang_to_default tests/sources/test_config.py::test_parse_sources_config_still_returns_source_only_model -q
```

Expected: PASS.

- [ ] **Step 5: Write failing loader and caller tests**

Update `tests/test_config.py` import list:

```python
from mimir.sources.config import RuntimeSourcesConfig
```

Add:

```python
def test_load_validated_sources_config_returns_runtime_config(tmp_path: Path):
    (tmp_path / "sources.yaml").write_text(
        "gray_enabled: false\ndisabled_ids: [rss]\nlang: ko\n",
        encoding="utf-8",
    )

    raw, runtime = load_validated_sources_config(tmp_path)

    assert raw["gray_enabled"] is False
    assert isinstance(runtime, RuntimeSourcesConfig)
    assert runtime.gray_enabled is False
    assert runtime.disabled_ids == ("rss",)
    assert runtime.lang == "ko"
```

In `tests/test_collect.py`, add:

```python
def test_run_collect_uses_typed_runtime_config_for_registry_and_lang(tmp_path: Path):
    summary = run_collect(
        cadence="daily",
        env={},
        watchlist={"us": [], "kr": []},
        data_root=tmp_path / "data",
        status_path=tmp_path / "reports/status.html",
        sources_config={"gray_enabled": False, "disabled_ids": ["sec_edgar", "rss"], "lang": "ko"},
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )

    html = (tmp_path / "reports/status.html").read_text(encoding="utf-8")
    assert summary.had_failures is False
    assert 'lang="ko"' in html
    assert "source(s)" not in html
```

In `tests/test_run.py`, add:

```python
def test_run_pipeline_uses_typed_runtime_config_for_lang(tmp_path: Path):
    result = run_pipeline(
        cadence="daily",
        env={},
        watchlist={"us": [], "kr": []},
        data_root=tmp_path / "data",
        reports_root=tmp_path / "reports",
        sources_config={"disabled_ids": ["sec_edgar", "rss"], "lang": "ko"},
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert result["collect_failures"] is False
    assert 'lang="ko"' in (tmp_path / "reports/2026/05/31.html").read_text(encoding="utf-8")
```

- [ ] **Step 6: Run RED loader and caller tests**

Run:

```bash
uv run pytest tests/test_config.py::test_load_validated_sources_config_returns_runtime_config tests/test_collect.py::test_run_collect_uses_typed_runtime_config_for_registry_and_lang tests/test_run.py::test_run_pipeline_uses_typed_runtime_config_for_lang -q
```

Expected: FAIL because `load_validated_sources_config()` still returns a raw `SourcesConfig`, and callers still read `gray_enabled`, `disabled_ids`, and `lang` from raw dicts.

- [ ] **Step 7: Wire runtime config through CLI/runtime callers**

In `mimir/config.py`, import `RuntimeSourcesConfig` and `parse_runtime_sources_config`, then change:

```python
def load_validated_sources_config(...) -> tuple[dict[str, Any], RuntimeSourcesConfig]:
    raw = _resolve_sources_config_paths(load_sources_config(config_dir), config_dir)
    return raw, parse_runtime_sources_config(raw)
```

In `mimir/collect.py`:

- Import `RuntimeSourcesConfig`.
- Change `_build_source_registry(settings, cfg: dict[str, Any])` to `_build_source_registry(settings, cfg: RuntimeSourcesConfig)`.
- Build sources with `build_sources(settings, cfg.source_config)`.
- Construct `Registry(..., gray_enabled=cfg.gray_enabled, disabled_ids=set(cfg.disabled_ids))`.
- In `run_collect()`, convert raw `sources_config` with `parse_runtime_sources_config(sources_config or {})` once, use `runtime.lang`, and pass the runtime config into `_build_source_registry()`.
- In `main()`, unpack `_, runtime_config = load_validated_sources_config(config_dir)` and pass `sources_config=runtime_config`.
- Type the public `run_collect(..., sources_config: dict[str, Any] | RuntimeSourcesConfig | None = None)`.

In `mimir/run.py`:

- Import `RuntimeSourcesConfig` and `parse_runtime_sources_config`.
- In `run_pipeline()`, convert raw `sources_config` with `parse_runtime_sources_config(sources_config or {})` once.
- Use `runtime.lang`, pass `runtime` into `run_collect()`, pass `runtime.source_config` into `run_analyze()`.
- In `main()`, unpack `_, runtime_config = load_validated_sources_config(config_dir)` and pass that into `run_pipeline()`.
- Type `sources_config: dict[str, Any] | RuntimeSourcesConfig | None = None`.

In `mimir/deliver.py`:

- Unpack `_, runtime_config = load_validated_sources_config(...)`.
- Use `runtime_config.lang`.

In `mimir/dashboard.py`:

- Unpack `_, runtime_config = load_validated_sources_config(...)`.
- Use `args.lang or runtime_config.lang`.

In `mimir/analyze.py`, `mimir/backfill.py`, and `mimir/doctor/doctor_cli.py`:

- Adjust unpacking to `_, runtime_config = load_validated_sources_config(...)`.
- Pass `runtime_config.source_config` where a `SourcesConfig` is needed, or ignore the value when validation is enough.

- [ ] **Step 8: Run Task 1 verification**

Run:

```bash
uv run pytest tests/sources/test_config.py tests/test_config.py tests/test_collect.py tests/test_run.py tests/test_deliver.py tests/test_dashboard_cli.py tests/test_analyze.py tests/test_backfill.py tests/doctor/test_cli.py -q
uv run ruff check mimir/sources/config.py mimir/config.py mimir/collect.py mimir/run.py mimir/deliver.py mimir/dashboard.py mimir/analyze.py mimir/backfill.py mimir/doctor/doctor_cli.py tests/sources/test_config.py tests/test_config.py tests/test_collect.py tests/test_run.py
uv run mypy mimir
```

Expected: all focused tests pass, ruff passes, mypy passes.

- [ ] **Step 9: Commit**

Commit with:

```bash
git add mimir/sources/config.py mimir/config.py mimir/collect.py mimir/run.py mimir/deliver.py mimir/dashboard.py mimir/analyze.py mimir/backfill.py mimir/doctor/doctor_cli.py tests/sources/test_config.py tests/test_config.py tests/test_collect.py tests/test_run.py
git commit -m "refactor(config): add typed runtime sources config"
```

---

### Task 2: SEC Refresh Orphaned 304 Resilience

**Files:**
- Modify: `mimir/sources/sec_ticker_cik_refresh.py`
- Modify: `tests/sources/test_sec_ticker_cik_refresh.py`

**Interfaces:**
- Preserves: `refresh_sec_ticker_cik_map(...) -> None`
- Preserves: disabled refresh path makes zero network calls.
- Fixes: `304 Not Modified` with an orphaned `.etag` but no local map file must not raise `FileNotFoundError`.

- [ ] **Step 1: Write failing orphaned-ETag regression**

Add to `tests/sources/test_sec_ticker_cik_refresh.py`:

```python
def test_304_without_existing_cache_file_does_not_crash(tmp_path):
    path = tmp_path / "company_tickers.json"
    (tmp_path / "company_tickers.json.etag").write_text('"abc"', encoding="utf-8")
    rec = _Recorder(resp=_FakeResp(304))

    refresh_sec_ticker_cik_map(path, _enabled(), user_agent="Svc me@x.com", http_get_fn=rec)

    assert rec.calls[0][1]["If-None-Match"] == '"abc"'
    assert not path.exists()
```

- [ ] **Step 2: Run RED refresh regression**

Run:

```bash
uv run pytest tests/sources/test_sec_ticker_cik_refresh.py::test_304_without_existing_cache_file_does_not_crash -q
```

Expected: FAIL with `FileNotFoundError` from `os.utime(path)`.

- [ ] **Step 3: Fix 304 orphaned-cache handling**

Change the `304` branch in `mimir/sources/sec_ticker_cik_refresh.py` to:

```python
if resp.status_code == 304:
    if path.exists():
        os.utime(path)
    else:
        logger.warning(
            "SEC ticker CIK map refresh returned 304 but %s is missing; keeping no cache",
            path,
        )
    return
```

This keeps the best-effort contract: an inconsistent local sidecar cannot break collection, and a real cached file still gets its TTL reset.

- [ ] **Step 4: Run GREEN refresh tests**

Run:

```bash
uv run pytest tests/sources/test_sec_ticker_cik_refresh.py -q
uv run ruff check mimir/sources/sec_ticker_cik_refresh.py tests/sources/test_sec_ticker_cik_refresh.py
uv run mypy mimir
```

Expected: all pass.

- [ ] **Step 5: Commit**

Commit with:

```bash
git add mimir/sources/sec_ticker_cik_refresh.py tests/sources/test_sec_ticker_cik_refresh.py
git commit -m "fix(sources): tolerate orphaned SEC map 304"
```

---

### Task 3: Documentation Truth Guards

**Files:**
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/decisions/tech-spec/README.md`
- Modify: `docs/reference/analysis/scoring.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `tests/test_readme_docs.py`
- Create: `docs/reference/cli.md`

**Interfaces:**
- Documents current as-built behavior after Tasks 1 and 2.
- Adds guard coverage so implemented SEC refresh and current reference pages stay discoverable.
- Does not change runtime code.

- [ ] **Step 1: Write failing docs guard tests**

In `tests/test_readme_docs.py`, add to `README_REQUIRED_LINKS`:

```python
"docs/reference/cli.md",
```

Add constants:

```python
REFERENCE_DOCS = tuple(sorted(Path("docs/reference").rglob("*.md")))
SEC_REFRESH_DESIGN_SPEC = Path(
    "docs/superpowers/specs/2026-06-19-sec-ticker-cik-map-cache-design.md"
)
SEC_REFRESH_DOCS = (
    Path("docs/reference/config/sources.md"),
    Path("docs/architecture/extensibility/README.md"),
    SEC_REFRESH_DESIGN_SPEC,
)
SEC_REFRESH_STALE_GUARD_DOCS = tuple(sorted(Path("docs").rglob("*.md")))
```

Add tests:

```python
def test_readme_links_all_reference_docs():
    required = tuple(str(path) for path in REFERENCE_DOCS)
    for path in README_FILES:
        text = path.read_text(encoding="utf-8")
        for link in required:
            assert link in text, f"{path} missing {link}"


def test_sec_ticker_cik_refresh_docs_match_implemented_state():
    for path in SEC_REFRESH_DOCS:
        text = path.read_text(encoding="utf-8")
        assert "ticker_cik_map_refresh" in text, f"{path} missing refresh config"
        assert "enabled" in text, f"{path} missing enabled field"
        assert "max_age_hours" in text, f"{path} missing TTL field"

    stale_phrases = (
        # Keep the final literal list in tests/test_readme_docs.py only, so docs
        # can be scanned without matching their own examples.
    )
    for path in SEC_REFRESH_STALE_GUARD_DOCS:
        text = path.read_text(encoding="utf-8")
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still says: {phrase}"


def test_scoring_reference_documents_news_volume_confidence():
    text = Path("docs/reference/analysis/scoring.md").read_text(encoding="utf-8")

    assert "| `news_volume` | 항상 NEUTRAL | 0.5 | 0.5 |" in text
```

- [ ] **Step 2: Run RED docs tests**

Run:

```bash
uv run pytest tests/test_readme_docs.py::test_readme_links_all_reference_docs tests/test_readme_docs.py::test_sec_ticker_cik_refresh_docs_match_implemented_state tests/test_readme_docs.py::test_scoring_reference_documents_news_volume_confidence -q
```

Expected: FAIL because `docs/reference/cli.md` does not exist or is not linked, SEC refresh docs still describe deferred behavior, and `news_volume` confidence is documented as `—`.

- [ ] **Step 3: Create CLI reference**

Create `docs/reference/cli.md` in Korean. Include:

- Command matrix for `mimir run`, `collect`, `backfill`, `analyze`, `deliver`, `history`, `doctor`, `evaluate`, `dashboard`.
- Which commands read `sources.yaml`, `watchlist.yaml`, data, reports.
- Friendly config error prefixes:
  - `[mimir] invalid sources.yaml:`
  - `[mimir] invalid watchlist.yaml:`
- `evaluate` explicitly does not read `--config-dir`.
- `doctor --strict` is an operator choice, not a scheduled pipeline hard gate.
- Unified `mimir <command>` and dotted aliases remain available.

- [ ] **Step 4: Update SEC refresh docs**

In `docs/reference/config/sources.md`:

- Add `sec.ticker_cik_map_refresh` to the RSS field table.
- Add fields `enabled`, `url`, `max_age_hours`.
- State default is disabled, so the standard path makes zero SEC mapping download requests.
- State refresh runs before source build, not inside RSS resolver.
- State TTL gate, ETag conditional GET, `304` TTL reset when cache file exists, orphaned `304` warning/no crash, temp-file validation through canonical loader, atomic adoption, and fallback on failure.
- Remove stale wording that says Mimir never downloads or judges staleness.

In `docs/architecture/extensibility/README.md`:

- Update final date to `2026-06-23`.
- Add `ticker_cik_map_refresh` to the YAML example.
- Replace deferred SEC live cache debt with implemented off-by-default cache behavior.
- Keep generic provider RSS live discovery as remaining debt.

In `docs/decisions/tech-spec/README.md`:

- Add source-row links for:
  - `docs/superpowers/specs/2026-06-19-sec-ticker-cik-map-cache-design.md`
  - `docs/superpowers/specs/2026-06-19-captured-date-persistent-index-design.md`
- Label them as design specs when no `docs/decisions/tech-spec/` file exists.

- [ ] **Step 5: Update scoring docs and README links**

In `docs/reference/analysis/scoring.md`, change the `news_volume` row from default confidence `—` to `0.5`.

In `README.md`, `README.ko.md`, and `README.zh.md`, add `docs/reference/cli.md` to Further Reading.

- [ ] **Step 6: Run docs verification**

Run:

```bash
uv run pytest tests/test_readme_docs.py -q
uv run pytest --collect-only -q
uv run ruff check tests/test_readme_docs.py
git diff --check
```

Expected: all pass.

- [ ] **Step 7: Commit**

Commit with:

```bash
git add README.md README.ko.md README.zh.md docs/reference/cli.md docs/reference/config/sources.md docs/architecture/extensibility/README.md docs/decisions/tech-spec/README.md docs/reference/analysis/scoring.md tests/test_readme_docs.py docs/superpowers/plans/2026-06-23-runtime-config-doc-truth.md
git commit -m "docs(ops): align source refresh and CLI references"
```

---

### Task 4: Final Verification And Branch Review

**Files:**
- No required source edits.
- May create review artifacts under `.git/sdd/`.

**Interfaces:**
- Verifies all previous tasks as one branch.
- Produces final status for the user.

- [ ] **Step 1: Run full verification**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy mimir
git diff --check
git status --short --branch
```

Expected: tests, ruff, mypy, and diff check pass. `git status` may still show existing untracked `uv.lock`; do not delete it unless separately scoped.

- [ ] **Step 2: Run final whole-branch review**

Use `superpowers:requesting-code-review` through the current multi-agent reviewer role. Review the merge-base range:

```bash
MERGE_BASE=$(git merge-base origin/main HEAD)
/Users/yousang/.codex/superpowers/skills/subagent-driven-development/scripts/review-package "$MERGE_BASE" HEAD
```

Pass the generated diff package path to the reviewer.

- [ ] **Step 3: Address review findings**

If the final reviewer reports Critical or Important findings, dispatch one fix subagent with the complete findings list, re-run covering tests, and re-review.

- [ ] **Step 4: Final report**

Report:

- What changed.
- Commits created.
- Verification commands and results.
- Remaining broader candidates not implemented yet:
  - analysis signal plugin seam
  - storage schema migration/version dispatch
  - streaming/batched backfill writes
  - plugin trust/compatibility hardening
  - CI release guardrails
