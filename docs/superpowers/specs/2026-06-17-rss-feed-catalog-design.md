# RSS Feed Catalog Design

> **상태**: ✅ 구현 완료 (`sources.rss.catalogs` + RSS resolver chain). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **날짜**: 2026-06-17
> **범위**: `sources.rss.catalogs` 정적 catalog, `sources.rss.sec.company_filings` SEC Atom URL 조립, local resolver, off-by-default SEC mapping refresh prep. Live endpoint discovery, HTML scraping, vendor URL 추측은 제외한다.

---

## 1. 한눈에 보기

사용자가 종목별 RSS feed URL을 이미 알고 있으면 `sources.rss.feeds[].symbol`로 연결할 수 있다. 그러나 공식 RSS feed를 매번 직접 찾아 YAML에 복사해야 해서 운영자가 같은 URL을 반복해서 관리한다.

이번 증분은 **검증된 RSS feed catalog**를 추가한다. 사용자는 `sources.rss.catalogs`에서 catalog id를 고르고, Mimir는 이를 기존 `RssFeed` 목록으로 변환한다. 변환은 로컬 데이터만 읽고 네트워크를 호출하지 않는다.

---

## 2. 배경

### 2.1 이미 구현된 뉴스 연결 흐름

`RssFeed`는 현재 `url`, `publisher`, `market`, `symbol`만 허용한다. `extra="forbid"`로 오타를 막고, `symbol`은 공백을 제거한 뒤 빈 값이면 실패한다.

`RssSource.fetch()`는 각 feed URL을 가져와 제목, 링크, 발행일, 짧은 요약만 저장한다. 기사 본문 전문은 저장하지 않는다. `symbol`이 있는 feed는 `RawRecord.symbol`을 채우고, idempotency key를 `rss:{symbol}:{link}` 형식으로 만든다. 같은 기사 URL이 여러 종목 feed에 있어도 symbol 관계가 dedup으로 사라지지 않는다.

`NewsMentionMatcher`는 record의 symbol을 제목과 요약보다 먼저 확인한다. 그래서 symbol-tagged RSS feed는 `news_volume`과 opt-in `llm_sentiment` 양쪽에서 바로 효과를 낸다.

### 2.2 남은 문제

운영자가 공식 RSS feed를 쓰려면 URL, publisher, market을 직접 찾아 써야 한다. 이 작업은 작지만 반복적이다. 또한 같은 공식 feed를 여러 환경에서 쓰면 URL 표기가 어긋날 수 있다.

반대로 Mimir가 웹사이트를 돌아다니며 RSS URL을 자동 탐색하면 위험이 커진다. Provider마다 정책과 ToS가 다르고, HTML 구조나 RSS 링크 위치는 안정적인 API 계약이 아니다. 이번 변경은 이 위험을 피한다.

---

## 3. 목표

1. 검증된 RSS feed를 catalog id로 선택할 수 있게 한다.
2. Catalog 선택 결과는 기존 `RssFeed`로 확장한다.
3. 기존 `sources.rss.feeds` 수동 설정은 그대로 유지한다.
4. 설정 오타와 알 수 없는 catalog id는 조용히 무시하지 않는다.
5. Catalog resolver는 네트워크를 호출하지 않는다.
6. 공식 출처와 검증 날짜를 문서에 남긴다.

---

## 4. 비목표

| 제외 항목 | 제외 이유 |
|---|---|
| Live RSS discovery | Provider 정책과 HTML 구조에 의존한다. 첫 증분에서 구현하면 실패 원인이 불명확해진다. |
| Vendor URL pattern 추측 | 검증되지 않은 endpoint를 코드 계약으로 만들 수 있다. |
| 회사별 EDGAR search RSS 자동 생성 | SEC가 EDGAR 검색 결과 RSS를 제공하지만, company/CIK/form filter 조합은 별도 설계가 필요하다. |
| 기사 본문 수집 | 현재 RSS source는 제목과 요약 metadata만 저장한다. 저작권·저장량 정책을 바꾸지 않는다. |
| 유료 뉴스 provider 통합 | 프로젝트의 무료 실행 원칙과 충돌할 수 있다. |

---

## 5. 사용자 설정

새 설정은 `sources.rss.catalogs` 아래에 둔다.

```yaml
sources:
  rss:
    catalogs:
      - id: "sec_press_releases"
    feeds:
      - url: "https://example.com/aapl.rss"
        publisher: "Example"
        market: "US"
        symbol: "AAPL"
```

`catalogs`와 `feeds`를 함께 쓰면 catalog에서 확장한 feed가 먼저 오고, 사용자가 직접 쓴 feed가 뒤에 붙는다. 이 순서는 결과를 예측 가능하게 만든다.

알 수 없는 catalog id는 실패한다. 예를 들어 `sec_press_release`처럼 id를 잘못 쓰면 resolver가 source 생성 전에 실패해야 한다. 잘못된 catalog field는 `extra="forbid"` 정책으로 config parser에서 실패해야 한다.

---

## 6. Catalog 데이터 모델

### 6.1 설정 모델

Catalog selection은 `RssCatalogSelection` 모델로 표현한다.

```python
class RssCatalogSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
```

첫 증분은 `symbols`를 받지 않는다. SEC press release나 litigation release feed는 특정 종목 전용 feed가 아니다. Symbol expansion은 provider별 symbol URL template이 검증된 뒤 별도 증분으로 추가한다.

### 6.2 내부 catalog entry

```python
class RssCatalogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    feed: RssFeed
    description: str
    source_url: str
    verified_on: date
```

`RssCatalogEntry`는 코드 안의 정적 데이터다. `source_url`은 feed가 공식 문서나 공식 페이지에서 확인된 위치를 가리킨다. 이 값은 fetch 대상이 아니라 문서와 감사용 metadata다.

---

## 7. Resolver 설계

새 모듈 `mimir/sources/rss_catalog.py`가 catalog를 소유한다.

Catalog-only resolver는 `resolve_rss_catalogs()`다.

```python
def resolve_rss_catalogs(selections: Sequence[RssCatalogSelection] | None) -> list[RssFeed]:
    ...
```

동작:

1. `selections`가 `None`이면 빈 list를 반환한다.
2. 각 selection의 `id`를 정적 catalog에서 찾는다.
3. 없으면 `ValueError("unknown RSS catalog id: ...")`로 실패한다.
4. 찾으면 entry의 `feed`를 새 `RssFeed`로 복사해 반환한다.
5. 같은 `(url, symbol)`이 두 번 나오면 `ValueError`로 실패한다.

중복은 dedupe하지 않고 실패시킨다. Dedup은 운영자의 설정 오류를 숨길 수 있다. 특히 symbol-tagged feed에서는 같은 URL이라도 symbol이 다르면 서로 다른 관계를 뜻하므로 `(url, symbol)` 기준으로만 판단한다.

현재 구현에는 상위 resolver인 `resolve_rss_feeds()`도 있다. 이 함수는 `resolve_rss_catalogs(selections)`, `resolve_sec_company_filing_feeds(sec.company_filings, sec_ticker_cik_map)`, manual `sources.rss.feeds`를 합친 뒤 같은 `(url, symbol)` 중복을 검증한다. Catalog-only resolver는 여전히 순수 함수이고, 통합 resolver도 네트워크를 호출하지 않는다.

---

## 8. Config와 Builder 흐름

`_RssBlock`은 `catalogs: list[RssCatalogSelection] | None = None`을 가진다. `SourcesConfig`는 `rss_catalogs`를 보존한다.

`parse_sources_config()`는 catalog selection의 shape와 field typo를 검증한다. Catalog id 존재 여부는 resolver가 확인한다. Resolver가 catalog module의 정적 데이터와 가장 가깝기 때문이다.

`build_sources()`의 RSS factory는 다음 순서로 feed를 만든다.

1. `resolve_rss_catalogs(cfg.rss_catalogs)`
2. `resolve_sec_company_filing_feeds(cfg.rss_sec_company_filings, sec_ticker_cik_map)`
3. `cfg.rss_feeds or []`
4. 세 list를 합친 값이 비어 있으면 `None`을 넘겨 기존 `DEFAULT_FEEDS`를 유지한다.
5. 하나라도 있으면 합친 list를 `RssSource(feeds=..., user_agent=settings.sec_user_agent)`에 넘긴다.

즉 현재 ordering은 `catalogs`, `sec.company_filings`, `feeds` 순서다. `MIMIR_SEC_USER_AGENT`는 build된 RSS source의 모든 RSS HTTP 요청에 `User-Agent` header로 전달된다.

`ticker_cik_map_refresh`는 resolver 안에서 실행되지 않는다. 설정에서 `sources.rss.sec.ticker_cik_map_refresh.enabled: true`와 `sources.rss.sec.ticker_cik_map_path`를 함께 둔 경우, `build_sources()`가 resolver 호출 전에 TTL/ETag 기반 best-effort refresh를 수행한다. 기본값은 disabled라서 표준 경로의 mapping download 요청은 0회다.

---

## 9. Catalog 범위와 후속 SEC RSS 증분

R1e 당시 초기 catalog는 SEC 공식 RSS 문서와 SEC 공식 newsroom page에서 확인 가능하고, 직접 HEAD 요청으로 RSS 응답이 확인된 feed만 포함했다.

| id | feed URL | publisher | market | 근거 |
|---|---|---|---|---|
| `sec_press_releases` | `https://www.sec.gov/news/pressreleases.rss` | `SEC` | `US` | SEC RSS Feeds page와 Press Releases page |

현재 `RSS_CATALOG`에는 후속 R1g-SEC-STRUCTURED에서 추가된 SEC structured disclosure catalog도 포함된다.

| id | 범위 |
|---|---|
| `sec_structured_usgaap` | US GAAP/IFRS tagged financial statement filings |
| `sec_structured_risk_return` | mutual fund risk/return tagged filings |
| `sec_structured_inline_xbrl` | Inline XBRL financial statement filings |
| `sec_structured_all_xbrl` | all XBRL filings submitted to the SEC |

이 네 feed는 broad SEC/XBRL feed다. 특정 watchlist symbol 전용 feed가 아니므로 `symbol`을 붙이지 않는다.

SEC Company Search Atom feed 조립은 후속 R1f/R1h/R1i 흐름으로 구현되어 현재 `sources.rss.sec.company_filings` 아래에 있다. 사용자는 CIK 또는 ticker token을 명시하고, 필요하면 `ticker_cik_map_path`로 로컬 SEC mapping file을 읽어 ticker를 10자리 CIK로 바꿀 수 있다. Generic live discovery, watchlist 기반 feed 자동 생성, SEC 외 provider discovery, HTML scraping, vendor URL pattern inference는 여전히 제외한다.

---

## 10. 실패와 예외 처리

| 상황 | 동작 |
|---|---|
| `sources.rss.catalogs`가 없음 | catalog feed를 추가하지 않는다. |
| `sources.rss.catalogs: []` | catalog feed를 추가하지 않는다. |
| catalog id 오타 | config load/build 단계에서 실패한다. |
| catalog field 오타 | pydantic `ValidationError`로 실패한다. |
| 동일 `(url, symbol)`이 catalog와 manual feed에 동시에 있음 | 실패한다. |
| catalog feed fetch 실패 | 기존 `RssSource` fetch 실패 경로를 따른다. |

---

## 11. 테스트 전략

### 11.1 Config parser

- `sources.rss.catalogs`가 typed model로 파싱된다.
- catalog field typo는 실패한다.
- 기존 `sources.rss.feeds` 파싱은 바뀌지 않는다.
- `sources.rss` 미설정은 기존 default feed 동작을 보존한다.

### 11.2 Catalog resolver

- known id가 예상 `RssFeed`로 확장된다.
- unknown id가 실패한다.
- duplicate `(url, symbol)`가 실패한다.
- resolver는 네트워크 호출 없이 순수 함수로 동작한다.

### 11.3 Builder integration

- catalog만 설정해도 `RssSource`가 확장된 feed로 생성된다.
- catalog와 manual feed가 deterministic order로 합쳐진다.
- catalog/manual duplicate는 source 생성 전에 실패한다.
- RSS 설정이 없으면 기존 default feed가 유지된다.

### 11.4 RSS fetch regression

- catalog로 생성된 SEC feed도 기존 RSS fetch path를 그대로 탄다.
- symbol이 없는 catalog feed는 기존 `rss:{link}` idempotency key를 유지한다.

---

## 12. 문서 갱신

다음 문서를 갱신한다.

| 문서 | 변경 |
|---|---|
| `config/sources.yaml` | `sources.rss.catalogs` 예시를 주석으로 추가 |
| `docs/reference/config/sources.md` | catalog 설정, 실패 조건, live discovery 제외 범위 설명 |
| `docs/architecture/extensibility/README.md` | RSS catalog가 source extension 흐름에서 차지하는 위치 설명 |
| `docs/architecture/improvement-catalog.md` | R1e를 보류에서 구현 완료로 이동하되, live discovery는 별도 보류로 남김 |
| `docs/IMPROVEMENTS.md` | 후속 후보 문구를 static catalog 구현 완료 + live discovery 보류로 정리 |
| `README.md`, `README.ko.md`, `README.zh.md` | 테스트 수와 RSS catalog 기능 한 줄 업데이트 |

---

## 13. 수용 기준

- [x] `sources.rss.catalogs`가 `sources.yaml`에서 파싱된다.
- [x] 알 수 없는 catalog id와 typo field가 fail-fast로 실패한다.
- [x] Catalog resolver는 네트워크를 호출하지 않는다.
- [x] Catalog feed와 manual feed는 deterministic order로 합쳐진다.
- [x] 동일 `(url, symbol)` 중복은 실패한다.
- [x] RSS 설정이 없으면 기존 default feed가 유지된다.
- [x] 기존 `sources.rss.feeds[].symbol` behavior는 바뀌지 않는다.
- [x] 문서가 static catalog와 live discovery 제외 범위를 구분한다.
- [x] 전체 test, ruff, mypy, coverage gate가 통과한다.

---

## 14. 보안·정책 영향

이 변경은 secret을 추가하지 않는다. Feed catalog는 공개 RSS URL만 담는다.

Catalog resolver는 네트워크를 호출하지 않는다. 실제 fetch는 기존 `RssSource`만 수행한다. 이 분리는 provider 정책 위반 가능성을 줄이고, 실패 위치를 기존 source fetch 경계로 유지한다.

문서는 live discovery와 vendor URL 추측을 제외한다고 명시한다. 향후 이를 추가하려면 provider별 공식 문서, rate limit, robots/ToS, 저장 metadata 범위를 따로 검토해야 한다.

---

## 15. Rollout

기본 설정은 바뀌지 않는다. `sources.rss.catalogs`를 쓰지 않으면 기존 default SEC press release feed가 유지된다.

운영자는 다음처럼 점진적으로 옮길 수 있다.

1. 기존 manual SEC feed를 그대로 둔다.
2. `sources.rss.catalogs: [{id: "sec_press_releases"}]`를 추가한다.
3. 같은 URL duplicate 실패가 나면 manual SEC feed를 제거한다.
4. 이후 custom symbol feed만 `sources.rss.feeds`에 남긴다.

이 흐름은 duplicate를 조용히 dedupe하지 않기 때문에 운영자가 어떤 feed가 중복인지 명확히 확인하게 한다.
