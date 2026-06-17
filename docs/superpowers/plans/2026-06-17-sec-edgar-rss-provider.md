# SEC EDGAR RSS Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a constrained SEC EDGAR RSS provider that expands explicit CIK/form config into official SEC Atom feed URLs without provider crawling or discovery-time network calls.

**Architecture:** Keep the feature inside the existing RSS feed resolver path. `sources.rss.sec.company_filings` parses into typed models, `resolve_rss_feeds()` expands them into `RssFeed` objects, and `RssSource` fetches those feeds with the configured `MIMIR_SEC_USER_AGENT`.

**Tech Stack:** Python 3.14, pydantic v2, requests/responses, pytest, ruff, mypy.

---

## File Structure

| Path | Responsibility |
|---|---|
| `mimir/sources/rss_catalog.py` | Add SEC company filing config model and URL resolver beside the static RSS catalog resolver. |
| `mimir/sources/config.py` | Parse `sources.rss.sec.company_filings` into `SourcesConfig`. |
| `mimir/sources/rss.py` | Allow `RssSource` to send a configured `User-Agent` header on RSS requests. |
| `mimir/core/builder.py` | Pass SEC RSS config into `resolve_rss_feeds()` and pass `settings.sec_user_agent` into `RssSource`. |
| `tests/sources/test_rss_catalog.py` | Cover SEC feed URL generation, metadata, encoding, duplicate handling, and validation. |
| `tests/sources/test_config.py` | Cover config parsing and malformed SEC RSS config. |
| `tests/sources/test_rss.py` | Cover RSS request `User-Agent` header behavior. |
| `tests/core/test_builder.py` | Cover end-to-end builder wiring from `SourcesConfig` + `Settings` into `RssSource`. |
| `config/sources.yaml` | Add commented example for SEC EDGAR RSS company filing feeds. |
| `docs/reference/config/sources.md` | Document config contract, examples, limits, and User-Agent responsibility. |
| `docs/architecture/extensibility/README.md` | Add SEC RSS provider to the RSS extensibility path. |
| `docs/architecture/improvement-catalog.md` | Mark R1f-SEC implemented while keeping generic provider discovery constrained. |
| `docs/IMPROVEMENTS.md` | Update the follow-up candidate wording after R1f-SEC. |
| `docs/superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md` | Mark implementation status and acceptance checklist after verification. |

---

## Task 1: Add R1f-SEC Contract Tests

**Files:**
- Modify: `tests/sources/test_rss_catalog.py`
- Modify: `tests/sources/test_config.py`
- Modify: `tests/sources/test_rss.py`
- Modify: `tests/core/test_builder.py`

- [ ] **Step 1: Add RSS catalog resolver tests**

Append these tests to `tests/sources/test_rss_catalog.py`:

```python
from pydantic import ValidationError

from mimir.sources.rss_catalog import SecCompanyFilingFeed


def test_resolve_sec_company_filing_feed_without_form_filter():
    feeds = resolve_rss_feeds(
        None,
        None,
        [SecCompanyFilingFeed(cik="320193", symbol="AAPL")],
    )

    assert feeds == [
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=0000320193&owner=exclude&count=40&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        )
    ]


def test_resolve_sec_company_filing_feeds_with_encoded_form_filters():
    feeds = resolve_rss_feeds(
        None,
        None,
        [
            SecCompanyFilingFeed(
                cik="0000320193",
                symbol="AAPL",
                forms=["10-K", "10-K/A"],
                count=20,
                owner="include",
            )
        ],
    )

    assert feeds == [
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=0000320193&type=10-K&owner=include&count=20&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        ),
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=0000320193&type=10-K%2FA&owner=include&count=20&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        ),
    ]


def test_resolve_rss_feeds_rejects_duplicate_sec_and_manual_feed():
    manual = RssFeed(
        url=(
            "https://www.sec.gov/cgi-bin/browse-edgar?"
            "action=getcompany&CIK=0000320193&owner=exclude&count=40&output=atom"
        ),
        publisher="SEC",
        market="US",
        symbol="AAPL",
    )

    with pytest.raises(ValueError, match="duplicate RSS feed"):
        resolve_rss_feeds(None, [manual], [SecCompanyFilingFeed(cik="320193", symbol="AAPL")])


@pytest.mark.parametrize("bad_cik", ["", "ABC", "12345678901"])
def test_sec_company_filing_feed_rejects_bad_cik(bad_cik: str):
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed(cik=bad_cik)


def test_sec_company_filing_feed_rejects_blank_form():
    with pytest.raises(ValidationError):
        SecCompanyFilingFeed(cik="320193", forms=["10-K", "  "])
```

- [ ] **Step 2: Add config parsing tests**

In `tests/sources/test_config.py`, add `SecCompanyFilingFeed` to the `rss_catalog` import:

```python
from mimir.sources.rss_catalog import RssCatalogSelection, SecCompanyFilingFeed
```

Append these tests:

```python
def test_rss_sec_company_filings_parse_from_config():
    cfg = parse_sources_config(
        {
            "sources": {
                "rss": {
                    "sec": {
                        "company_filings": [
                            {
                                "cik": "320193",
                                "symbol": " AAPL ",
                                "forms": ["10-K", "10-K/A"],
                                "count": 20,
                                "owner": "include",
                            }
                        ]
                    }
                }
            }
        }
    )

    assert cfg.rss_sec_company_filings == [
        SecCompanyFilingFeed(
            cik="0000320193",
            symbol="AAPL",
            forms=["10-K", "10-K/A"],
            count=20,
            owner="include",
        )
    ]


def test_rss_sec_company_filings_typo_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config(
            {"sources": {"rss": {"sec": {"company_filingz": [{"cik": "320193"}]}}}}
        )


def test_rss_sec_company_filings_bad_owner_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config(
            {
                "sources": {
                    "rss": {
                        "sec": {
                            "company_filings": [
                                {"cik": "320193", "owner": "everything"}
                            ]
                        }
                    }
                }
            }
        )
```

- [ ] **Step 3: Add RSS User-Agent fetch test**

Append this test to `tests/sources/test_rss.py`:

```python
@responses.activate
def test_rss_fetch_sends_configured_user_agent():
    def callback(request):
        assert request.headers["User-Agent"] == "Mimir Test test@example.com"
        return (200, {}, RSS)

    responses.add_callback(
        responses.GET,
        "https://example.test/feed",
        callback=callback,
    )
    src = RssSource(
        feeds=FEEDS,
        session=requests.Session(),
        user_agent="Mimir Test test@example.com",
    )

    recs = list(src.fetch(_ctx()))

    assert len(recs) == 1
```

- [ ] **Step 4: Add builder wiring tests**

In `tests/core/test_builder.py`, add `SecCompanyFilingFeed` to the `rss_catalog` import:

```python
from mimir.sources.rss_catalog import RssCatalogSelection, SecCompanyFilingFeed
```

Append these tests near the existing RSS builder tests:

```python
def test_build_sources_resolves_sec_company_filing_feeds(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    cfg = SourcesConfig(
        rss_sec_company_filings=[
            SecCompanyFilingFeed(cik="320193", symbol="AAPL", forms=["10-K/A"])
        ]
    )

    sources = build_sources(
        Settings.from_env({"MIMIR_SEC_USER_AGENT": "Mimir Test test@example.com"}),
        cfg,
    )
    rss = _by_id(sources)["rss"]

    assert isinstance(rss, RssSource)
    assert rss._feeds == [
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=0000320193&type=10-K%2FA&owner=exclude&count=40&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        )
    ]
    assert rss._headers == {"User-Agent": "Mimir Test test@example.com"}


def test_build_sources_combines_catalog_sec_and_manual_feeds(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    manual = RssFeed(
        url="https://example.com/aapl.rss",
        publisher="Example",
        market="US",
        symbol="AAPL",
    )
    cfg = SourcesConfig(
        rss_catalogs=[RssCatalogSelection(id="sec_press_releases")],
        rss_sec_company_filings=[SecCompanyFilingFeed(cik="320193", symbol="AAPL")],
        rss_feeds=[manual],
    )

    sources = build_sources(Settings.from_env({}), cfg)
    rss = _by_id(sources)["rss"]

    assert [feed.url for feed in rss._feeds] == [
        "https://www.sec.gov/news/pressreleases.rss",
        (
            "https://www.sec.gov/cgi-bin/browse-edgar?"
            "action=getcompany&CIK=0000320193&owner=exclude&count=40&output=atom"
        ),
        "https://example.com/aapl.rss",
    ]
```

- [ ] **Step 5: Run tests to verify RED**

Run:

```bash
uv run pytest tests/sources/test_rss_catalog.py tests/sources/test_config.py tests/sources/test_rss.py tests/core/test_builder.py -q
```

Expected: FAIL because `SecCompanyFilingFeed`, `rss_sec_company_filings`, `RssSource(user_agent=...)`, and builder wiring do not exist yet.

- [ ] **Step 6: Commit failing tests**

```bash
git add tests/sources/test_rss_catalog.py tests/sources/test_config.py tests/sources/test_rss.py tests/core/test_builder.py
git commit -m "test: cover sec edgar rss provider contract"
```

---

## Task 2: Implement SEC RSS Config and Resolver

**Files:**
- Modify: `mimir/sources/rss_catalog.py`
- Modify: `mimir/sources/config.py`

- [ ] **Step 1: Implement SEC model and resolver**

In `mimir/sources/rss_catalog.py`, add imports:

```python
from typing import Literal
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field, field_validator
```

Replace the existing pydantic import with the combined import above. Add this code after `RssCatalogEntry`:

```python
SEC_BROWSE_EDGAR_URL = "https://www.sec.gov/cgi-bin/browse-edgar"


class SecCompanyFilingFeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cik: str
    symbol: str | None = None
    forms: list[str] | None = None
    count: int = Field(default=40, ge=10, le=100)
    owner: Literal["exclude", "include", "only"] = "exclude"

    @field_validator("cik")
    @classmethod
    def _normalize_cik(cls, value: str) -> str:
        cik = value.strip()
        if not cik or not cik.isdigit() or len(cik) > 10:
            raise ValueError("SEC CIK must be a 1-10 digit string")
        return cik.zfill(10)

    @field_validator("forms")
    @classmethod
    def _normalize_forms(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        forms: list[str] = []
        for form in value:
            normalized = form.strip()
            if not normalized:
                raise ValueError("SEC form type must not be blank")
            forms.append(normalized)
        return forms
```

Add these functions before `_validate_unique_feeds()`:

```python
def resolve_sec_company_filing_feeds(
    selections: Sequence[SecCompanyFilingFeed] | None,
) -> list[RssFeed]:
    feeds: list[RssFeed] = []
    for selection in selections or ():
        forms: Sequence[str | None] = selection.forms or (None,)
        for form in forms:
            feeds.append(
                RssFeed(
                    url=_sec_company_filing_url(selection, form),
                    publisher="SEC",
                    market="US",
                    symbol=selection.symbol,
                )
            )
    _validate_unique_feeds(feeds)
    return feeds


def _sec_company_filing_url(selection: SecCompanyFilingFeed, form: str | None) -> str:
    params: list[tuple[str, str]] = [
        ("action", "getcompany"),
        ("CIK", selection.cik),
    ]
    if form is not None:
        params.append(("type", form))
    params.extend(
        [
            ("owner", selection.owner),
            ("count", str(selection.count)),
            ("output", "atom"),
        ]
    )
    return f"{SEC_BROWSE_EDGAR_URL}?{urlencode(params)}"
```

Change `resolve_rss_feeds()` signature and body:

```python
def resolve_rss_feeds(
    selections: Sequence[RssCatalogSelection] | None,
    manual_feeds: Sequence[RssFeed] | None,
    sec_company_filings: Sequence[SecCompanyFilingFeed] | None = None,
) -> list[RssFeed] | None:
    feeds = [
        *resolve_rss_catalogs(selections),
        *resolve_sec_company_filing_feeds(sec_company_filings),
        *list(manual_feeds or ()),
    ]
    _validate_unique_feeds(feeds)
    return feeds or None
```

- [ ] **Step 2: Implement config parsing**

In `mimir/sources/config.py`, change the `rss_catalog` import:

```python
from mimir.sources.rss_catalog import RssCatalogSelection, SecCompanyFilingFeed
```

Add this field to `SourcesConfig` after `rss_catalogs`:

```python
rss_sec_company_filings: list[SecCompanyFilingFeed] | None = None
```

Add this private model before `_RssBlock`:

```python
class _RssSecBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_filings: list[SecCompanyFilingFeed] | None = None
```

Add this field to `_RssBlock`:

```python
sec: _RssSecBlock | None = None
```

Add this argument to the returned `SourcesConfig` in `parse_sources_config()`:

```python
rss_sec_company_filings=(
    block.rss.sec.company_filings if block.rss and block.rss.sec else None
),
```

- [ ] **Step 3: Run resolver/config tests**

Run:

```bash
uv run pytest tests/sources/test_rss_catalog.py tests/sources/test_config.py -q
```

Expected: PASS for resolver/config tests. RSS and builder tests may still fail until Task 3.

- [ ] **Step 4: Commit implementation**

```bash
git add mimir/sources/rss_catalog.py mimir/sources/config.py
git commit -m "feat: resolve sec edgar rss feeds from config"
```

---

## Task 3: Wire RSS User-Agent Through Builder

**Files:**
- Modify: `mimir/sources/rss.py`
- Modify: `mimir/core/builder.py`

- [ ] **Step 1: Add `RssSource` header support**

In `mimir/sources/rss.py`, update `RssSource.__init__`:

```python
def __init__(
    self,
    *,
    feeds: list[RssFeed] | None = None,
    parse_fn: Callable[[Any], Any] = feedparser.parse,
    session: requests.Session | None = None,
    throttle: Throttle | None = None,
    user_agent: str | None = None,
) -> None:
    super().__init__(session=session, throttle=throttle)
    self._feeds = feeds or list(DEFAULT_FEEDS)
    self._parse_fn = parse_fn
    self._headers = {"User-Agent": user_agent} if user_agent else None
```

Update `fetch()` to pass headers:

```python
resp = self.get(feed.url, headers=self._headers)
```

- [ ] **Step 2: Wire builder config and User-Agent**

In `mimir/core/builder.py`, update the RSS source factory:

```python
SourceSpec(
    "rss",
    lambda settings, cfg: RssSource(
        feeds=resolve_rss_feeds(
            cfg.rss_catalogs,
            cfg.rss_feeds,
            cfg.rss_sec_company_filings,
        ),
        user_agent=settings.sec_user_agent,
    ),
),
```

- [ ] **Step 3: Run targeted tests**

Run:

```bash
uv run pytest tests/sources/test_rss_catalog.py tests/sources/test_config.py tests/sources/test_rss.py tests/core/test_builder.py -q
```

Expected: PASS.

- [ ] **Step 4: Run style/type checks for touched code**

Run:

```bash
uv run ruff check mimir/sources/rss_catalog.py mimir/sources/config.py mimir/sources/rss.py mimir/core/builder.py tests/sources/test_rss_catalog.py tests/sources/test_config.py tests/sources/test_rss.py tests/core/test_builder.py
uv run mypy mimir
```

Expected: both commands pass.

- [ ] **Step 5: Commit wiring**

```bash
git add mimir/sources/rss.py mimir/core/builder.py
git commit -m "feat: send user agent for rss feeds"
```

---

## Task 4: Update Documentation

**Files:**
- Modify: `config/sources.yaml`
- Modify: `docs/reference/config/sources.md`
- Modify: `docs/architecture/extensibility/README.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/IMPROVEMENTS.md`

- [ ] **Step 1: Update example config**

In `config/sources.yaml`, under the commented `sources.rss` block and before `feeds:`, add:

```yaml
#     # SEC EDGAR company filing Atom feeds. This expands config into official
#     # browse-edgar output=atom URLs without crawling SEC pages.
#     # Set MIMIR_SEC_USER_AGENT with a contact email before fetching SEC feeds.
#     sec:
#       company_filings:
#         - { cik: "0000320193", symbol: "AAPL", forms: ["10-K", "10-Q", "8-K"] }
```

- [ ] **Step 2: Update config reference**

In `docs/reference/config/sources.md`, update the top example under `sources.rss` to include:

```yaml
    sec:
      company_filings:
        - cik: "0000320193"
          symbol: "AAPL"
          forms: ["10-K", "10-Q", "8-K"]
          count: 40
          owner: "exclude"
```

Add a subsection after catalog/manual feed explanation:

```markdown
#### SEC EDGAR company filing feeds

`sources.rss.sec.company_filings`는 SEC EDGAR Company Search가 제공하는 Atom feed URL을 설정에서 조립한다. 이 기능은 SEC 페이지를 크롤링하지 않는다. 사용자가 CIK를 명시하면 Mimir가 `browse-edgar?action=getcompany&output=atom` URL을 만든다.

| 필드 | 필수 | 기본값 | 의미 |
|---|---|---|---|
| `cik` | 예 | 없음 | SEC CIK. 숫자 1~10자리를 받으며 URL에는 10자리로 zero-pad된다 |
| `symbol` | 아니오 | 없음 | 이 feed를 연결할 watchlist symbol |
| `forms` | 아니오 | 없음 | `10-K`, `10-Q`, `8-K`, `10-K/A` 같은 form type 목록 |
| `count` | 아니오 | `40` | SEC Atom feed의 count. 허용 범위는 10~100 |
| `owner` | 아니오 | `exclude` | SEC owner filter. `exclude`, `include`, `only` 중 하나 |

SEC fair-access 정책은 자동화 도구가 자신을 식별하고 필요한 요청만 보내기를 요구한다. SEC feed를 쓰는 환경에서는 `MIMIR_SEC_USER_AGENT`를 `서비스명 이메일` 형식으로 설정한다.
```

- [ ] **Step 3: Update architecture docs**

In `docs/architecture/extensibility/README.md`, update the RSS config description to say:

```markdown
RSS 확장은 세 경로를 가진다. `sources.rss.catalogs`는 검증된 정적 feed를 id로 고른다. `sources.rss.sec.company_filings`는 사용자가 명시한 CIK와 form type에서 SEC EDGAR Atom feed URL을 조립한다. `sources.rss.feeds`는 운영자가 직접 아는 URL을 그대로 추가한다.
```

- [ ] **Step 4: Update improvement catalog**

In `docs/architecture/improvement-catalog.md`:

1. Add `R1f-SEC` to the status line.
2. Add a summary row after `R1e`:

```markdown
| **R1f-SEC** | SEC EDGAR company filing RSS provider | 분석품질/확장성 | R1f 보류 항목의 안전한 일부 | **✅ 구현 완료 (2026-06-17)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md) |
```

3. Add a section after R1e:

```markdown
### R1f-SEC. SEC EDGAR RSS provider — **구현 완료 (2026-06-17)**

R1f 전체 live discovery는 여전히 provider별 정책 검토가 필요하다. 하지만 SEC Company Search의 Atom feed는 공식 문서로 추적되고, 사용자가 CIK를 명시하면 URL을 크롤링 없이 조립할 수 있다.

구현 후 `sources.rss.sec.company_filings`는 CIK, optional symbol, optional form list를 받아 `browse-edgar?action=getcompany&output=atom` feed로 확장한다. Resolver는 네트워크를 호출하지 않는다. Fetch 시점에는 `RssSource`가 `MIMIR_SEC_USER_AGENT`를 `User-Agent` header로 보낸다.

남은 generic discovery 부채는 SEC 외 provider, SEC structured disclosure category 자동화, watchlist symbol→CIK 자동 조회, HTML RSS link crawling이다.
```

4. Keep the deferred row, but rename it to generic discovery:

```markdown
| **R1f Generic provider RSS discovery** | R1f-SEC는 공식 SEC Company Search Atom URL 조립만 해결했다. SEC 외 provider, watchlist symbol→CIK 조회, HTML RSS link crawling, vendor URL pattern 추측은 provider 정책과 ToS 검토가 더 필요하다. |
```

5. Add the sequence line:

```text
R1f-SEC ─── SEC EDGAR company filing RSS provider
```

- [ ] **Step 5: Update backlog**

In `docs/IMPROVEMENTS.md`, replace the follow-up candidate with:

```markdown
- Provider별 RSS discovery는 SEC 일부만 안전하게 해소됐다. `sources.rss.sec.company_filings`는 사용자가 CIK를 명시하면 SEC Company Search Atom feed URL을 조립한다. 남은 작업은 SEC structured disclosure category, SEC symbol→CIK 자동 조회, SEC 외 provider, HTML RSS link crawling, vendor URL pattern 추측처럼 provider 정책과 ToS 검토가 더 필요한 범위다.
```

- [ ] **Step 6: Run documentation checks**

Run:

```bash
rg -n "R1f-SEC|sources\\.rss\\.sec|MIMIR_SEC_USER_AGENT|generic discovery|Provider별 RSS" config/sources.yaml docs/reference/config/sources.md docs/architecture/extensibility/README.md docs/architecture/improvement-catalog.md docs/IMPROVEMENTS.md
git diff --check
```

Expected: `rg` finds the new R1f-SEC/config/User-Agent mentions, and `git diff --check` has no output.

- [ ] **Step 7: Commit docs**

```bash
git add config/sources.yaml docs/reference/config/sources.md docs/architecture/extensibility/README.md docs/architecture/improvement-catalog.md docs/IMPROVEMENTS.md
git commit -m "docs: document sec edgar rss provider"
```

---

## Task 5: Mark Spec Complete and Run Full Gates

**Files:**
- Modify: `docs/superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md`

- [ ] **Step 1: Update spec status**

Change:

```markdown
> **상태**: 구현 예정
```

to:

```markdown
> **상태**: 구현 완료
```

Check every item under `## 10. 수용 기준` after the relevant command has passed.

- [ ] **Step 2: Run targeted and full verification**

Run:

```bash
uv run pytest tests/sources/test_rss_catalog.py tests/sources/test_config.py tests/sources/test_rss.py tests/core/test_builder.py -q
uv run ruff check .
uv run mypy mimir
uv run pytest -q
git diff --check
```

Expected:
- Targeted tests pass.
- Ruff reports `All checks passed!`.
- Mypy reports `Success: no issues found`.
- Full pytest passes.
- `git diff --check` has no output.

- [ ] **Step 3: Commit final spec update**

```bash
git add docs/superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md
git commit -m "docs: mark sec edgar rss provider complete"
```

---

## Self-Review

- Spec coverage: Tasks 1-3 cover parsing, CIK normalization, URL generation, encoding, metadata, duplicate detection, no resolver network call by construction, and User-Agent fetch behavior. Task 4 covers all named docs. Task 5 covers verification and checklist updates.
- Placeholder scan command:

```bash
rg -n "TB[D]|TO[D]O|similar[ ]to|implement[ ]later|fill[ ]in[ ]details|appropriate[ ]error|write[ ]tests[ ]for[ ]the[ ]above" docs/superpowers/plans/2026-06-17-sec-edgar-rss-provider.md
```

Expected: no matches.
