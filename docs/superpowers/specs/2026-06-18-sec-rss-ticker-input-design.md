# R1h-SEC-TICKER. SEC RSS Ticker Input Design

> **상태**: ✅ 구현 완료 (`SecCompanyFilingFeed.ticker` + SEC Company Search Atom URL expansion). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **작성일**: 2026-06-18
> **범위**: `sources.rss.sec.company_filings`에서 CIK 대신 ticker token을 입력할 수 있게 한다. 별도 SEC ticker map 다운로드, resolver-time network lookup, watchlist-wide feed generation은 제외한다.

---

## 1. 한눈에 보기

R1f-SEC는 사용자가 CIK를 알 때 SEC Company Search Atom feed URL을 조립한다. 이 방식은 안전하지만 운영자가 매번 ticker를 CIK로 바꿔야 한다.

이번 증분은 `sources.rss.sec.company_filings[]` 항목에 `ticker`를 추가한다. 사용자는 `cik` 또는 `ticker` 중 하나만 입력한다. Mimir는 SEC Company Search Atom URL의 `CIK=` query parameter에 해당 값을 deterministic하게 넣고, 실제 feed fetch는 기존 `RssSource.fetch()`에 맡긴다.

구현은 `_normalize_ticker()`로 입력을 정규화하고, `SecCompanyFilingFeed`를 `resolve_sec_company_filing_feeds()`와 `resolve_rss_feeds()`의 기존 흐름에 연결한다.

---

## 2. 근거

SEC 공식 RSS 문서는 EDGAR Company Search 결과를 RSS feed로 구독할 수 있고 filing type으로 더 필터링할 수 있다고 설명한다. SEC Developer Resources와 Accessing EDGAR Data 문서는 자동화 요청이 효율적이어야 하고, 필요한 것만 다운로드해야 하며, 선언된 `User-Agent`를 써야 한다고 설명한다.

SEC Webmaster FAQ는 `company_tickers.json`과 `ticker.txt`를 제공하지만, 이 파일들의 정확성과 범위를 보장하지 않는다고 밝힌다. 따라서 이번 증분에서 resolver가 SEC mapping file을 live로 가져오거나, mapping snapshot을 코드에 크게 내장하지 않는다.

Local verification on 2026-06-18:

```bash
curl -fsSL -A 'Mimir research contact@example.com' \
  'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=AAPL&owner=exclude&count=10&output=atom'
```

위 요청은 Apple company info를 포함한 Atom feed를 반환했다. 이 동작은 SEC Company Search RSS의 현재 관찰된 동작으로 다루며, 버전 고정 API로 과장하지 않는다.

---

## 3. 목표

- `SecCompanyFilingFeed`가 `cik` 또는 `ticker` 중 정확히 하나를 받는다.
- `ticker`는 공백 제거 후 대문자로 정규화한다.
- `ticker`는 ticker token으로 제한하고 회사명 검색 문자열은 받지 않는다.
- `forms`, `count`, `owner`, `symbol`, duplicate `(url, symbol)` 정책은 기존과 동일하게 유지한다.
- Resolver는 네트워크를 호출하지 않는다.
- Config reference와 architecture docs는 `ticker`가 convenience input이며 CIK 직접 지정이 더 deterministic한 path임을 설명한다.

R1i/R1j follow-up note: `ticker_cik_map_refresh`와 local SEC mapping file cache path는 off-by-default로 추가되었지만, `resolve_sec_company_filing_feeds()`와 `resolve_rss_feeds()`의 no-network resolver boundary는 그대로 유지된다. 이번 spec의 현재-truth는 `ticker_cik_map_refresh`를 입력 계약 밖으로 두는 것이다.

---

## 4. 비목표

| 제외 항목 | 이유 |
|---|---|
| SEC mapping file live fetch | resolver-time network dependency와 fair-access 부담을 만든다. |
| SEC mapping snapshot 내장 | 빠르게 stale해지고 정확성/범위가 보장되지 않는다. |
| `ticker_cik_map_refresh` 추가 | 이번 증분은 입력 계약만 바꾸며 별도 refresh 설정을 도입하지 않는다. |
| ambiguous ticker 자동 해소 | SEC mapping 정확성이 보장되지 않으므로 제품 정책 없이 자동 결정을 하지 않는다. |
| watchlist 전체 자동 feed 생성 | 요청 수와 사용자 의도를 바꾼다. |
| SEC 외 provider discovery | provider별 ToS와 HTML 구조 검토가 필요하다. |

---

## 5. 설정 계약

```yaml
sources:
  rss:
    sec:
      company_filings:
        - ticker: "AAPL"
          symbol: "AAPL"
          forms: ["10-K", "10-Q", "8-K"]
          count: 40
          owner: "exclude"
```

| 필드 | 필수 | 기본값 | 의미 |
|---|---|---|---|
| `cik` | 조건부 | 없음 | `ticker`가 없을 때 필수. SEC CIK 1~10자리 숫자이며 URL에는 10자리로 zero-pad된다. |
| `ticker` | 조건부 | 없음 | `cik`가 없을 때 필수. SEC Company Search가 받는 ticker token이다. 공백 제거 후 대문자로 정규화한다. |
| `symbol` | 아니오 | 없음 | 수집 record의 top-level symbol |
| `forms` | 아니오 | 없음 | form type 목록. 여러 개면 form별 feed URL을 만든다. |
| `count` | 아니오 | `40` | SEC Atom feed의 count. 허용 범위는 10~100 |
| `owner` | 아니오 | `exclude` | `exclude`, `include`, `only` 중 하나 |

`cik`와 `ticker`를 둘 다 쓰거나 둘 다 생략하면 설정 오류다. 운영 환경에서 안정성과 duplicate 검출이 더 중요하면 `cik`를 직접 쓰는 편이 낫다.

---

## 6. URL 규칙

Ticker input:

```text
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=AAPL&owner=exclude&count=40&output=atom
```

Ticker + form input:

```text
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=AAPL&type=10-K&owner=exclude&count=40&output=atom
```

CIK input은 기존 zero-padded URL을 그대로 만든다.

---

## 7. 실패와 예외 처리

| 상황 | 처리 |
|---|---|
| `cik`와 `ticker` 둘 다 없음 | pydantic validation error |
| `cik`와 `ticker` 둘 다 있음 | pydantic validation error |
| `ticker`가 blank | pydantic validation error |
| `ticker`에 whitespace나 허용하지 않는 문자가 있음 | pydantic validation error |
| `forms` 항목이 blank | pydantic validation error |
| duplicate `(url, symbol)` | 기존 `duplicate RSS feed` `ValueError` |

---

## 8. 수용 기준

- [x] `{ticker: " aapl ", symbol: "AAPL"}`가 `CIK=AAPL` SEC Atom URL로 확장된다.
- [x] `ticker` path에서도 form filter, count, owner가 기존처럼 적용된다.
- [x] `cik` path는 기존 URL을 유지한다.
- [x] `cik`와 `ticker`를 둘 다 쓰면 실패한다.
- [x] `cik`와 `ticker`를 둘 다 생략하면 실패한다.
- [x] invalid ticker token은 실패한다.
- [x] duplicate `(url, symbol)` 검증은 ticker-generated feed에도 적용된다.
- [x] Config parser와 builder tests가 새 계약을 검증한다.
- [x] User docs와 architecture docs가 no-network boundary와 남은 deferred 범위를 설명한다.
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.

---

## 9. 추적 출처

- SEC RSS Feeds: `https://www.sec.gov/about/rss-feeds`
- SEC Developer Resources: `https://www.sec.gov/about/developer-resources`
- SEC Accessing EDGAR Data: `https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data`
- SEC Webmaster FAQ: `https://www.sec.gov/about/webmaster-frequently-asked-questions`
