# Backfill Manifest Recording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `mimir.backfill`이 성공과 실패 실행을 기존 manifest 형식으로 기록하게 만든다.

**Architecture:** `run_backfill()`은 기존 `JsonlStore` 옆에 `Manifest`를 만들고, 단일 source 실행 결과를 `SourceResult` 하나로 기록한다. 성공은 기존 반환값을 유지하고, 실패는 manifest를 남긴 뒤 예외를 다시 던진다.

**Tech Stack:** Python 3.14, pydantic manifest models, pytest, responses, ruff, mypy.

---

### Task 1: Backfill Manifest Accounting

**Files:**
- Modify: `mimir/backfill.py`
- Modify: `tests/test_backfill.py`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Create: `docs/superpowers/specs/2026-06-16-backfill-manifest-design.md`
- Create: `docs/superpowers/plans/2026-06-16-backfill-manifest.md`

- [x] **Step 1: Write failing success manifest test**

Extend `tests/test_backfill.py::test_backfill_stooq_loads_history`:

```python
from mimir.manifest.manifest import Manifest

latest = Manifest(root=tmp_path / "data").latest_run()
assert latest is not None
assert latest.cadence == "daily"
result = latest.results[0]
assert result.source == "stooq"
assert result.ok is True
assert result.fetched == 2
assert result.stored == 2
assert result.invalid == 0
```

Run:

```bash
uv run pytest tests/test_backfill.py::test_backfill_stooq_loads_history -q
```

Expected: FAIL because `run_backfill()` does not write a manifest yet.

- [x] **Step 2: Write failing invalid-count manifest test**

Add this test to `tests/test_backfill.py`:

```python
@responses.activate
def test_backfill_records_invalid_count_in_manifest(tmp_path: Path, monkeypatch):
    from mimir import backfill as backfill_mod
    from mimir.core.errors import NormalizationError
    from mimir.manifest.manifest import Manifest

    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)
    real_normalize = backfill_mod.normalize
    calls = {"n": 0}

    def flaky_normalize(raw, meta, *, captured_at):
        calls["n"] += 1
        if calls["n"] == 1:
            raise NormalizationError("bad record")
        return real_normalize(raw, meta, captured_at=captured_at)

    monkeypatch.setattr(backfill_mod, "normalize", flaky_normalize)

    appended = run_backfill(
        source_id="stooq",
        since=date(2018, 1, 1),
        env={"STOOQ_API_KEY": "test-key"},
        watchlist={"us": ["AAPL"], "kr": []},
        data_root=tmp_path / "data",
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert appended == 1
    latest = Manifest(root=tmp_path / "data").latest_run()
    assert latest is not None
    result = latest.results[0]
    assert result.fetched == 2
    assert result.stored == 1
    assert result.invalid == 1
```

Run:

```bash
uv run pytest tests/test_backfill.py::test_backfill_records_invalid_count_in_manifest -q
```

Expected: FAIL because no manifest exists yet.

- [x] **Step 3: Write failing failure-manifest test**

Add a fake source test:

```python
def test_backfill_records_failure_manifest_before_reraising(tmp_path: Path, monkeypatch):
    from mimir import backfill as backfill_mod
    from mimir.core.source import Cadence, Dataset, FetchContext, LegalStatus, Market, RateLimit, SourceMeta
    from mimir.manifest.manifest import Manifest

    class FailSource:
        meta = SourceMeta(
            id="fail",
            market=Market.US,
            dataset=Dataset.PRICES,
            cadence=Cadence.DAILY,
            legal_status=LegalStatus.OFFICIAL,
            rate_limit=RateLimit(),
        )

        def fetch(self, ctx: FetchContext):
            raise RuntimeError("upstream down")

    monkeypatch.setattr(backfill_mod, "build_sources", lambda settings, config: [FailSource()])

    with pytest.raises(RuntimeError, match="upstream down"):
        run_backfill(
            source_id="fail",
            since=date(2018, 1, 1),
            env={},
            watchlist={"us": ["AAPL"], "kr": []},
            data_root=tmp_path / "data",
            now=datetime(2026, 5, 31, tzinfo=UTC),
        )

    latest = Manifest(root=tmp_path / "data").latest_run()
    assert latest is not None
    result = latest.results[0]
    assert result.source == "fail"
    assert result.ok is False
    assert "upstream down" in (result.error or "")
```

Run:

```bash
uv run pytest tests/test_backfill.py::test_backfill_records_failure_manifest_before_reraising -q
```

Expected: FAIL because failure is not logged before re-raise.

- [x] **Step 3a: Write failing original-error preservation test**

Add a test that monkeypatches `Manifest.write()` to raise and monkeypatches `normalize()` to raise `ValueError("normalize exploded")`.

Run:

```bash
uv run pytest tests/test_backfill.py::test_backfill_preserves_original_error_when_failure_manifest_write_fails -q
```

Expected before the fix: FAIL because `manifest write failed` masks `normalize exploded`.

- [x] **Step 4: Implement manifest writing in `run_backfill()`**

Update `mimir/backfill.py`:

```python
from mimir.manifest.manifest import Manifest, SourceResult
```

Inside `run_backfill()`:

```python
store = JsonlStore(root=data_root)
manifest = Manifest(root=data_root)
ctx = FetchContext(watchlist=watchlist, now=now, backfill_since=since)

records: list[Record] = []
fetched = 0
invalid = 0
try:
    for raw in source.fetch(ctx):
        fetched += 1
        try:
            records.append(normalize(raw, source.meta, captured_at=now))
        except NormalizationError:
            invalid += 1
    if invalid:
        logger.warning("backfill %s: skipped %d invalid record(s)", source_id, invalid)
    stored = store.append(records)
except Exception as exc:
    manifest.write(
        now=now,
        cadence=source.meta.cadence,
        results=[
            SourceResult(
                source=source.meta.id,
                ok=False,
                fetched=fetched,
                invalid=invalid,
                error=str(exc),
            )
        ],
    )
    raise

manifest.write(
    now=now,
    cadence=source.meta.cadence,
    results=[
        SourceResult(
            source=source.meta.id,
            ok=True,
            fetched=fetched,
            stored=stored,
            invalid=invalid,
        )
    ],
)
return stored
```

- [x] **Step 5: Run focused tests**

Run:

```bash
uv run pytest tests/test_backfill.py tests/manifest/test_manifest.py -q
```

Expected: PASS.

- [x] **Step 6: Update docs**

Update:

- `docs/IMPROVEMENTS.md`: mark backfill isolation/manifest fully complete.
- `docs/architecture/improvement-catalog.md`: mention backfill now records manifest success/failure.
- `README.md`, `README.ko.md`, `README.zh.md`: explain that `backfill` also writes manifest entries; update test count after verification.
- `docs/superpowers/specs/2026-06-16-backfill-manifest-design.md`: mark implemented with verification count.

- [x] **Step 7: Run verification**

Run:

```bash
uv run ruff check .
uv run mypy mimir
git diff --check
uv run coverage run -m pytest
uv run coverage report --fail-under=80
```

Expected: all pass.

- [x] **Step 8: Mark plan complete and commit**

Update this plan's checkboxes to `[x]`, set the spec status to implemented, then commit:

```bash
git add mimir/backfill.py tests/test_backfill.py docs/IMPROVEMENTS.md docs/architecture/improvement-catalog.md README.md README.ko.md README.zh.md docs/superpowers/specs/2026-06-16-backfill-manifest-design.md docs/superpowers/plans/2026-06-16-backfill-manifest.md
git commit -m "feat: record backfill manifests"
```
