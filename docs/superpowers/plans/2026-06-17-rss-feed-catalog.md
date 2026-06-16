# RSS Feed Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `sources.rss.catalogs`가 검증된 정적 RSS feed catalog를 선택하고, 이를 기존 `RssFeed` 목록으로 확장하게 한다.

**Architecture:** 새 `mimir/sources/rss_catalog.py`가 catalog selection model, 정적 catalog metadata, resolver, feed 병합/중복 검증을 소유한다. `mimir/sources/config.py`는 `sources.rss.catalogs` shape만 검증하고, `mimir/core/builder.py`가 resolver 결과를 `RssSource(feeds=...)`에 전달한다. Live discovery, URL pattern 추측, HTML scraping은 구현하지 않는다.

**Tech Stack:** Python 3.14, pydantic v2, pytest, ruff, mypy.

---

### Task 1: Config Parser Shape

**Files:**
- Create: `mimir/sources/rss_catalog.py`
- Modify: `mimir/sources/config.py`
- Modify: `tests/sources/test_config.py`

- [ ] **Step 1: Write failing config parse tests**

Add imports to `tests/sources/test_config.py`:

```python
from mimir.sources.rss_catalog import RssCatalogSelection
```

Add tests near the existing RSS config tests:

```python
def test_rss_catalogs_parse_from_config():
    cfg = parse_sources_config({"sources": {"rss": {"catalogs": [{"id": "sec_press_releases"}]}}})

    assert cfg.rss_catalogs == [RssCatalogSelection(id="sec_press_releases")]
    assert cfg.rss_feeds is None


def test_rss_catalog_typo_field_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config({"sources": {"rss": {"catalogs": [{"idd": "sec_press_releases"}]}}})
```

- [ ] **Step 2: Run tests to verify RED**

```bash
uv run pytest tests/sources/test_config.py::test_rss_catalogs_parse_from_config tests/sources/test_config.py::test_rss_catalog_typo_field_raises_validation_error -q
```

Expected: FAIL because `mimir.sources.rss_catalog` and `SourcesConfig.rss_catalogs` do not exist.

- [ ] **Step 3: Add minimal catalog selection model**

Create `mimir/sources/rss_catalog.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RssCatalogSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
```

Update `mimir/sources/config.py`:

```python
from mimir.sources.rss_catalog import RssCatalogSelection
```

Add to `SourcesConfig`:

```python
rss_catalogs: list[RssCatalogSelection] | None = None
```

Add to `_RssBlock`:

```python
catalogs: list[RssCatalogSelection] | None = None
```

Map it in `parse_sources_config()`:

```python
rss_catalogs=block.rss.catalogs if block.rss else None,
```

- [ ] **Step 4: Run config tests to verify GREEN**

```bash
uv run pytest tests/sources/test_config.py::test_rss_catalogs_parse_from_config tests/sources/test_config.py::test_rss_catalog_typo_field_raises_validation_error -q
```

Expected: PASS.

### Task 2: Static Catalog Resolver

**Files:**
- Modify: `mimir/sources/rss_catalog.py`
- Create: `tests/sources/test_rss_catalog.py`

- [ ] **Step 1: Write failing resolver tests**

Create `tests/sources/test_rss_catalog.py`:

```python
import pytest

from mimir.sources.rss import RssFeed
from mimir.sources.rss_catalog import (
    RssCatalogSelection,
    resolve_rss_catalogs,
    resolve_rss_feeds,
)


def test_resolve_known_rss_catalog_id():
    feeds = resolve_rss_catalogs([RssCatalogSelection(id="sec_press_releases")])

    assert feeds == [
        RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        )
    ]


def test_resolve_unknown_rss_catalog_id_raises_value_error():
    with pytest.raises(ValueError, match="unknown RSS catalog id: nope"):
        resolve_rss_catalogs([RssCatalogSelection(id="nope")])


def test_resolve_duplicate_catalog_selection_raises_value_error():
    with pytest.raises(ValueError, match="duplicate RSS feed"):
        resolve_rss_catalogs(
            [
                RssCatalogSelection(id="sec_press_releases"),
                RssCatalogSelection(id="sec_press_releases"),
            ]
        )


def test_resolve_rss_feeds_combines_catalogs_before_manual_feeds():
    manual = RssFeed(
        url="https://example.com/aapl.rss",
        publisher="Example",
        market="US",
        symbol="AAPL",
    )

    feeds = resolve_rss_feeds([RssCatalogSelection(id="sec_press_releases")], [manual])

    assert feeds == [
        RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        ),
        manual,
    ]


def test_resolve_rss_feeds_returns_none_when_no_catalog_or_manual_feeds():
    assert resolve_rss_feeds(None, None) is None


def test_resolve_rss_feeds_rejects_duplicate_manual_and_catalog_feed():
    manual = RssFeed(
        url="https://www.sec.gov/news/pressreleases.rss",
        publisher="SEC",
        market="US",
    )

    with pytest.raises(ValueError, match="duplicate RSS feed"):
        resolve_rss_feeds([RssCatalogSelection(id="sec_press_releases")], [manual])
```

- [ ] **Step 2: Run resolver tests to verify RED**

```bash
uv run pytest tests/sources/test_rss_catalog.py -q
```

Expected: FAIL because resolver functions and static catalog do not exist.

- [ ] **Step 3: Implement static catalog and resolver**

Replace `mimir/sources/rss_catalog.py` with:

```python
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from pydantic import BaseModel, ConfigDict

from mimir.sources.rss import RssFeed


class RssCatalogSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str


class RssCatalogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    feed: RssFeed
    description: str
    source_url: str
    verified_on: date


RSS_CATALOG: dict[str, RssCatalogEntry] = {
    "sec_press_releases": RssCatalogEntry(
        id="sec_press_releases",
        feed=RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        ),
        description="SEC press releases RSS feed.",
        source_url="https://www.sec.gov/about/rss-feeds",
        verified_on=date(2026, 6, 16),
    )
}


def resolve_rss_catalogs(
    selections: Sequence[RssCatalogSelection] | None,
) -> list[RssFeed]:
    feeds: list[RssFeed] = []
    for selection in selections or ():
        entry = RSS_CATALOG.get(selection.id)
        if entry is None:
            raise ValueError(f"unknown RSS catalog id: {selection.id}")
        feeds.append(entry.feed.model_copy(deep=True))
    _validate_unique_feeds(feeds)
    return feeds


def resolve_rss_feeds(
    selections: Sequence[RssCatalogSelection] | None,
    manual_feeds: Sequence[RssFeed] | None,
) -> list[RssFeed] | None:
    feeds = [*resolve_rss_catalogs(selections), *list(manual_feeds or ())]
    _validate_unique_feeds(feeds)
    return feeds or None


def _validate_unique_feeds(feeds: Sequence[RssFeed]) -> None:
    seen: set[tuple[str, str | None]] = set()
    for feed in feeds:
        key = (feed.url, feed.symbol)
        if key in seen:
            suffix = f" for symbol {feed.symbol}" if feed.symbol else ""
            raise ValueError(f"duplicate RSS feed: {feed.url}{suffix}")
        seen.add(key)
```

- [ ] **Step 4: Run resolver tests to verify GREEN**

```bash
uv run pytest tests/sources/test_rss_catalog.py -q
```

Expected: PASS.

### Task 3: Builder Integration

**Files:**
- Modify: `mimir/core/builder.py`
- Modify: `tests/core/test_builder.py`

- [ ] **Step 1: Write failing builder tests**

Add import to `tests/core/test_builder.py`:

```python
from mimir.sources.rss_catalog import RssCatalogSelection
```

Add tests near existing RSS/source builder tests:

```python
def test_build_sources_resolves_rss_catalog_feeds(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    cfg = SourcesConfig(rss_catalogs=[RssCatalogSelection(id="sec_press_releases")])

    sources = build_sources(Settings.from_env({}), cfg)
    rss = _by_id(sources)["rss"]

    assert isinstance(rss, RssSource)
    assert rss._feeds == [
        RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        )
    ]


def test_build_sources_combines_rss_catalog_and_manual_feeds(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    manual = RssFeed(
        url="https://example.com/aapl.rss",
        publisher="Example",
        market="US",
        symbol="AAPL",
    )
    cfg = SourcesConfig(
        rss_catalogs=[RssCatalogSelection(id="sec_press_releases")],
        rss_feeds=[manual],
    )

    sources = build_sources(Settings.from_env({}), cfg)
    rss = _by_id(sources)["rss"]

    assert isinstance(rss, RssSource)
    assert rss._feeds == [
        RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        ),
        manual,
    ]


def test_build_sources_rejects_duplicate_rss_catalog_and_manual_feed(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    manual = RssFeed(
        url="https://www.sec.gov/news/pressreleases.rss",
        publisher="SEC",
        market="US",
    )
    cfg = SourcesConfig(
        rss_catalogs=[RssCatalogSelection(id="sec_press_releases")],
        rss_feeds=[manual],
    )

    with pytest.raises(ValueError, match="duplicate RSS feed"):
        build_sources(Settings.from_env({}), cfg)
```

- [ ] **Step 2: Run builder tests to verify RED**

```bash
uv run pytest tests/core/test_builder.py::test_build_sources_resolves_rss_catalog_feeds tests/core/test_builder.py::test_build_sources_combines_rss_catalog_and_manual_feeds tests/core/test_builder.py::test_build_sources_rejects_duplicate_rss_catalog_and_manual_feed -q
```

Expected: FAIL because the RSS `SourceSpec` still passes only `cfg.rss_feeds`.

- [ ] **Step 3: Wire resolver into RSS source construction**

Update imports in `mimir/core/builder.py`:

```python
from mimir.sources.rss_catalog import resolve_rss_feeds
```

Change the built-in RSS spec:

```python
SourceSpec(
    "rss",
    lambda settings, cfg: RssSource(
        feeds=resolve_rss_feeds(cfg.rss_catalogs, cfg.rss_feeds)
    ),
),
```

- [ ] **Step 4: Run builder tests to verify GREEN**

```bash
uv run pytest tests/core/test_builder.py::test_build_sources_resolves_rss_catalog_feeds tests/core/test_builder.py::test_build_sources_combines_rss_catalog_and_manual_feeds tests/core/test_builder.py::test_build_sources_rejects_duplicate_rss_catalog_and_manual_feed -q
```

Expected: PASS.

### Task 4: RSS Fetch Regression

**Files:**
- Modify: `tests/sources/test_rss.py`

- [ ] **Step 1: Write failing/guard regression test**

Add imports:

```python
from mimir.sources.rss_catalog import RssCatalogSelection, resolve_rss_feeds
```

Add test:

```python
@responses.activate
def test_rss_fetches_catalog_resolved_feed_with_existing_key_format():
    responses.add(
        responses.GET,
        "https://www.sec.gov/news/pressreleases.rss",
        body=RSS,
        status=200,
    )
    feeds = resolve_rss_feeds([RssCatalogSelection(id="sec_press_releases")], None)
    src = RssSource(feeds=feeds, session=requests.Session())

    recs = list(src.fetch(_ctx()))

    assert len(recs) == 1
    assert recs[0].symbol is None
    assert recs[0].idempotency_key == "rss:https://example.test/news/1"
```

- [ ] **Step 2: Run RSS regression test**

```bash
uv run pytest tests/sources/test_rss.py::test_rss_fetches_catalog_resolved_feed_with_existing_key_format -q
```

Expected: PASS after Task 2. If it fails, fix resolver integration rather than changing RSS idempotency behavior.

### Task 5: Documentation Updates

**Files:**
- Modify: `config/sources.yaml`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md`
- Modify: `docs/superpowers/plans/2026-06-17-rss-feed-catalog.md`

- [ ] **Step 1: Update operator config docs**

Document:

- `sources.rss.catalogs` shape.
- Built-in catalog id: `sec_press_releases`.
- Catalog resolver is static and no-network.
- Live discovery, vendor URL guessing, and EDGAR query RSS generation are not implemented.
- `sources.rss.feeds` remains the manual escape hatch.
- Duplicate `(url, symbol)` fails.

- [ ] **Step 2: Update architecture and improvement docs**

Update:

- `docs/architecture/improvement-catalog.md`: mark R1e static catalog implemented; leave live discovery/provider expansion as deferred.
- `docs/IMPROVEMENTS.md`: replace the follow-up candidate with provider-specific live discovery/catalog expansion.
- `docs/architecture/extensibility/README.md`: explain RSS catalog as a built-in configuration convenience, not a plugin system replacement.

- [ ] **Step 3: Update README variants and test counts**

After full verification, update README badge/table test count from 424 to the final count. Mention RSS catalog in the config/source adapter text.

- [ ] **Step 4: Update spec and plan status**

After verification, mark acceptance criteria in `docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md` as complete and check completed plan steps in this file.

### Task 6: Final Verification And Reviews

**Files:** no intended source writes except review fixes.

- [ ] **Step 1: Run focused tests**

```bash
uv run pytest tests/sources/test_config.py tests/sources/test_rss_catalog.py tests/sources/test_rss.py tests/core/test_builder.py -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run quality gates**

```bash
uv run ruff check .
uv run mypy mimir
uv run coverage run -m pytest
uv run coverage report --fail-under=80
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 3: Run subagent reviews**

Dispatch spec compliance review first. After approval, dispatch code quality review. Fix any findings and rerun relevant tests plus `git diff --check`.

- [ ] **Step 4: Commit**

Stage only intended files. Do not stage unrelated `uv.lock`.

```bash
git add \
  README.md README.ko.md README.zh.md \
  config/sources.yaml \
  docs/IMPROVEMENTS.md \
  docs/architecture/extensibility/README.md \
  docs/architecture/improvement-catalog.md \
  docs/reference/config/sources.md \
  docs/superpowers/specs/2026-06-17-rss-feed-catalog-design.md \
  docs/superpowers/plans/2026-06-17-rss-feed-catalog.md \
  mimir/core/builder.py \
  mimir/sources/config.py \
  mimir/sources/rss_catalog.py \
  tests/core/test_builder.py \
  tests/sources/test_config.py \
  tests/sources/test_rss.py \
  tests/sources/test_rss_catalog.py
git commit -m "feat: add rss feed catalog"
```
