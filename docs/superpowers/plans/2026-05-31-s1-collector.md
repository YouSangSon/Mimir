# S1 Collector — Implementation Plan (Increment 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a free, legal, GitHub-Actions-driven data-collection layer that fetches KR+US market data through source adapters and stores it as date-partitioned JSONL in the repo (git-as-DB).

**Architecture:** Adapter pattern. Each source implements a common `Source` protocol exposing `meta` (id, market, dataset, cadence, legal_status, rate_limit) and `fetch(ctx) -> Iterable[RawRecord]`. An orchestrator selects sources due for a cadence, throttles them, normalizes raw records into a validated `Record` envelope, and appends them idempotently to `data/<dataset>/YYYY/MM/DD.jsonl`. A manifest logs every run; a minimal status HTML + optional Telegram ping make the pipeline visible.

**Tech Stack:** Python 3.12, `requests`, `pydantic` v2, `pyyaml`, `pytest` + `responses` (HTTP mocking), `ruff`, `mypy`, GitHub Actions.

**Increment scope:** Framework + storage + 3 adapters (Stooq US prices, SEC EDGAR US filings, DART KR filings) + orchestrator + manifest + settings + minimal visibility + daily workflow + backfill entrypoint. **Deferred to Increment 2** (a follow-up plan): pykrx (KR prices, GRAY), FRED + ECOS (macro), RSS + Naver (news), hourly/weekly/monthly workflows.

**Satisfies acceptance criteria** 1, 2, 3, 4, 5, 6, 7 and the GRAY-policy *mechanism* of 8 (pykrx itself lands in Increment 2).

---

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, deps, ruff/mypy/pytest config |
| `mimir/core/source.py` | Enums, `RateLimit`, `SourceMeta`, `FetchContext`, `RawRecord`, `Source` protocol |
| `mimir/core/errors.py` | Domain exceptions |
| `mimir/core/throttle.py` | Per-source rate limiting (injectable clock/sleep) |
| `mimir/core/normalize.py` | `RawRecord` + `SourceMeta` → validated `Record` |
| `mimir/core/registry.py` | Source registration, `due(cadence)`, GRAY/disabled policy |
| `mimir/core/orchestrator.py` | Run a tick: select → throttle → fetch → normalize → store → manifest, with source isolation |
| `mimir/storage/schema.py` | `Record` envelope (pydantic) |
| `mimir/storage/paths.py` | Date-partition path rule |
| `mimir/storage/jsonl_store.py` | Idempotent append + read |
| `mimir/sources/base.py` | `http_get` (UA/timeout/retry), `BaseSource` (throttled `get`) |
| `mimir/sources/stooq.py` | US EOD prices |
| `mimir/sources/sec_edgar.py` | US filings |
| `mimir/sources/dart.py` | KR filings |
| `mimir/manifest/manifest.py` | Run log records |
| `mimir/settings.py` | Env/secret loading + validation |
| `mimir/report/status_html.py` | Minimal data-status HTML |
| `mimir/report/telegram.py` | Optional "collection done" ping |
| `mimir/collect.py` | CLI entrypoint `python -m mimir.collect --cadence daily` |
| `mimir/backfill.py` | CLI entrypoint `python -m mimir.backfill --source stooq --since 2018-01-01` |
| `config/watchlist.yaml` | Tracked tickers (US/KR) |
| `config/sources.yaml` | Source on/off + GRAY policy |
| `.github/workflows/collect-daily.yml` | Daily cron + commit-back |

---

## Task 0: Project scaffolding

**Files:**
- Create: `pyproject.toml`, `mimir/__init__.py`, `mimir/core/__init__.py`, `mimir/storage/__init__.py`, `mimir/sources/__init__.py`, `mimir/manifest/__init__.py`, `mimir/report/__init__.py`, `tests/__init__.py`, `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "mimir"
version = "0.1.0"
description = "Free, legal investment-insight data collector"
requires-python = ">=3.12"
dependencies = [
    "requests>=2.32",
    "pydantic>=2.7",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "responses>=0.25",
    "ruff>=0.5",
    "mypy>=1.10",
    "coverage>=7.5",
    "types-requests",
    "types-PyYAML",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["mimir*"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
markers = ["integration: hits real network; deselected by default"]
addopts = "-m 'not integration'"
```

- [ ] **Step 2: Create empty `__init__.py` files** (all packages listed above) and `.gitignore`

`.gitignore`:
```
.env
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
*.egg-info/
```

- [ ] **Step 3: Create the directory tree** for `mimir/{core,storage,sources,manifest,report}`, `tests`, `config`, `data`, `reports`, `.github/workflows`.

- [ ] **Step 4: Install dev deps**

Run: `python -m pip install -e ".[dev]"`
Expected: installs without error.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml mimir/ tests/ .gitignore
git commit -m "chore: scaffold mimir package and tooling"
```

---

## Task 1: Core domain types

**Files:**
- Create: `mimir/core/source.py`
- Test: `tests/core/test_source.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_source.py
from datetime import UTC, datetime

from mimir.core.source import (
    Cadence, Dataset, FetchContext, LegalStatus, Market, RateLimit, RawRecord, Source, SourceMeta,
)


def test_source_meta_round_trips():
    meta = SourceMeta(
        id="stooq", market=Market.US, dataset=Dataset.PRICES, cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL, rate_limit=RateLimit(max_per_second=1.0),
    )
    assert meta.id == "stooq"
    assert meta.legal_status is LegalStatus.OFFICIAL
    assert meta.requires_secret is None


def test_raw_record_requires_idempotency_key():
    rec = RawRecord(symbol="AAPL", ts=datetime(2026, 5, 29, tzinfo=UTC),
                    idempotency_key="stooq:AAPL:2026-05-29", payload={"close": 1.0})
    assert rec.idempotency_key == "stooq:AAPL:2026-05-29"


def test_source_protocol_is_runtime_checkable():
    class Dummy:
        meta = SourceMeta(
            id="d", market=Market.US, dataset=Dataset.PRICES, cadence=Cadence.DAILY,
            legal_status=LegalStatus.OFFICIAL, rate_limit=RateLimit(),
        )
        def fetch(self, ctx):  # noqa: ANN001
            return []
    assert isinstance(Dummy(), Source)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_source.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mimir.core.source'`

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/core/source.py
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Iterable, Protocol, runtime_checkable

from pydantic import BaseModel


class Cadence(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class LegalStatus(str, Enum):
    OFFICIAL = "official"
    GRAY = "gray"


class Market(str, Enum):
    US = "US"
    KR = "KR"
    GLOBAL = "GLOBAL"


class Dataset(str, Enum):
    PRICES = "prices"
    FILINGS = "filings"
    MACRO = "macro"
    NEWS = "news"


class RateLimit(BaseModel):
    # None means unknown / unpublished -> caller throttles conservatively.
    max_per_second: float | None = None


class SourceMeta(BaseModel):
    id: str
    market: Market
    dataset: Dataset
    cadence: Cadence
    legal_status: LegalStatus
    rate_limit: RateLimit
    requires_secret: str | None = None


class FetchContext(BaseModel):
    watchlist: dict[str, list[str]]
    now: datetime
    backfill_since: date | None = None


class RawRecord(BaseModel):
    symbol: str | None
    ts: datetime
    idempotency_key: str
    payload: dict[str, Any]


@runtime_checkable
class Source(Protocol):
    meta: SourceMeta

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_source.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/core/source.py tests/core/test_source.py
git commit -m "feat: add core source protocol and domain types"
```

---

## Task 2: Record envelope schema

**Files:**
- Create: `mimir/storage/schema.py`
- Test: `tests/storage/test_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_schema.py
import pytest
from datetime import UTC, datetime
from pydantic import ValidationError

from mimir.core.source import Dataset, Market
from mimir.storage.schema import Record


def test_record_serializes_to_json_line():
    rec = Record(
        source="stooq", dataset=Dataset.PRICES, market=Market.US, symbol="AAPL",
        ts=datetime(2026, 5, 29, tzinfo=UTC), captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key="stooq:AAPL:2026-05-29", payload={"close": 195.1},
    )
    line = rec.model_dump_json()
    again = Record.model_validate_json(line)
    assert again.idempotency_key == "stooq:AAPL:2026-05-29"
    assert again.schema_version == 1


def test_record_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        Record(source="x", dataset=Dataset.PRICES, market=Market.US, symbol=None,
               ts=datetime(2026, 5, 29, tzinfo=UTC), captured_at=datetime(2026, 5, 29, tzinfo=UTC),
               payload={})  # missing idempotency_key
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mimir.storage.schema'`

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/storage/schema.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from mimir.core.source import Dataset, Market


class Record(BaseModel):
    schema_version: int = 1
    source: str
    dataset: Dataset
    market: Market
    symbol: str | None
    ts: datetime
    captured_at: datetime
    idempotency_key: str
    payload: dict[str, Any]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/storage/test_schema.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/storage/schema.py tests/storage/test_schema.py
git commit -m "feat: add normalized Record envelope schema"
```

---

## Task 3: Partition paths

**Files:**
- Create: `mimir/storage/paths.py`
- Test: `tests/storage/test_paths.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_paths.py
from datetime import date
from pathlib import Path

from mimir.core.source import Dataset
from mimir.storage.paths import partition_path


def test_partition_path_uses_dataset_and_date():
    p = partition_path(Dataset.PRICES, date(2026, 5, 31), root=Path("data"))
    assert p == Path("data/prices/2026/05/31.jsonl")


def test_partition_path_accepts_string_dataset():
    p = partition_path("filings", date(2026, 1, 9), root=Path("/tmp/x"))
    assert p == Path("/tmp/x/filings/2026/01/09.jsonl")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_paths.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/storage/paths.py
from __future__ import annotations

from datetime import date
from pathlib import Path

from mimir.core.source import Dataset

DEFAULT_ROOT = Path("data")


def partition_path(dataset: Dataset | str, dt: date, root: Path = DEFAULT_ROOT) -> Path:
    name = dataset.value if isinstance(dataset, Dataset) else str(dataset)
    return root / name / f"{dt:%Y}" / f"{dt:%m}" / f"{dt:%d}.jsonl"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/storage/test_paths.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/storage/paths.py tests/storage/test_paths.py
git commit -m "feat: add date-partition path rule"
```

---

## Task 4: JSONL store (idempotent append)

**Files:**
- Create: `mimir/storage/jsonl_store.py`
- Test: `tests/storage/test_jsonl_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_jsonl_store.py
from datetime import UTC, datetime
from pathlib import Path

from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record


def _rec(key: str, day: int) -> Record:
    return Record(
        source="stooq", dataset=Dataset.PRICES, market=Market.US, symbol="AAPL",
        ts=datetime(2026, 5, day, tzinfo=UTC), captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key=key, payload={"close": 1.0},
    )


def test_append_writes_partitioned_file(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    n = store.append([_rec("k1", 29)])
    assert n == 1
    assert (tmp_path / "prices/2026/05/29.jsonl").exists()


def test_append_is_idempotent(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k1", 29)])
    added = store.append([_rec("k1", 29), _rec("k2", 29)])
    assert added == 1  # k1 already present, only k2 is new
    lines = (tmp_path / "prices/2026/05/29.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2


def test_append_groups_records_by_day(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k1", 29), _rec("k2", 30)])
    assert (tmp_path / "prices/2026/05/29.jsonl").exists()
    assert (tmp_path / "prices/2026/05/30.jsonl").exists()


def test_read_all_yields_records(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    store.append([_rec("k1", 29), _rec("k2", 30)])
    keys = {r.idempotency_key for r in store.read_all(Dataset.PRICES)}
    assert keys == {"k1", "k2"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_jsonl_store.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/storage/jsonl_store.py
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator

from mimir.core.source import Dataset
from mimir.storage.paths import DEFAULT_ROOT, partition_path
from mimir.storage.schema import Record


class JsonlStore:
    def __init__(self, root: Path = DEFAULT_ROOT) -> None:
        self._root = root

    def _existing_keys(self, path: Path) -> set[str]:
        if not path.exists():
            return set()
        keys: set[str] = set()
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    keys.add(Record.model_validate_json(line).idempotency_key)
        return keys

    def append(self, records: Iterable[Record]) -> int:
        by_path: dict[Path, list[Record]] = defaultdict(list)
        for rec in records:
            by_path[partition_path(rec.dataset, rec.ts.date(), self._root)].append(rec)

        appended = 0
        for path, recs in by_path.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            seen = self._existing_keys(path)
            with path.open("a", encoding="utf-8") as fh:
                for rec in recs:
                    if rec.idempotency_key in seen:
                        continue
                    fh.write(rec.model_dump_json() + "\n")
                    seen.add(rec.idempotency_key)
                    appended += 1
        return appended

    def read_all(self, dataset: Dataset) -> Iterator[Record]:
        base = self._root / dataset.value
        if not base.exists():
            return
        for path in sorted(base.rglob("*.jsonl")):
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        yield Record.model_validate_json(line)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/storage/test_jsonl_store.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/storage/jsonl_store.py tests/storage/test_jsonl_store.py
git commit -m "feat: add idempotent date-partitioned JSONL store"
```

---

## Task 5: Domain errors

**Files:**
- Create: `mimir/core/errors.py`
- Test: `tests/core/test_errors.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_errors.py
from mimir.core.errors import FetchError, MimirError, NormalizationError


def test_error_hierarchy():
    assert issubclass(FetchError, MimirError)
    assert issubclass(NormalizationError, MimirError)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_errors.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/core/errors.py
from __future__ import annotations


class MimirError(Exception):
    """Base class for all Mimir domain errors."""


class FetchError(MimirError):
    """A source failed to fetch data from its upstream."""


class NormalizationError(MimirError):
    """A raw record could not be normalized into a valid Record."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_errors.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mimir/core/errors.py tests/core/test_errors.py
git commit -m "feat: add domain error hierarchy"
```

---

## Task 6: Normalize raw → Record

**Files:**
- Create: `mimir/core/normalize.py`
- Test: `tests/core/test_normalize.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_normalize.py
import pytest
from datetime import UTC, datetime

from mimir.core.errors import NormalizationError
from mimir.core.normalize import normalize
from mimir.core.source import Cadence, Dataset, LegalStatus, Market, RateLimit, RawRecord, SourceMeta

META = SourceMeta(
    id="stooq", market=Market.US, dataset=Dataset.PRICES, cadence=Cadence.DAILY,
    legal_status=LegalStatus.OFFICIAL, rate_limit=RateLimit(),
)
CAPTURED = datetime(2026, 5, 31, tzinfo=UTC)


def test_normalize_builds_record_from_meta():
    raw = RawRecord(symbol="AAPL", ts=datetime(2026, 5, 29, tzinfo=UTC),
                    idempotency_key="stooq:AAPL:2026-05-29", payload={"close": 1.0})
    rec = normalize(raw, META, captured_at=CAPTURED)
    assert rec.source == "stooq"
    assert rec.dataset is Dataset.PRICES
    assert rec.market is Market.US
    assert rec.captured_at == CAPTURED


def test_normalize_wraps_validation_failure():
    class Bad:
        symbol = "AAPL"
        ts = "not-a-datetime"
        idempotency_key = "k"
        payload = {}
    with pytest.raises(NormalizationError):
        normalize(Bad(), META, captured_at=CAPTURED)  # type: ignore[arg-type]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_normalize.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/core/normalize.py
from __future__ import annotations

from datetime import datetime

from pydantic import ValidationError

from mimir.core.errors import NormalizationError
from mimir.core.source import RawRecord, SourceMeta
from mimir.storage.schema import Record


def normalize(raw: RawRecord, meta: SourceMeta, *, captured_at: datetime) -> Record:
    try:
        return Record(
            source=meta.id,
            dataset=meta.dataset,
            market=meta.market,
            symbol=raw.symbol,
            ts=raw.ts,
            captured_at=captured_at,
            idempotency_key=raw.idempotency_key,
            payload=raw.payload,
        )
    except ValidationError as exc:
        raise NormalizationError(str(exc)) from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_normalize.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/core/normalize.py tests/core/test_normalize.py
git commit -m "feat: add raw-to-Record normalization with validation"
```

---

## Task 7: Throttle

**Files:**
- Create: `mimir/core/throttle.py`
- Test: `tests/core/test_throttle.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_throttle.py
from mimir.core.throttle import Throttle


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, secs: float) -> None:
        self.slept.append(secs)
        self.t += secs


def test_first_call_does_not_sleep():
    clock = FakeClock()
    Throttle(max_per_second=2.0, sleep=clock.sleep, monotonic=clock.monotonic).wait()
    assert clock.slept == []


def test_second_call_sleeps_to_respect_rate():
    clock = FakeClock()
    t = Throttle(max_per_second=2.0, sleep=clock.sleep, monotonic=clock.monotonic)  # min interval 0.5s
    t.wait()
    t.wait()
    assert clock.slept == [0.5]


def test_none_rate_uses_conservative_default():
    clock = FakeClock()
    t = Throttle(max_per_second=None, sleep=clock.sleep, monotonic=clock.monotonic)  # default 1/s
    t.wait()
    t.wait()
    assert clock.slept == [1.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_throttle.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/core/throttle.py
from __future__ import annotations

import time
from typing import Callable


class Throttle:
    DEFAULT_MAX_PER_SECOND = 1.0

    def __init__(
        self,
        max_per_second: float | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        rate = max_per_second or self.DEFAULT_MAX_PER_SECOND
        self._min_interval = 1.0 / rate
        self._sleep = sleep
        self._monotonic = monotonic
        self._last: float | None = None

    def wait(self) -> None:
        now = self._monotonic()
        if self._last is not None:
            elapsed = now - self._last
            if elapsed < self._min_interval:
                self._sleep(self._min_interval - elapsed)
        self._last = self._monotonic()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_throttle.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/core/throttle.py tests/core/test_throttle.py
git commit -m "feat: add injectable rate-limit throttle"
```

---

## Task 8: HTTP base + BaseSource

**Files:**
- Create: `mimir/sources/base.py`
- Test: `tests/sources/test_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sources/test_base.py
import pytest
import responses

from mimir.core.errors import FetchError
from mimir.sources.base import http_get


@responses.activate
def test_http_get_returns_on_2xx():
    responses.add(responses.GET, "https://x.test/ok", body="hi", status=200)
    import requests
    resp = http_get("https://x.test/ok", session=requests.Session())
    assert resp.text == "hi"


@responses.activate
def test_http_get_raises_on_4xx():
    responses.add(responses.GET, "https://x.test/nope", status=404)
    import requests
    with pytest.raises(FetchError):
        http_get("https://x.test/nope", session=requests.Session(), max_retries=0)


@responses.activate
def test_http_get_retries_then_succeeds_on_5xx():
    responses.add(responses.GET, "https://x.test/flaky", status=503)
    responses.add(responses.GET, "https://x.test/flaky", body="ok", status=200)
    import requests
    resp = http_get("https://x.test/flaky", session=requests.Session(),
                    max_retries=1, sleep=lambda s: None)
    assert resp.text == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/sources/test_base.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/sources/base.py
from __future__ import annotations

import time
from typing import Any, Callable

import requests

from mimir.core.errors import FetchError
from mimir.core.source import SourceMeta
from mimir.core.throttle import Throttle

DEFAULT_TIMEOUT = 15


def http_get(
    url: str,
    *,
    session: requests.Session,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = 2,
    backoff: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, headers=headers, params=params, timeout=timeout)
        except requests.RequestException as exc:
            last_exc = exc
        else:
            if resp.status_code < 400:
                return resp
            if 400 <= resp.status_code < 500:
                raise FetchError(f"{url} -> HTTP {resp.status_code}")
            last_exc = FetchError(f"{url} -> HTTP {resp.status_code}")
        if attempt < max_retries:
            sleep(backoff * (2**attempt))
    raise FetchError(f"GET failed after retries: {url}") from last_exc


class BaseSource:
    meta: SourceMeta

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        throttle: Throttle | None = None,
    ) -> None:
        self._session = session or requests.Session()
        self._throttle = throttle or Throttle(self.meta.rate_limit.max_per_second)

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        self._throttle.wait()
        return http_get(url, session=self._session, headers=headers, params=params)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/sources/test_base.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/sources/base.py tests/sources/test_base.py
git commit -m "feat: add HTTP helper with retry and throttled BaseSource"
```

---

## Task 9: Stooq adapter (US prices)

**Files:**
- Create: `mimir/sources/stooq.py`
- Test: `tests/sources/test_stooq.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/sources/test_stooq.py
from datetime import UTC, datetime

import requests
import responses

from mimir.core.source import Cadence, Dataset, LegalStatus, Market
from mimir.sources.stooq import StooqSource

CSV = "Date,Open,High,Low,Close,Volume\n2026-05-28,1.0,2.0,0.5,1.5,100\n2026-05-29,1.5,2.5,1.0,2.0,200\n"


def _ctx(symbols):
    from mimir.core.source import FetchContext
    return FetchContext(watchlist={"us": symbols}, now=datetime(2026, 5, 31, tzinfo=UTC))


@responses.activate
def test_stooq_parses_daily_bars():
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)
    src = StooqSource(session=requests.Session())
    recs = list(src.fetch(_ctx(["AAPL"])))
    assert len(recs) == 2
    first = recs[0]
    assert first.symbol == "AAPL"
    assert first.idempotency_key == "stooq:AAPL:2026-05-28"
    assert first.payload["close"] == 1.5
    assert first.ts == datetime(2026, 5, 28, tzinfo=UTC)


def test_stooq_meta_is_official_daily_prices():
    assert StooqSource.meta.market is Market.US
    assert StooqSource.meta.dataset is Dataset.PRICES
    assert StooqSource.meta.cadence is Cadence.DAILY
    assert StooqSource.meta.legal_status is LegalStatus.OFFICIAL
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/sources/test_stooq.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/sources/stooq.py
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Iterable

from mimir.core.source import (
    Cadence, Dataset, FetchContext, LegalStatus, Market, RateLimit, RawRecord, SourceMeta,
)
from mimir.sources.base import BaseSource

BASE_URL = "https://stooq.com/q/d/l/"


class StooqSource(BaseSource):
    meta = SourceMeta(
        id="stooq",
        market=Market.US,
        dataset=Dataset.PRICES,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1.0),
    )

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        for symbol in ctx.watchlist.get("us", []):
            params: dict[str, str] = {"s": f"{symbol.lower()}.us", "i": "d"}
            if ctx.backfill_since is not None:
                params["d1"] = ctx.backfill_since.strftime("%Y%m%d")
                params["d2"] = ctx.now.strftime("%Y%m%d")
            resp = self.get(BASE_URL, params=params)
            yield from self._parse(symbol, resp.text)

    @staticmethod
    def _parse(symbol: str, body: str) -> Iterable[RawRecord]:
        reader = csv.DictReader(io.StringIO(body))
        for row in reader:
            day = row.get("Date", "")
            close = row.get("Close", "")
            if not day or close in ("", "N/D"):
                continue
            ts = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
            yield RawRecord(
                symbol=symbol,
                ts=ts,
                idempotency_key=f"stooq:{symbol}:{day}",
                payload={
                    "open": _f(row.get("Open")),
                    "high": _f(row.get("High")),
                    "low": _f(row.get("Low")),
                    "close": _f(close),
                    "volume": _f(row.get("Volume")),
                    "currency": "USD",
                    "interval": "1d",
                },
            )


def _f(value: str | None) -> float | None:
    if value in (None, "", "N/D"):
        return None
    return float(value)  # type: ignore[arg-type]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/sources/test_stooq.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/sources/stooq.py tests/sources/test_stooq.py
git commit -m "feat: add Stooq US EOD price adapter"
```

---

## Task 10: SEC EDGAR adapter (US filings)

**Files:**
- Create: `mimir/sources/sec_edgar.py`
- Test: `tests/sources/test_sec_edgar.py`

**Note:** SEC requires a descriptive `User-Agent` with contact info (≤10 req/s). The UA is injected from settings (Task 13); the adapter accepts it as a constructor argument with a safe default.

- [ ] **Step 1: Write the failing test**

```python
# tests/sources/test_sec_edgar.py
import json
from datetime import UTC, datetime

import requests
import responses

from mimir.core.source import Dataset, FetchContext, LegalStatus
from mimir.sources.sec_edgar import SecEdgarSource

TICKERS = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
SUBMISSIONS = {
    "filings": {
        "recent": {
            "accessionNumber": ["0000320193-26-000050"],
            "form": ["8-K"],
            "filingDate": ["2026-05-29"],
            "primaryDocument": ["aapl-20260529.htm"],
        }
    }
}


def _ctx():
    return FetchContext(watchlist={"us": ["AAPL"]}, now=datetime(2026, 5, 31, tzinfo=UTC))


@responses.activate
def test_sec_edgar_emits_recent_filings():
    responses.add(responses.GET, "https://www.sec.gov/files/company_tickers.json",
                  body=json.dumps(TICKERS), status=200)
    responses.add(responses.GET, "https://data.sec.gov/submissions/CIK0000320193.json",
                  body=json.dumps(SUBMISSIONS), status=200)
    src = SecEdgarSource(session=requests.Session(), user_agent="Mimir test@example.com")
    recs = list(src.fetch(_ctx()))
    assert len(recs) == 1
    rec = recs[0]
    assert rec.symbol == "AAPL"
    assert rec.idempotency_key == "sec_edgar:0000320193:0000320193-26-000050"
    assert rec.payload["form_type"] == "8-K"
    assert rec.ts == datetime(2026, 5, 29, tzinfo=UTC)
    assert "0000320193-26-000050" in rec.payload["url"]


def test_sec_edgar_meta():
    assert SecEdgarSource.meta.dataset is Dataset.FILINGS
    assert SecEdgarSource.meta.legal_status is LegalStatus.OFFICIAL
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/sources/test_sec_edgar.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/sources/sec_edgar.py
from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

import requests

from mimir.core.source import (
    Cadence, Dataset, FetchContext, LegalStatus, Market, RateLimit, RawRecord, SourceMeta,
)
from mimir.core.throttle import Throttle
from mimir.sources.base import BaseSource

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
RECENT_LIMIT = 50
DEFAULT_UA = "Mimir/0.1 (set MIMIR_SEC_USER_AGENT to your contact)"


class SecEdgarSource(BaseSource):
    meta = SourceMeta(
        id="sec_edgar",
        market=Market.US,
        dataset=Dataset.FILINGS,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=10.0),
    )

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        throttle: Throttle | None = None,
        user_agent: str = DEFAULT_UA,
    ) -> None:
        super().__init__(session=session, throttle=throttle)
        self._headers = {"User-Agent": user_agent}

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        cik_by_ticker = self._load_ticker_map()
        for symbol in ctx.watchlist.get("us", []):
            cik = cik_by_ticker.get(symbol.upper())
            if cik is None:
                continue
            yield from self._fetch_filings(symbol, cik)

    def _load_ticker_map(self) -> dict[str, str]:
        data = self.get(TICKERS_URL, headers=self._headers).json()
        return {row["ticker"].upper(): f"{int(row['cik_str']):010d}" for row in data.values()}

    def _fetch_filings(self, symbol: str, cik10: str) -> Iterable[RawRecord]:
        data = self.get(SUBMISSIONS_URL.format(cik10=cik10), headers=self._headers).json()
        recent = data.get("filings", {}).get("recent", {})
        accessions = recent.get("accessionNumber", [])[:RECENT_LIMIT]
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        docs = recent.get("primaryDocument", [])
        for i, accession in enumerate(accessions):
            day = dates[i]
            ts = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
            no_dashes = accession.replace("-", "")
            doc = docs[i] if i < len(docs) else ""
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik10)}/{no_dashes}/{doc}"
            yield RawRecord(
                symbol=symbol,
                ts=ts,
                idempotency_key=f"sec_edgar:{cik10}:{accession}",
                payload={
                    "form_type": forms[i] if i < len(forms) else None,
                    "title": forms[i] if i < len(forms) else None,
                    "url": url,
                    "filed_at": day,
                },
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/sources/test_sec_edgar.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/sources/sec_edgar.py tests/sources/test_sec_edgar.py
git commit -m "feat: add SEC EDGAR US filings adapter"
```

---

## Task 11: DART adapter (KR filings)

**Files:**
- Create: `mimir/sources/dart.py`
- Test: `tests/sources/test_dart.py`

**Note:** DART `list.json` returns recent filings for a date range and includes `stock_code` per item, so we filter to watchlist codes without the corp_code zip. Requires `DART_API_KEY`.

- [ ] **Step 1: Write the failing test**

```python
# tests/sources/test_dart.py
import json
from datetime import UTC, datetime

import requests
import responses

from mimir.core.source import Dataset, FetchContext, LegalStatus, Market
from mimir.sources.dart import DartSource

LIST_RESPONSE = {
    "status": "000",
    "message": "정상",
    "list": [
        {"corp_code": "00126380", "corp_name": "삼성전자", "stock_code": "005930",
         "report_nm": "주요사항보고서", "rcept_no": "20260529000123", "flr_nm": "삼성전자",
         "rcept_dt": "20260529", "rm": ""},
        {"corp_code": "00999999", "corp_name": "관심없는회사", "stock_code": "111111",
         "report_nm": "분기보고서", "rcept_no": "20260529000999", "flr_nm": "x",
         "rcept_dt": "20260529", "rm": ""},
    ],
}


def _ctx():
    return FetchContext(watchlist={"kr": ["005930"]}, now=datetime(2026, 5, 31, tzinfo=UTC))


@responses.activate
def test_dart_filters_to_watchlist_stock_codes():
    responses.add(responses.GET, "https://opendart.fss.or.kr/api/list.json",
                  body=json.dumps(LIST_RESPONSE), status=200)
    src = DartSource(api_key="dummy", session=requests.Session())
    recs = list(src.fetch(_ctx()))
    assert len(recs) == 1
    rec = recs[0]
    assert rec.symbol == "005930"
    assert rec.idempotency_key == "dart:20260529000123"
    assert rec.payload["form_type"] == "주요사항보고서"
    assert rec.ts == datetime(2026, 5, 29, tzinfo=UTC)
    assert "20260529000123" in rec.payload["url"]


def test_dart_meta():
    assert DartSource.meta.market is Market.KR
    assert DartSource.meta.dataset is Dataset.FILINGS
    assert DartSource.meta.legal_status is LegalStatus.OFFICIAL
    assert DartSource.meta.requires_secret == "DART_API_KEY"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/sources/test_dart.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/sources/dart.py
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Iterable

import requests

from mimir.core.errors import FetchError
from mimir.core.source import (
    Cadence, Dataset, FetchContext, LegalStatus, Market, RateLimit, RawRecord, SourceMeta,
)
from mimir.core.throttle import Throttle
from mimir.sources.base import BaseSource

LIST_URL = "https://opendart.fss.or.kr/api/list.json"
PAGE_COUNT = 100


class DartSource(BaseSource):
    meta = SourceMeta(
        id="dart",
        market=Market.KR,
        dataset=Dataset.FILINGS,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=2.0),
        requires_secret="DART_API_KEY",
    )

    def __init__(
        self,
        *,
        api_key: str,
        session: requests.Session | None = None,
        throttle: Throttle | None = None,
    ) -> None:
        super().__init__(session=session, throttle=throttle)
        self._api_key = api_key

    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]:
        wanted = {code for code in ctx.watchlist.get("kr", [])}
        if not wanted:
            return
        since = ctx.backfill_since or (ctx.now.date() - timedelta(days=1))
        params = {
            "crtfc_key": self._api_key,
            "bgn_de": since.strftime("%Y%m%d"),
            "end_de": ctx.now.strftime("%Y%m%d"),
            "page_no": "1",
            "page_count": str(PAGE_COUNT),
        }
        data = self.get(LIST_URL, params=params).json()
        status = data.get("status")
        if status not in ("000", "013"):  # 013 = no data
            raise FetchError(f"DART error status={status}: {data.get('message')}")
        for item in data.get("list", []):
            code = item.get("stock_code")
            if code not in wanted:
                continue
            rcept_no = item["rcept_no"]
            ts = datetime.strptime(item["rcept_dt"], "%Y%m%d").replace(tzinfo=UTC)
            yield RawRecord(
                symbol=code,
                ts=ts,
                idempotency_key=f"dart:{rcept_no}",
                payload={
                    "form_type": item.get("report_nm"),
                    "title": item.get("report_nm"),
                    "corp_name": item.get("corp_name"),
                    "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                    "filed_at": item.get("rcept_dt"),
                    "flr_nm": item.get("flr_nm"),
                },
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/sources/test_dart.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/sources/dart.py tests/sources/test_dart.py
git commit -m "feat: add DART KR filings adapter"
```

---

## Task 12: Manifest (run log)

**Files:**
- Create: `mimir/manifest/manifest.py`
- Test: `tests/manifest/test_manifest.py` (+ `tests/manifest/__init__.py`)

- [ ] **Step 1: Write the failing test**

```python
# tests/manifest/test_manifest.py
from datetime import UTC, datetime
from pathlib import Path

from mimir.core.source import Cadence
from mimir.manifest.manifest import Manifest, SourceResult


def test_manifest_writes_and_reads_back(tmp_path: Path):
    m = Manifest(root=tmp_path)
    m.write(
        now=datetime(2026, 5, 31, 12, 0, tzinfo=UTC),
        cadence=Cadence.DAILY,
        results=[
            SourceResult(source="stooq", ok=True, fetched=2, stored=2, invalid=0),
            SourceResult(source="dart", ok=False, error="boom"),
        ],
    )
    path = tmp_path / "_manifest/2026/05/31.jsonl"
    assert path.exists()
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1
    assert '"stored":2' in lines[0].replace(" ", "")
    assert "boom" in lines[0]


def test_source_result_ok_default_counts():
    r = SourceResult(source="x", ok=True)
    assert r.fetched == 0 and r.stored == 0 and r.invalid == 0 and r.error is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/manifest/test_manifest.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/manifest/manifest.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from mimir.core.source import Cadence
from mimir.storage.paths import DEFAULT_ROOT


class SourceResult(BaseModel):
    source: str
    ok: bool
    fetched: int = 0
    stored: int = 0
    invalid: int = 0
    error: str | None = None


class RunRecord(BaseModel):
    ran_at: datetime
    cadence: Cadence
    results: list[SourceResult]


class Manifest:
    def __init__(self, root: Path = DEFAULT_ROOT) -> None:
        self._root = root

    def write(self, *, now: datetime, cadence: Cadence, results: list[SourceResult]) -> RunRecord:
        record = RunRecord(ran_at=now, cadence=cadence, results=results)
        path = self._root / "_manifest" / f"{now:%Y}" / f"{now:%m}" / f"{now:%d}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(record.model_dump_json() + "\n")
        return record
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/manifest/test_manifest.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/manifest/manifest.py tests/manifest/
git commit -m "feat: add run manifest log"
```

---

## Task 13: Registry (cadence selection + GRAY policy)

**Files:**
- Create: `mimir/core/registry.py`
- Test: `tests/core/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_registry.py
from mimir.core.registry import Registry
from mimir.core.source import (
    Cadence, Dataset, LegalStatus, Market, RateLimit, SourceMeta,
)


class _FakeSource:
    def __init__(self, meta: SourceMeta) -> None:
        self.meta = meta

    def fetch(self, ctx):  # noqa: ANN001
        return []


def _meta(id_: str, cadence: Cadence, legal: LegalStatus) -> SourceMeta:
    return SourceMeta(id=id_, market=Market.US, dataset=Dataset.PRICES, cadence=cadence,
                      legal_status=legal, rate_limit=RateLimit())


def test_due_filters_by_cadence():
    daily = _FakeSource(_meta("a", Cadence.DAILY, LegalStatus.OFFICIAL))
    weekly = _FakeSource(_meta("b", Cadence.WEEKLY, LegalStatus.OFFICIAL))
    reg = Registry([daily, weekly])
    assert [s.meta.id for s in reg.due(Cadence.DAILY)] == ["a"]


def test_gray_source_excluded_when_disabled():
    official = _FakeSource(_meta("a", Cadence.DAILY, LegalStatus.OFFICIAL))
    gray = _FakeSource(_meta("pykrx", Cadence.DAILY, LegalStatus.GRAY))
    reg = Registry([official, gray], gray_enabled=False)
    assert [s.meta.id for s in reg.due(Cadence.DAILY)] == ["a"]


def test_explicitly_disabled_id_excluded():
    a = _FakeSource(_meta("a", Cadence.DAILY, LegalStatus.OFFICIAL))
    b = _FakeSource(_meta("b", Cadence.DAILY, LegalStatus.OFFICIAL))
    reg = Registry([a, b], disabled_ids={"b"})
    assert [s.meta.id for s in reg.due(Cadence.DAILY)] == ["a"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_registry.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/core/registry.py
from __future__ import annotations

from mimir.core.source import Cadence, LegalStatus, Source


class Registry:
    def __init__(
        self,
        sources: list[Source],
        *,
        gray_enabled: bool = True,
        disabled_ids: set[str] | None = None,
    ) -> None:
        self._sources = sources
        self._gray_enabled = gray_enabled
        self._disabled_ids = disabled_ids or set()

    def due(self, cadence: Cadence) -> list[Source]:
        selected = []
        for source in self._sources:
            meta = source.meta
            if meta.cadence != cadence:
                continue
            if meta.id in self._disabled_ids:
                continue
            if not self._gray_enabled and meta.legal_status is LegalStatus.GRAY:
                continue
            selected.append(source)
        return selected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_registry.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/core/registry.py tests/core/test_registry.py
git commit -m "feat: add source registry with cadence and GRAY policy"
```

---

## Task 14: Orchestrator (run a tick, isolated per source)

**Files:**
- Create: `mimir/core/orchestrator.py`
- Test: `tests/core/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_orchestrator.py
from datetime import UTC, datetime
from pathlib import Path

from mimir.core.orchestrator import Orchestrator
from mimir.core.registry import Registry
from mimir.core.source import (
    Cadence, Dataset, FetchContext, LegalStatus, Market, RateLimit, RawRecord, SourceMeta,
)
from mimir.manifest.manifest import Manifest
from mimir.storage.jsonl_store import JsonlStore


def _meta(id_: str) -> SourceMeta:
    return SourceMeta(id=id_, market=Market.US, dataset=Dataset.PRICES, cadence=Cadence.DAILY,
                      legal_status=LegalStatus.OFFICIAL, rate_limit=RateLimit(max_per_second=1000.0))


class _OkSource:
    meta = _meta("ok")

    def fetch(self, ctx: FetchContext):
        yield RawRecord(symbol="AAPL", ts=datetime(2026, 5, 29, tzinfo=UTC),
                        idempotency_key="ok:AAPL:1", payload={"close": 1.0})


class _BoomSource:
    meta = _meta("boom")

    def fetch(self, ctx: FetchContext):
        raise RuntimeError("upstream down")


def _ctx():
    return FetchContext(watchlist={"us": ["AAPL"]}, now=datetime(2026, 5, 31, tzinfo=UTC))


def test_one_source_failure_does_not_block_others(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    manifest = Manifest(root=tmp_path)
    orch = Orchestrator(Registry([_BoomSource(), _OkSource()]), store, manifest)
    summary = orch.run(Cadence.DAILY, _ctx())
    by_id = {r.source: r for r in summary.results}
    assert by_id["ok"].ok is True
    assert by_id["ok"].stored == 1
    assert by_id["boom"].ok is False
    assert "upstream down" in (by_id["boom"].error or "")
    assert summary.had_failures is True


def test_records_are_persisted(tmp_path: Path):
    store = JsonlStore(root=tmp_path)
    orch = Orchestrator(Registry([_OkSource()]), store, Manifest(root=tmp_path))
    orch.run(Cadence.DAILY, _ctx())
    keys = {r.idempotency_key for r in store.read_all(Dataset.PRICES)}
    assert keys == {"ok:AAPL:1"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_orchestrator.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/core/orchestrator.py
from __future__ import annotations

from pydantic import BaseModel

from mimir.core.errors import NormalizationError
from mimir.core.normalize import normalize
from mimir.core.registry import Registry
from mimir.core.source import Cadence, FetchContext
from mimir.manifest.manifest import Manifest, SourceResult
from mimir.storage.jsonl_store import JsonlStore


class RunSummary(BaseModel):
    cadence: Cadence
    results: list[SourceResult]

    @property
    def had_failures(self) -> bool:
        return any(not r.ok for r in self.results)


class Orchestrator:
    def __init__(self, registry: Registry, store: JsonlStore, manifest: Manifest) -> None:
        self._registry = registry
        self._store = store
        self._manifest = manifest

    def run(self, cadence: Cadence, ctx: FetchContext) -> RunSummary:
        results: list[SourceResult] = []
        for source in self._registry.due(cadence):
            results.append(self._run_one(source, ctx))
        self._manifest.write(now=ctx.now, cadence=cadence, results=results)
        return RunSummary(cadence=cadence, results=results)

    def _run_one(self, source, ctx: FetchContext) -> SourceResult:  # noqa: ANN001
        try:
            raws = list(source.fetch(ctx))
            records = []
            invalid = 0
            for raw in raws:
                try:
                    records.append(normalize(raw, source.meta, captured_at=ctx.now))
                except NormalizationError:
                    invalid += 1
            stored = self._store.append(records)
            return SourceResult(source=source.meta.id, ok=True, fetched=len(raws),
                                stored=stored, invalid=invalid)
        except Exception as exc:  # source isolation: never let one source kill the run
            return SourceResult(source=source.meta.id, ok=False, error=str(exc))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_orchestrator.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/core/orchestrator.py tests/core/test_orchestrator.py
git commit -m "feat: add orchestrator with per-source isolation"
```

---

## Task 15: Settings (env + secret validation)

**Files:**
- Create: `mimir/settings.py`
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_settings.py
from mimir.settings import Settings


def test_settings_reads_env():
    env = {"DART_API_KEY": "abc", "MIMIR_SEC_USER_AGENT": "Me me@example.com"}
    s = Settings.from_env(env)
    assert s.dart_api_key == "abc"
    assert s.sec_user_agent == "Me me@example.com"
    assert s.telegram_bot_token is None


def test_settings_defaults_sec_user_agent():
    s = Settings.from_env({})
    assert "Mimir" in s.sec_user_agent
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_settings.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/settings.py
from __future__ import annotations

import os
from typing import Mapping

from pydantic import BaseModel

DEFAULT_SEC_UA = "Mimir/0.1 (set MIMIR_SEC_USER_AGENT to your contact email)"


class Settings(BaseModel):
    dart_api_key: str | None = None
    fred_api_key: str | None = None
    ecos_api_key: str | None = None
    sec_user_agent: str = DEFAULT_SEC_UA
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = env if env is not None else os.environ
        return cls(
            dart_api_key=env.get("DART_API_KEY"),
            fred_api_key=env.get("FRED_API_KEY"),
            ecos_api_key=env.get("ECOS_API_KEY"),
            sec_user_agent=env.get("MIMIR_SEC_USER_AGENT", DEFAULT_SEC_UA),
            telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=env.get("TELEGRAM_CHAT_ID"),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_settings.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/settings.py tests/test_settings.py
git commit -m "feat: add settings/secret loading from env"
```

---

## Task 16: Status HTML (minimal visibility)

**Files:**
- Create: `mimir/report/status_html.py`
- Test: `tests/report/test_status_html.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/report/test_status_html.py
from datetime import UTC, datetime
from pathlib import Path

from mimir.core.source import Cadence
from mimir.manifest.manifest import RunRecord, SourceResult
from mimir.report.status_html import render_status_html


def test_render_writes_html_with_counts(tmp_path: Path):
    out = tmp_path / "status.html"
    run = RunRecord(
        ran_at=datetime(2026, 5, 31, 12, 0, tzinfo=UTC),
        cadence=Cadence.DAILY,
        results=[SourceResult(source="stooq", ok=True, fetched=2, stored=2),
                 SourceResult(source="dart", ok=False, error="boom")],
    )
    render_status_html(run, out)
    html = out.read_text()
    assert "<html" in html.lower()
    assert "stooq" in html
    assert "dart" in html
    assert "boom" in html
    assert "not financial advice" in html.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/report/test_status_html.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/report/status_html.py
from __future__ import annotations

import html
from pathlib import Path

from mimir.manifest.manifest import RunRecord

DISCLAIMER = "For information only. This is not financial advice."


def render_status_html(run: RunRecord, out_path: Path) -> None:
    rows = []
    for r in run.results:
        status = "OK" if r.ok else "FAIL"
        detail = html.escape(r.error or "") if not r.ok else f"fetched={r.fetched} stored={r.stored}"
        rows.append(
            f"<tr><td>{html.escape(r.source)}</td><td>{status}</td><td>{detail}</td></tr>"
        )
    table = "\n".join(rows)
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Mimir status</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem}}
table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:.4rem .8rem}}
.dis{{color:#888;font-size:.85rem;margin-top:1rem}}</style></head>
<body>
<h1>Mimir — collection status</h1>
<p>Last run: {run.ran_at.isoformat()} ({run.cadence.value})</p>
<table><tr><th>source</th><th>status</th><th>detail</th></tr>
{table}
</table>
<p class="dis">{DISCLAIMER}</p>
</body></html>"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/report/test_status_html.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mimir/report/status_html.py tests/report/
git commit -m "feat: add minimal data-status HTML report"
```

---

## Task 17: Telegram ping (optional)

**Files:**
- Create: `mimir/report/telegram.py`
- Test: `tests/report/test_telegram.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/report/test_telegram.py
import requests
import responses

from mimir.report.telegram import send_ping


def test_send_ping_noop_without_token():
    assert send_ping(bot_token=None, chat_id=None, text="hi") is False


@responses.activate
def test_send_ping_posts_when_configured():
    responses.add(responses.POST, "https://api.telegram.org/botTOK/sendMessage",
                  json={"ok": True}, status=200)
    sent = send_ping(bot_token="TOK", chat_id="123", text="hi", session=requests.Session())
    assert sent is True
    assert responses.calls[0].request.url.endswith("/botTOK/sendMessage")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/report/test_telegram.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/report/telegram.py
from __future__ import annotations

import requests


def send_ping(
    *,
    bot_token: str | None,
    chat_id: str | None,
    text: str,
    session: requests.Session | None = None,
) -> bool:
    if not bot_token or not chat_id:
        return False
    session = session or requests.Session()
    resp = session.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data={"chat_id": chat_id, "text": text},
        timeout=15,
    )
    return resp.status_code == 200
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/report/test_telegram.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mimir/report/telegram.py tests/report/test_telegram.py
git commit -m "feat: add optional Telegram ping"
```

---

## Task 18: Config files + source builder

**Files:**
- Create: `config/watchlist.yaml`, `config/sources.yaml`, `mimir/core/builder.py`
- Test: `tests/core/test_builder.py`

The builder wires settings + config into a concrete source list, skipping sources whose required secret is missing (recorded, not silently dropped).

- [ ] **Step 1: Create config files**

`config/watchlist.yaml`:
```yaml
us:
  - AAPL
  - MSFT
  - NVDA
kr:
  - "005930"   # 삼성전자
  - "000660"   # SK하이닉스
```

`config/sources.yaml`:
```yaml
# Toggle individual sources, and the global gray-source policy.
gray_enabled: true        # set false to disable scraping-based (GRAY) sources like pykrx
disabled_ids: []          # e.g. ["dart"] to turn one off
```

- [ ] **Step 2: Write the failing test**

```python
# tests/core/test_builder.py
from mimir.core.builder import build_sources
from mimir.settings import Settings


def test_builder_includes_keyless_sources():
    sources = build_sources(Settings.from_env({}))
    ids = {s.meta.id for s in sources}
    assert "stooq" in ids
    assert "sec_edgar" in ids


def test_builder_skips_dart_without_key():
    sources = build_sources(Settings.from_env({}))
    assert "dart" not in {s.meta.id for s in sources}


def test_builder_includes_dart_with_key():
    sources = build_sources(Settings.from_env({"DART_API_KEY": "abc"}))
    assert "dart" in {s.meta.id for s in sources}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/core/test_builder.py -v`
Expected: FAIL — module not found.

- [ ] **Step 4: Write minimal implementation**

```python
# mimir/core/builder.py
from __future__ import annotations

from mimir.core.source import Source
from mimir.settings import Settings
from mimir.sources.dart import DartSource
from mimir.sources.sec_edgar import SecEdgarSource
from mimir.sources.stooq import StooqSource


def build_sources(settings: Settings) -> list[Source]:
    sources: list[Source] = [
        StooqSource(),
        SecEdgarSource(user_agent=settings.sec_user_agent),
    ]
    if settings.dart_api_key:
        sources.append(DartSource(api_key=settings.dart_api_key))
    return sources
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/core/test_builder.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add config/ mimir/core/builder.py tests/core/test_builder.py
git commit -m "feat: add config files and source builder"
```

---

## Task 19: `collect` entrypoint

**Files:**
- Create: `mimir/collect.py`
- Test: `tests/test_collect.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_collect.py
from datetime import UTC, datetime
from pathlib import Path

import responses

from mimir.collect import run_collect

CSV = "Date,Open,High,Low,Close,Volume\n2026-05-29,1.0,2.0,0.5,1.5,100\n"
TICKERS = '{"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}'
SUBS = '{"filings": {"recent": {"accessionNumber": [], "form": [], "filingDate": [], "primaryDocument": []}}}'


@responses.activate
def test_run_collect_writes_data_and_status(tmp_path: Path):
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)
    responses.add(responses.GET, "https://www.sec.gov/files/company_tickers.json", body=TICKERS, status=200)
    responses.add(responses.GET, "https://data.sec.gov/submissions/CIK0000320193.json", body=SUBS, status=200)

    summary = run_collect(
        cadence="daily",
        env={},
        watchlist={"us": ["AAPL"], "kr": []},
        data_root=tmp_path / "data",
        status_path=tmp_path / "reports/status.html",
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )
    assert summary.had_failures is False
    assert (tmp_path / "data/prices/2026/05/29.jsonl").exists()
    assert (tmp_path / "reports/status.html").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_collect.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/collect.py
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping

import yaml

from mimir.core.builder import build_sources
from mimir.core.orchestrator import Orchestrator, RunSummary
from mimir.core.registry import Registry
from mimir.core.source import Cadence, FetchContext
from mimir.manifest.manifest import Manifest
from mimir.report.status_html import render_status_html
from mimir.report.telegram import send_ping
from mimir.settings import Settings
from mimir.storage.jsonl_store import JsonlStore

DEFAULT_DATA_ROOT = Path("data")
DEFAULT_STATUS_PATH = Path("reports/status.html")


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_collect(
    *,
    cadence: str,
    env: Mapping[str, str],
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_DATA_ROOT,
    status_path: Path = DEFAULT_STATUS_PATH,
    sources_config: dict | None = None,
    now: datetime | None = None,
) -> RunSummary:
    now = now or datetime.now(UTC)
    settings = Settings.from_env(env)
    cfg = sources_config or {}
    registry = Registry(
        build_sources(settings),
        gray_enabled=cfg.get("gray_enabled", True),
        disabled_ids=set(cfg.get("disabled_ids", [])),
    )
    store = JsonlStore(root=data_root)
    manifest = Manifest(root=data_root)
    orch = Orchestrator(registry, store, manifest)

    ctx = FetchContext(watchlist=watchlist, now=now)
    summary = orch.run(Cadence(cadence), ctx)

    last_run = manifest.write  # already written inside run(); rebuild a RunRecord for the report
    from mimir.manifest.manifest import RunRecord
    render_status_html(RunRecord(ran_at=now, cadence=Cadence(cadence), results=summary.results), status_path)

    ok = sum(1 for r in summary.results if r.ok)
    send_ping(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        text=f"Mimir {cadence}: {ok}/{len(summary.results)} sources OK"
        + ("" if not summary.had_failures else " (failures present)"),
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.collect")
    parser.add_argument("--cadence", required=True, choices=[c.value for c in Cadence])
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args(argv)

    import os
    config_dir = Path(args.config_dir)
    watchlist = _load_yaml(config_dir / "watchlist.yaml") or {"us": [], "kr": []}
    sources_config = _load_yaml(config_dir / "sources.yaml")

    summary = run_collect(
        cadence=args.cadence, env=os.environ, watchlist=watchlist, sources_config=sources_config,
    )
    print(f"[mimir] {args.cadence}: {summary.results}")
    return 1 if summary.had_failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

**Note:** remove the dead `last_run = manifest.write` line during implementation — it is shown here only to flag that the manifest is already written inside `orch.run()`; the report is rebuilt from `summary.results`. Final code:

```python
    summary = orch.run(Cadence(cadence), ctx)

    from mimir.manifest.manifest import RunRecord
    render_status_html(
        RunRecord(ran_at=now, cadence=Cadence(cadence), results=summary.results), status_path
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_collect.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mimir/collect.py tests/test_collect.py
git commit -m "feat: add collect entrypoint wiring the pipeline"
```

---

## Task 20: `backfill` entrypoint

**Files:**
- Create: `mimir/backfill.py`
- Test: `tests/test_backfill.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_backfill.py
from datetime import UTC, date, datetime
from pathlib import Path

import responses

from mimir.backfill import run_backfill

CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2018-01-02,1.0,2.0,0.5,1.5,100\n"
    "2018-01-03,1.5,2.5,1.0,2.0,200\n"
)


@responses.activate
def test_backfill_stooq_loads_history(tmp_path: Path):
    responses.add(responses.GET, "https://stooq.com/q/d/l/", body=CSV, status=200)
    appended = run_backfill(
        source_id="stooq",
        since=date(2018, 1, 1),
        env={},
        watchlist={"us": ["AAPL"], "kr": []},
        data_root=tmp_path / "data",
        now=datetime(2026, 5, 31, tzinfo=UTC),
    )
    assert appended == 2
    assert (tmp_path / "data/prices/2018/01/02.jsonl").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backfill.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# mimir/backfill.py
from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Mapping

import yaml

from mimir.core.builder import build_sources
from mimir.core.normalize import normalize
from mimir.core.source import FetchContext
from mimir.settings import Settings
from mimir.storage.jsonl_store import JsonlStore

DEFAULT_DATA_ROOT = Path("data")


def run_backfill(
    *,
    source_id: str,
    since: date,
    env: Mapping[str, str],
    watchlist: dict[str, list[str]],
    data_root: Path = DEFAULT_DATA_ROOT,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    settings = Settings.from_env(env)
    sources = {s.meta.id: s for s in build_sources(settings)}
    if source_id not in sources:
        raise SystemExit(f"unknown or unavailable source: {source_id}")
    source = sources[source_id]
    store = JsonlStore(root=data_root)

    ctx = FetchContext(watchlist=watchlist, now=now, backfill_since=since)
    records = []
    for raw in source.fetch(ctx):
        records.append(normalize(raw, source.meta, captured_at=now))
    return store.append(records)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mimir.backfill")
    parser.add_argument("--source", required=True)
    parser.add_argument("--since", required=True, help="YYYY-MM-DD")
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args(argv)

    watchlist = _load_yaml(Path(args.config_dir) / "watchlist.yaml") or {"us": [], "kr": []}
    appended = run_backfill(
        source_id=args.source,
        since=date.fromisoformat(args.since),
        env=os.environ,
        watchlist=watchlist,
    )
    print(f"[mimir] backfill {args.source}: appended {appended} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_backfill.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mimir/backfill.py tests/test_backfill.py
git commit -m "feat: add backfill entrypoint"
```

---

## Task 21: GitHub Actions daily workflow + CI

**Files:**
- Create: `.github/workflows/collect-daily.yml`, `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

`.github/workflows/ci.yml`:
```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e ".[dev]"
      - run: ruff check .
      - run: mypy mimir
      - run: coverage run -m pytest && coverage report --fail-under=80
```

- [ ] **Step 2: Create daily collection workflow**

`.github/workflows/collect-daily.yml`:
```yaml
name: collect-daily
on:
  schedule:
    - cron: "23 21 * * 1-5"   # 21:23 UTC weekdays (off-peak minute); adjust as needed
  workflow_dispatch:           # allow manual runs

concurrency:
  group: collect
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e "."
      - name: Collect
        env:
          DART_API_KEY: ${{ secrets.DART_API_KEY }}
          MIMIR_SEC_USER_AGENT: ${{ secrets.MIMIR_SEC_USER_AGENT }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python -m mimir.collect --cadence daily
      - name: Commit data
        run: |
          git config user.name "mimir-bot"
          git config user.email "actions@users.noreply.github.com"
          git add data reports
          git commit -m "data: daily $(date -u +%FT%TZ)" || exit 0
          git pull --rebase
          git push
```

- [ ] **Step 3: Verify workflows are valid YAML**

Run: `python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]; print('ok')"`
Expected: prints `ok`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/
git commit -m "ci: add test workflow and daily collection workflow"
```

---

## Task 22: Full-suite verification + README

**Files:**
- Create: `README.md` (replace the stub), `.env.example`

- [ ] **Step 1: Run the whole suite with coverage**

Run: `coverage run -m pytest && coverage report`
Expected: all tests PASS, coverage ≥ 80%.

- [ ] **Step 2: Run lint + types**

Run: `ruff check . && mypy mimir`
Expected: no errors.

- [ ] **Step 3: Smoke-run the collector locally (network)**

Run: `python -m mimir.collect --cadence daily --config-dir config`
Expected: exits 0 (or 1 with recorded failures), writes `data/...` and `reports/status.html`. Open `reports/status.html` to confirm visibility.

- [ ] **Step 4: Write `.env.example` and README**

`.env.example`:
```
# Optional. Without these the matching sources are skipped (recorded in the manifest).
DART_API_KEY=
MIMIR_SEC_USER_AGENT=Your Name your-email@example.com
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

`README.md` (replace stub): document what Mimir is, the roadmap link, how to install (`pip install -e ".[dev]"`), how to configure the watchlist + secrets, how to run `collect`/`backfill`, the git-as-DB layout, and the legal/disclaimer note.

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example
git commit -m "docs: add README and .env.example"
```

---

## Self-Review

**1. Spec coverage (against `2026-05-31-collector-design.md`):**

| Spec section | Covered by |
|---|---|
| §5.1 Source protocol | Task 1 |
| §5.2 Registry | Task 13 |
| §5.3 Orchestrator | Task 14 |
| §5.4 Throttler | Task 7 |
| §5.5 Normalize + validation | Task 6 |
| §5.6/§8 Storage (JSONL, partition, idempotent) | Tasks 2–4 |
| §5.7 Manifest | Task 12 |
| §5.8/§14 Minimal visibility (HTML + Telegram) | Tasks 16, 17 |
| §6 Data model | Tasks 1, 2 |
| §7 Source catalog (3 adapters) | Tasks 9–11 |
| §9 Scheduling (Actions cron + commit-back) | Task 21 |
| §10 Backfill | Task 20 |
| §11 Error handling + isolation | Tasks 8, 14 |
| §12 Secrets | Task 15 |
| §13 Config (watchlist, sources) | Task 18 |
| §15 Tests (TDD + coverage gate) | every task + Task 21/22 |
| §16 Stack/tooling | Task 0 |
| §17 Acceptance criteria | Task 22 verification |

Deferred (Increment 2, noted up front): pykrx, FRED, ECOS, RSS/Naver, hourly/weekly/monthly workflows. The GRAY on/off mechanism (criterion 8) is built and tested in Task 13.

**2. Placeholder scan:** No "TBD"/"add error handling"/"similar to Task N". Task 19 contains a deliberately-flagged dead line with a corrected final snippet (clearly marked). All code steps show full code.

**3. Type consistency check:**
- `SourceMeta`, `RawRecord`, `Record`, `FetchContext` field names match across Tasks 1, 2, 6, 9–11, 14.
- `JsonlStore.append`/`read_all`, `partition_path` signatures consistent (Tasks 3, 4, 14, 19, 20).
- `Manifest.write(now=, cadence=, results=)` + `SourceResult` fields consistent (Tasks 12, 14, 16, 19).
- `Registry(sources, gray_enabled=, disabled_ids=)` + `due(cadence)` consistent (Tasks 13, 14, 19).
- `normalize(raw, meta, captured_at=)` consistent (Tasks 6, 14, 20).
- `build_sources(settings)` and adapter constructors (`SecEdgarSource(user_agent=)`, `DartSource(api_key=)`, `StooqSource()`) consistent (Tasks 9–11, 18, 19, 20).
- `send_ping(bot_token=, chat_id=, text=, session=)` consistent (Tasks 17, 19).

No mismatches found.
