# pykrx Retry Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pykrx` OHLCV 호출이 일시적으로 실패해도 짧게 재시도하고, 소진 시 `FetchError`로 명확히 실패하도록 만든다.

**Architecture:** `PykrxSource` 안에 pykrx 함수 호출 전용 retry wrapper를 둔다. `BaseSource`는 직접 상속하지 않는다. `pykrx`는 URL 기반 `requests` source가 아니라 외부 package 함수 호출 source이기 때문이다.

**Tech Stack:** Python 3.14, pytest, ruff, mypy, coverage.

---

### Task 1: pykrx retry wrapper

**Files:**
- Modify: `tests/sources/test_pykrx_source.py`
- Modify: `mimir/sources/pykrx_source.py`

- [x] **Step 1: Write failing retry success test**

Add this test to `tests/sources/test_pykrx_source.py`:

```python
def test_pykrx_retries_ohlcv_failure_then_parses_records():
    calls: list[str] = []
    sleeps: list[float] = []

    def flaky_ohlcv_fn(fromdate, todate, ticker):
        calls.append(ticker)
        if len(calls) == 1:
            raise RuntimeError("temporary upstream error")
        return _fake_ohlcv_fn(fromdate, todate, ticker)

    src = PykrxSource(
        ohlcv_fn=flaky_ohlcv_fn,
        max_retries=1,
        backoff=0.25,
        sleep=sleeps.append,
    )

    recs = list(src.fetch(_ctx()))

    assert len(calls) == 2
    assert sleeps == [0.25]
    assert len(recs) == 2
    assert recs[0].idempotency_key == "pykrx:005930:2026-05-28"
```

- [x] **Step 2: Run retry success test and verify RED**

Run:

```bash
.venv/bin/pytest tests/sources/test_pykrx_source.py::test_pykrx_retries_ohlcv_failure_then_parses_records -q
```

Expected: FAIL because `PykrxSource.__init__()` does not accept `max_retries`, `backoff`, or `sleep`.

- [x] **Step 3: Write failing retry exhaustion test**

Add this test to `tests/sources/test_pykrx_source.py`:

```python
def test_pykrx_raises_fetch_error_after_retry_exhaustion():
    calls: list[str] = []
    sleeps: list[float] = []

    def down_ohlcv_fn(fromdate, todate, ticker):
        calls.append(ticker)
        raise RuntimeError("naver timeout")

    src = PykrxSource(
        ohlcv_fn=down_ohlcv_fn,
        max_retries=2,
        backoff=0.1,
        sleep=sleeps.append,
    )

    with pytest.raises(FetchError) as ei:
        list(src.fetch(_ctx()))

    assert len(calls) == 3
    assert sleeps == [0.1, 0.2]
    assert "pykrx OHLCV failed after 3 attempts for 005930" in str(ei.value)
    assert "naver timeout" in str(ei.value)
```

- [x] **Step 4: Run retry exhaustion test and verify RED**

Run:

```bash
.venv/bin/pytest tests/sources/test_pykrx_source.py::test_pykrx_raises_fetch_error_after_retry_exhaustion -q
```

Expected: FAIL for the same missing constructor options.

- [x] **Step 5: Write failing throttle-per-attempt test**

Add this helper and test to `tests/sources/test_pykrx_source.py`:

```python
class _SpyThrottle:
    def __init__(self):
        self.calls = 0

    def wait(self):
        self.calls += 1


def test_pykrx_throttles_every_ohlcv_attempt():
    calls = 0
    throttle = _SpyThrottle()

    def flaky_ohlcv_fn(fromdate, todate, ticker):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary upstream error")
        return _fake_ohlcv_fn(fromdate, todate, ticker)

    src = PykrxSource(
        ohlcv_fn=flaky_ohlcv_fn,
        throttle=throttle,
        max_retries=1,
        sleep=lambda seconds: None,
    )

    list(src.fetch(_ctx()))

    assert throttle.calls == 2
```

- [x] **Step 6: Run throttle test and verify RED**

Run:

```bash
.venv/bin/pytest tests/sources/test_pykrx_source.py::test_pykrx_throttles_every_ohlcv_attempt -q
```

Expected: FAIL because current `PykrxSource` throttles once per ticker and has no retry wrapper.

- [x] **Step 7: Implement minimal retry wrapper**

Update `mimir/sources/pykrx_source.py`:

```python
import time

from mimir.core.errors import FetchError

DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF = 0.5
```

Update the constructor:

```python
def __init__(
    self,
    *,
    ohlcv_fn: OhlcvFn | None = None,
    throttle: Throttle | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")
    if backoff < 0:
        raise ValueError("backoff must be >= 0")
    self._ohlcv_fn = ohlcv_fn or _default_ohlcv_fn
    self._throttle = throttle or Throttle(self.meta.rate_limit.max_per_second)
    self._max_retries = max_retries
    self._backoff = backoff
    self._sleep = sleep
```

Replace the direct call in `fetch()`:

```python
df = self._fetch_ohlcv(fromdate, todate, code)
```

Add helper:

```python
def _fetch_ohlcv(self, fromdate: str, todate: str, code: str) -> Any:
    last_exc: Exception | None = None
    attempts = self._max_retries + 1
    for attempt in range(attempts):
        self._throttle.wait()
        try:
            return self._ohlcv_fn(fromdate, todate, code)
        except Exception as exc:
            last_exc = exc
            if attempt < self._max_retries:
                self._sleep(self._backoff * (2**attempt))
    raise FetchError(
        f"pykrx OHLCV failed after {attempts} attempts for {code}: {last_exc}"
    ) from last_exc
```

- [x] **Step 8: Run focused pykrx tests**

Run:

```bash
.venv/bin/pytest tests/sources/test_pykrx_source.py -q
```

Expected: PASS.

### Task 2: Docs and verification

**Files:**
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/superpowers/specs/2026-06-16-pykrx-retry-policy-design.md`
- Modify: `docs/superpowers/plans/2026-06-16-pykrx-retry-policy.md`
- Possibly modify: `README.md`
- Possibly modify: `README.ko.md`
- Possibly modify: `README.zh.md`

- [x] **Step 1: Update improvement docs**

Mark C3 as implemented in `docs/IMPROVEMENTS.md` and `docs/architecture/improvement-catalog.md`.

Explain that `pykrx` still remains GRAY and optional. The change only makes transient failures less brittle.

- [x] **Step 2: Run verification**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy mimir
git diff --check
.venv/bin/coverage run -m pytest
.venv/bin/coverage report --fail-under=80
```

Expected: all pass. Update README test counts if the total changed.

- [x] **Step 3: Mark plan/spec complete**

After verification passes, update this plan's checkboxes to `[x]` and set the spec status to implemented with the verified test count.
