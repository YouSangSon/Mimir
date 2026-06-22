# SEC ticker→CIK mapping file refresh/cache — 설계문서 (off-by-default 구현 완료)

> **상태**: off-by-default 구현 완료 (2026-06-19) — `enabled: true` opt-in 시에만 동작. 기본 경로는 네트워크 0. 구현: `mimir/sources/sec_ticker_cik_refresh.py`, 배선: `build_sources` prep step.
> **작성**: 2026-06-19
> **선행**: R1i-SEC-CIK(로컬 lookup), R1j~R1n(오류 표면) · [개선 카탈로그 §6](../../architecture/improvement-catalog.md)
> **대상 독자**: SEC mapping refresh/cache의 현재 경계와 실패 정책을 유지·확장하는 개발자

---

## 0. 이 문서의 위치

이 문서는 R1i 이후 보류됐던 SEC `company_tickers.json` 자동 갱신·cache를 어떤 경계로 풀었는지 기록한다. 현재 구현은 `sources.rss.sec.ticker_cik_map_refresh.enabled`가 켜진 경우에만 build prep 단계에서 동작하며, 기본 경로는 네트워크 0을 유지한다. resolver의 "네트워크 호출 없음" 불변식과 git-as-DB 저장 원칙은 계속 유지된다.

---

## 1. 한눈에 보기

현재: 운영자가 SEC `company_tickers.json`을 로컬에 두고 `sources.rss.sec.ticker_cik_map_path`로 가리키면, resolver가 그 파일을 읽어 ticker를 10자리 CIK로 바꾼다. `ticker_cik_map_refresh.enabled`를 켠 경우에만 Mimir가 build prep 단계에서 TTL gate와 ETag conditional GET으로 mapping file을 best-effort 갱신한다. 파일이 없거나 깨진 상태에서 lookup이 필요하면 path가 포함된 설정 오류로 실패한다.

이 설계가 고정하는 구현 조각: Mimir가 SEC fair-access를 지키며 mapping file을 **선택적으로(opt-in)** 자동 갱신·캐시하는 방법.

---

## 2. 현재 문제와 제약

| 항목 | 현재 동작 | 한계 |
| ---- | --------- | ---- |
| mapping file 획득 | 운영자가 수동 다운로드 | 자동화 운영(GitHub Actions)에서 사람이 주기적으로 갱신해야 함 |
| freshness | 판단하지 않음 | 오래된 snapshot이 새 상장사 ticker를 놓칠 수 있음 |
| 위치 | 로컬 파일 1개 | ephemeral CI runner에서 매 실행 전 준비 필요 |

**왜 보류였나.** (1) SEC fair-access 정책은 자동화 도구가 자신을 식별(UA)하고 필요한 요청만 보내길 요구한다 — 무분별한 재다운로드는 정책 위반. (2) R1i resolver는 **resolver 단계에서 네트워크를 호출하지 않는다**는 불변식을 지킨다(공식 feed URL 조립만). 다운로드를 추가하면 이 경계를 넘는다. (3) git-as-DB 원칙상 큰 SEC 파일(수 MB)을 repo에 커밋할지, 별도 cache로 둘지 결정이 필요하다.

---

## 3. 설계

### 3.1 경계 — resolver 밖, opt-in, off-by-default

다운로드는 **resolver(URL 조립)가 아니라 별도의 명시적 준비 단계**에 둔다. resolver의 "네트워크 호출 없음" 불변식을 보존한다. LLM 시그널과 같은 off-by-default 철학: 명시적 opt-in이 없으면 기존 수동 파일 경로만 쓴다.

```yaml
sources:
  rss:
    sec:
      ticker_cik_map_path: company_tickers.json
      ticker_cik_map_refresh:           # 신규, 기본 미설정(=수동 모드 유지)
        enabled: false                  # off-by-default
        max_age_hours: 168              # 7일보다 오래되면 갱신 시도
        url: "https://www.sec.gov/files/company_tickers.json"
```

### 3.2 SEC fair-access 준수 갱신

- **조건부 GET**: 저장된 `ETag`를 `If-None-Match`로 보내 304면 다운로드 생략. 변경 없을 때 bandwidth·요청을 최소화.
- **UA 의무**: 기존 `MIMIR_SEC_USER_AGENT`(`서비스명 이메일`)를 그대로 재사용. UA 없으면 갱신 비활성(경고).
- **rate limit / throttle**: 기존 `Throttle`·`http_get`(429/5xx backoff, 4xx fast-fail) 경로를 재사용. 갱신은 실행당 최대 1회.
- **TTL 게이트**: 로컬 파일 mtime이 `max_age_hours` 이내면 네트워크를 아예 건드리지 않는다(불필요한 요청 금지).

### 3.3 저장 위치 — git-as-DB와의 조화

`company_tickers.json`(수 MB)은 **분석 산출물이 아니라 외부 reference snapshot**이다. 두 후보:

| 옵션 | 장점 | 단점 | 권고 |
| ---- | ---- | ---- | ---- |
| repo 커밋(`config/` 또는 `data/_cache/`) | CI runner 간 재사용, 감사 가능 | repo 비대, git churn | 비권고(데이터셋 아님) |
| `.gitignore`된 로컬 cache + CI cache key | repo 깨끗, fair-access 친화 | runner 간 ETag 보존에 `actions/cache` 필요 | **권고** |

권고: `data/`나 repo가 아니라 gitignore된 cache 디렉터리에 파일 + ETag metadata를 둔다. GitHub Actions에서는 `actions/cache`로 runner 간 ETag를 보존해 304 경로를 살린다. JSONL 저장 레이아웃·idempotency_key는 **건드리지 않는다**(이건 source record가 아니라 reference data).

### 3.4 실패 모드 — 절대 파이프라인을 막지 않음

| 상황 | 동작 |
| ---- | ---- |
| 갱신 비활성(기본) | 기존 R1i 수동 파일 경로 그대로 |
| 다운로드 실패(네트워크/4xx/5xx) | 경고 후 **기존 로컬 파일로 fallback**. 파일도 없으면 R1i의 기존 설정 오류 |
| 304 Not Modified | 다운로드 생략, 기존 파일 사용 |
| 다운로드 성공하나 비정상 JSON | 새 파일을 채택하지 않고 기존 파일 유지 + 경고(부분 다운로드로 좋은 snapshot을 덮지 않음) |

갱신은 **best-effort**다(telegram delivery와 같은 철학). lookup 자체의 fail-loud 계약(R1i~R1n)은 그대로 유지된다.

---

## 4. 테스트 전략 (구현 시)

- **녹화 fixture, 무네트워크**: 기존 ECOS/SEC 테스트처럼 `responses`로 200/304/4xx/5xx를 mock. 라이브 SEC 호출 없음.
- 조건부 GET: 저장된 ETag가 `If-None-Match`로 나가는지, 304면 다운로드를 생략하는지.
- TTL: 파일이 `max_age_hours` 이내면 네트워크 호출이 0회인지.
- fallback: 다운로드 실패 시 기존 파일로 떨어지고 lookup이 계속되는지; 파일도 없으면 기존 설정 오류.
- off-by-default: `enabled` 미설정/false면 네트워크 호출 0회, 수동 경로와 byte 동일.

---

## 5. 보류 해제 기준 (unblock criteria)

이 설계는 아래가 **모두** 충족될 때 구현한다.

1. 운영자가 SEC fair-access 부담(주기적 자동 요청)을 받아들이기로 명시적으로 결정한다.
2. `MIMIR_SEC_USER_AGENT`가 `서비스명 이메일` 형식으로 설정된 환경이다.
3. resolver의 "네트워크 호출 없음" 불변식을 **준비 단계 분리**(§3.1)로 보존한다는 데 합의한다.
4. cache 저장 위치(§3.3 권고: gitignore + `actions/cache`)를 확정한다.

하나라도 미충족이면 R1i 수동 파일 경로가 정답으로 남는다.

---

## 6. 범위 밖 (이 설계가 다루지 않는 것)

- SEC 외 provider의 mapping/discovery (별도 정책 검토).
- resolver 단계 네트워크 호출(불변식 위반).
- watchlist 전체에서 SEC feed 자동 생성.
- mapping 정확성 보장 — SEC도 보장하지 않으며, Mimir는 snapshot을 그대로 신뢰한다.

---

## 7. 보안·비용·합법성 영향

- **비용**: 무료. 조건부 GET + TTL로 요청을 최소화.
- **합법성**: off-by-default + UA + throttle + 304로 SEC fair-access를 지킨다. 기본 경로는 기존처럼 네트워크 0.
- **보안**: 비밀값 없음. 다운로드 콘텐츠는 public SEC 파일. 부분/오염 다운로드는 채택하지 않음(§3.4).
- **저장 계약**: JSONL/idempotency_key/partition **무변경** — mapping file은 reference snapshot이지 source record가 아니다.
