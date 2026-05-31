# S1. Mimir Collector — 설계문서

> **스펙 ID**: S1
> **작성일**: 2026-05-31
> **상태**: 리뷰 대기
> **선행 문서**: [프로그램 로드맵](../../architecture/roadmap.md)

---

## 1. 개요

Mimir Collector는 한국·미국 시장의 공개 데이터를 무료·합법으로 수집해, 정규화한 뒤 repo에 시계열로 저장하는 서브시스템이다. 이후 모든 분석·리포트·과거패턴 단계가 여기서 만든 데이터를 소비한다.

**한 줄 요약**: 이종(heterogeneous) 공개 소스 → 공통 어댑터 → 정규화 → 날짜 파티션 JSONL(git-as-DB).

---

## 2. 범위

### 포함 (in scope)

- **Source 어댑터 프레임워크 + 레지스트리** — 공통 인터페이스 뒤에 각 소스를 구현
- **정규화 레코드 스키마** — 모든 소스가 공통 envelope로 수렴, 경계에서 검증
- **저장 레이어** — 날짜 파티션 JSONL(`data/<dataset>/YYYY/MM/DD.jsonl`), append-only, 멱등
- **워치리스트 설정** — 추적할 KR/US 종목·기업 목록(YAML/TOML)
- **첫 소스 세트** — Stooq, SEC EDGAR, pykrx, DART OpenAPI, FRED, ECOS, RSS(+ 선택적 Naver 검색 API)
- **스로틀러 + 합법성 레지스트리** — 소스별 rate limit·legal_status를 코드로 강제
- **백필(backfill)** — 과거 이력 일괄 적재(Stooq EOD 수년치, FRED 장기 시계열, EDGAR 과거 공시)
- **cadence 오케스트레이터** — 매시간/매일/매주/매월에 어떤 소스를 돌릴지 선택
- **GitHub Actions 워크플로** — cadence별 cron + 커밋백 + concurrency 가드
- **수집 매니페스트** — 실행 로그(무엇을·언제·몇 건·성공/실패)
- **최소 가시성** — 데이터 현황 HTML 1장 + "수집 완료" 텔레그램 핑(옵션)

### 제외 (out of scope — 다음 스펙)

- 인사이트·⭐별점 생성 → **S2 Analysis**
- 과거 유사사례 매칭·사후수익 분석 → **S4 Historical** (단, S1의 백필이 이를 가능케 함)
- 풍부한 일일 HTML 리포트·정기 텔레그램 다이제스트 → **S3 Delivery** (S1은 최소 가시성 스텁만)
- 자동매매 → **S5 (미래)**

---

## 3. 설계 원칙

| 원칙 | 적용 |
|---|---|
| **소스 격리** | 한 어댑터의 실패·포맷변경이 다른 소스나 파이프라인 전체를 멈추지 않는다 |
| **합법성 우선** | 공식 API 우선. 그레이존(pykrx)은 메타데이터로 명시 + 스로틀 + 내부분석 한정 |
| **멱등성(idempotent)** | 같은 수집을 다시 돌려도 중복 레코드가 쌓이지 않는다 |
| **불변 데이터** | 한 번 쓴 JSONL 라인은 수정하지 않고 append만 한다 |
| **경계 검증** | 외부 데이터는 신뢰하지 않는다. pydantic으로 envelope를 검증한 뒤 저장 |
| **작은 파일 다수** | 어댑터·유틸을 도메인별로 분리(200–400줄 기본, 800줄 상한) |
| **무침묵 실패** | 에러를 삼키지 않는다. 매니페스트에 실패를 기록하고 비제로로 종료 신호 |

---

## 4. 아키텍처

### 4.1 모듈 구조

```
config/         워치리스트(종목), 소스 설정 (정적 데이터)
  │
sources/        어댑터들 — 각자 fetch() → Iterable[RawRecord], 메타데이터 보유
  │  (Source 프로토콜 구현)
  ▼
core/           오케스트레이터 · 스로틀러 · 정규화 · 합법성 레지스트리
  ▼
storage/        JSONL writer/reader (날짜 파티션, append-only, 멱등 dedup)
  ▼
report/         최소 데이터-현황 HTML + 텔레그램 핑(옵션)
  ▲
manifest/       수집 실행 로그
```

### 4.2 디렉토리 레이아웃 (제안)

```
mimir/
  __init__.py
  collect.py              # 진입점: python -m mimir.collect --cadence daily
  backfill.py             # 진입점: python -m mimir.backfill --source stooq --since 2018-01-01
  core/
    source.py             # Source 프로토콜, SourceMeta, Cadence, LegalStatus
    registry.py           # 소스 등록·조회, cadence별 due 소스 선택
    orchestrator.py       # 틱 실행: 선택→fetch→정규화→저장→매니페스트
    throttle.py           # 소스별 rate-limit 준수 (토큰버킷/슬립)
    normalize.py          # RawRecord → Record envelope 변환·검증
    errors.py             # 도메인 예외
  sources/
    base.py               # 공통 HTTP 헬퍼(UA, 재시도, 타임아웃)
    stooq.py              # US/KR EOD 가격 (대량 CSV)
    sec_edgar.py          # US 공시
    pykrx_source.py       # KR OHLCV (⚠️ gray)
    dart.py               # KR 공시
    fred.py               # US 거시
    ecos.py               # KR 거시
    rss.py                # 공식 RSS 뉴스 헤드라인
    naver_news.py         # (옵션) Naver 검색 API 뉴스
  storage/
    schema.py             # pydantic 모델: Record envelope, dataset별 payload
    jsonl_store.py        # 날짜 파티션 append, 멱등 키, reader
    paths.py              # 경로 규칙 data/<dataset>/YYYY/MM/DD.jsonl
  manifest/
    manifest.py           # 실행 로그 기록·조회
  report/
    status_html.py        # 데이터 현황 HTML 렌더
    telegram.py           # (옵션) 핑 발송
  settings.py             # 환경변수/시크릿 로딩·검증

config/
  watchlist.yaml          # 추적 종목 (KR/US)
  sources.yaml            # 소스 on/off, 파라미터

data/                     # git-as-DB (수집물 저장)
  prices/2026/05/31.jsonl
  filings/...
  macro/...
  news/...
  _manifest/2026/05/31.jsonl

reports/                  # 최소 가시성 산출물
  status.html

.github/workflows/
  collect-hourly.yml
  collect-daily.yml
  collect-weekly.yml
  collect-monthly.yml

tests/
  sources/  core/  storage/  fixtures/   # 녹화된 응답 픽스처
```

---

## 5. 핵심 컴포넌트

### 5.1 `Source` 프로토콜

모든 어댑터가 구현하는 공통 인터페이스. 오케스트레이터는 구체 소스를 모른 채 이 인터페이스만 다룬다.

```python
class SourceMeta(BaseModel):
    id: str                  # "sec_edgar"
    market: Literal["US", "KR", "GLOBAL"]
    dataset: Literal["prices", "filings", "macro", "news"]
    cadence: Cadence         # HOURLY/DAILY/WEEKLY/MONTHLY
    legal_status: LegalStatus  # OFFICIAL / GRAY
    rate_limit: RateLimit    # 예: 10 req/s, 2 req/s, None
    requires_secret: str | None  # 필요한 env 키 이름

class Source(Protocol):
    meta: SourceMeta
    def fetch(self, ctx: FetchContext) -> Iterable[RawRecord]: ...
```

- `FetchContext`: 워치리스트, 실행 시각, 백필 여부/기간 등 입력.
- `fetch()`는 *네트워크만* 담당하고 저장은 모른다(단일 책임).
- `legal_status == GRAY`인 소스는 `sources.yaml`에서 끌 수 있다(사용자 정책: pykrx는 언제든 off 가능).

### 5.2 레지스트리

- 사용 가능한 소스를 등록한다.
- `due(cadence)` → 이번 틱에 돌릴 소스 목록을 반환한다.
- `sources.yaml`의 on/off, GRAY 차단 정책을 반영한다.

### 5.3 오케스트레이터

틱당 실행 흐름:

```
1. registry.due(cadence) 로 대상 소스 선택
2. 각 소스마다 (격리된 try/except):
     throttle.acquire(source.meta.rate_limit)
     raw = source.fetch(ctx)
     records = normalize(raw, source.meta)   # 검증 포함
     stored = jsonl_store.append(records)     # 멱등 dedup
     manifest.record(source.id, ok=True, count=stored)
   실패 시: manifest.record(source.id, ok=False, error=...)  # 삼키지 않음
3. report.status_html.render()                # 최소 가시성
4. (옵션) telegram.ping(요약)
5. 비제로 종료코드로 부분 실패 신호(워크플로 로그에 노출)
```

### 5.4 스로틀러

소스별 rate limit을 코드로 강제한다(검증된 값 기준). 예: EDGAR ≤10 req/s, FRED ≤2 req/s. 토큰버킷 또는 최소 간격 슬립.

### 5.5 정규화 + 검증

`RawRecord`(소스별) → 공통 `Record` envelope. pydantic으로 필수 필드·타입을 검증한다. 검증 실패 레코드는 버리고 매니페스트에 카운트한다(부분 손실 가시화).

### 5.6 스토리지

5.7절 참고. append-only, 멱등 dedup, 날짜 파티션.

### 5.7 매니페스트

매 실행을 `data/_manifest/YYYY/MM/DD.jsonl`에 한 줄씩 기록한다: 시각, cadence, 소스별 성공여부·건수·소요시간·에러. 나중에 데이터 신뢰성·결손 추적의 근거가 된다.

### 5.8 리포트(최소 가시성)

- `reports/status.html` — 데이터셋별 마지막 수집 시각·누적 건수·최근 실패를 보여주는 정적 1페이지. "레이어가 죽은 코드가 아님"을 눈으로 확인하는 용도.
- `telegram.ping` — 옵션. 봇 토큰이 있으면 "수집 완료/실패 N건" 한 줄 발송. 풍부한 다이제스트는 S3.

---

## 6. 데이터 모델

### 6.1 공통 envelope

```jsonc
{
  "schema_version": 1,
  "source": "sec_edgar",          // SourceMeta.id
  "dataset": "filings",           // prices | filings | macro | news
  "market": "US",                 // US | KR | GLOBAL
  "symbol": "AAPL",               // 종목/시리즈 식별자 (없으면 null)
  "ts": "2026-05-31T13:23:00Z",   // 데이터가 가리키는 시점 (이벤트 시각)
  "captured_at": "2026-05-31T13:25:10Z", // 수집 시각
  "idempotency_key": "sec_edgar:AAPL:0000320193-26-000050", // dedup 키
  "payload": { /* 소스별 핵심 필드 (원본 보존) */ }
}
```

### 6.2 dataset별 payload (요지)

- **prices** — `open/high/low/close/volume`, `currency`, `interval`(1d 등)
- **filings** — `form_type`(10-K/8-K/사업보고서…), `title`, `url`, `filed_at`
- **macro** — `series_id`, `value`, `unit`, `period`
- **news** — `title`, `url`, `publisher`, `published_at`, `summary`(전문 저장 안 함, 저작권)

`idempotency_key`로 같은 사실의 중복 저장을 막는다(멱등성의 핵심).

---

## 7. 데이터 소스 카탈로그 (검증된 사실 기준, 2026-05-31)

> 일부 한도는 공식 페이지가 JS 렌더링이라 기계 확인이 어려워 **unverified**로 표시한다. 구현 단계에서 콘솔/문서로 재확인한다.

### 🇺🇸 US

| 소스 | 데이터 | 인증 | 무료 | rate limit | 합법성 | 라이브러리 |
|---|---|---|---|---|---|---|
| **SEC EDGAR** | 공시(10-K/Q/8-K), companyfacts | UA 헤더(연락처) | ✅ | **10 req/s** (공식) | ✅ 스크립트 접근 명시 허용 | `sec-edgar-api`/raw |
| **Stooq** | per-symbol EOD CSV | 무료 `apikey`(캡차 발급)¹ | ✅ | 미공시 | ✅ 무료 | `requests`(직접) |
| **FRED** | 거시 시계열 | 무료 키 | ✅ | **2 req/s** (공식, 초과시 429) | ✅ 공식, 출처표기 | `fredapi` |
| (보강) Finnhub | per-symbol 시세·펀더멘털 | 무료 키 | ✅ | 60/min (공식) | personal-use | `finnhub-python` |

> ¹ **구현 중 발견(2026-05-31)**: Stooq의 per-symbol CSV 엔드포인트(`/q/d/l/`)는 이제 무료 `apikey`를 요구한다(캡차로 1회 발급, 파라미터명 `apikey` 확인됨). 따라서 Stooq는 DART처럼 키가 없으면 스킵된다. 키 없이 동작하는 유일한 소스는 SEC EDGAR(UA만 필요). 키 발급이 번거로우면 Increment 2에서 Twelve Data(무료 키, time_series) 등으로 가격원 보강 가능.

- **1차 가격원으로 yfinance(야후)는 제외** — 야후 ToS가 자동수집을 금지(그레이). Stooq로 대체.

### 🇰🇷 KR

| 소스 | 데이터 | 인증 | 무료 | rate limit | 합법성 | 라이브러리 |
|---|---|---|---|---|---|---|
| **DART OpenAPI** | 공시·재무제표 | 무료 키 | ✅ | ~20,000/day (**unverified**) | ✅ 공식 | `OpenDartReader`/`dart-fss` |
| **pykrx** | KOSPI/KOSDAQ OHLCV·수급 | 불필요 | ✅ | 미공시 | ⚠️ **그레이(스크래핑)** — 스로틀+내부한정 | `pykrx` |
| **ECOS(한국은행)** | 금리·환율·CPI 등 거시 | 무료 키 | ✅ | ~100,000/day (**unverified**) | ✅ 공식 | `PublicDataReader` |
| 뉴스 | 헤드라인/메타 | RSS 불필요 / Naver 키 | ✅ | Naver ~25k/day(secondary) | ✅ 공식 RSS / Naver API | `feedparser` |

**pykrx 정책(사용자 확정)**: 포함하되 (1) 스로틀로 호출량 억제, (2) 내부분석 용도 한정(재배포 금지), (3) `sources.yaml`에서 언제든 off 가능. legal_status=GRAY로 코드에 표식.

---

## 8. 저장 레이아웃 (git-as-DB)

- **형식**: JSONL(라인당 1레코드). 텍스트라 diff 친화적이고, append가 순수 추가 diff가 된다.
- **파티셔닝**: `data/<dataset>/YYYY/MM/DD.jsonl`. 하나의 거대 파일을 매번 다시 쓰지 않아 git 비대화를 막는다.
- **금지**: SQLite/Parquet 바이너리를 git에 커밋(통째로 재저장되어 history 폭증). 분석용 스냅샷이 필요하면 release asset으로 분리.
- **멱등 dedup**: 파티션 쓰기 전 해당 파일의 `idempotency_key`를 읽어 중복 제외.
- **비대화 제어**: 날짜 파티션이 1차 방어. 추후 월별 롤업·history squash로 보완.

---

## 9. 스케줄링

- **공개 repo** 사용 → Actions 무료 분 무제한.
- **cron은 best-effort** — 정시(`0 * * * *`)는 고부하라 지연·드롭 위험. **오프셋 사용**(예: `23 * * * *`).
- **cadence별 워크플로**:
  - `collect-hourly.yml` → 뉴스·장중 핑(가벼운 것)
  - `collect-daily.yml` → 가격 EOD·공시·거시
  - `collect-weekly.yml` / `collect-monthly.yml` → 저빈도 거시·정리
- **커밋백 패턴**(Simon Willison git-scraping):
  ```bash
  git config user.name "mimir-bot"
  git add -A
  git commit -m "data: $(date -u +%FT%TZ)" || exit 0   # 변경 없으면 클린 종료
  git pull --rebase
  git push
  ```
  `permissions: contents: write` + `concurrency:` 그룹으로 중첩 실행 방지.
- **60일 비활성 자동 비활성화**: 매 실행이 커밋하므로 자동으로 살아있는다.

---

## 10. 백필 전략

`python -m mimir.backfill --source stooq --since 2018-01-01` 형태의 별도 진입점.

- **가격**: Stooq 대량 CSV로 수년치 EOD를 한 번에 적재.
- **거시**: FRED/ECOS 장기 시계열.
- **공시**: EDGAR/DART 과거 목록.
- 백필은 같은 정규화·저장 경로를 타되, 대량이므로 스로틀을 더 보수적으로 적용한다.
- 효과: S4(과거패턴)를 정주행 누적을 기다리지 않고 착수할 수 있다.

---

## 11. 에러 처리 & 합법성 강제

- **소스 격리**: 소스별 try/except. 한 소스 실패가 나머지를 막지 않는다.
- **무침묵**: 실패는 매니페스트에 기록하고, 부분 실패 시 워크플로를 비제로로 종료(로그에 노출).
- **재시도**: 일시적 네트워크 오류는 지수 백오프 제한 재시도. 4xx(인증/한도)는 즉시 실패로 기록.
- **합법성**: `legal_status`/`rate_limit`을 메타로 들고 스로틀러가 강제. EDGAR엔 연락처 UA, Naver엔 출처표기. GRAY 소스는 정책 스위치로 차단 가능.

---

## 12. 시크릿 관리

- 필요한 키: `DART_API_KEY`, `FRED_API_KEY`, `ECOS_API_KEY`, (옵션) `NAVER_CLIENT_ID/SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- 로컬: `.env`(gitignore). CI: **GitHub Actions Secrets** → `${{ secrets.* }}`.
- `settings.py`가 시작 시 *필요한* 키 존재를 검증한다(없으면 해당 소스 비활성 + 매니페스트 경고). 절대 커밋 금지.

---

## 13. 설정

- **`config/watchlist.yaml`** — 추적할 종목. 예:
  ```yaml
  us: [AAPL, MSFT, NVDA, SPY]
  kr: ["005930", "000660", "035720"]   # 종목코드
  ```
- **`config/sources.yaml`** — 소스 on/off·파라미터. GRAY 소스 정책 스위치.

---

## 14. 최소 가시성 (가치 확인 경로)

레이어가 죽은 코드가 되지 않도록, 첫 스펙에서도 "동작을 본다":

- `reports/status.html` — 데이터셋별 마지막 수집·누적 건수·최근 실패.
- 텔레그램 핑(옵션) — 봇 토큰이 있으면 수집 요약 한 줄.

이 둘은 S3에서 풍부한 리포트/다이제스트로 대체·확장한다.

---

## 15. 테스트 전략 (TDD, 80%+)

- **단위** — 어댑터는 **녹화된 픽스처**(`tests/fixtures/`)로 네트워크 없이 파싱·정규화 검증(`responses`로 HTTP 모킹).
- **스토리지** — append 라운드트립, 멱등 dedup, 날짜 파티션 경로 규칙.
- **오케스트레이터** — cadence별 due 소스 선택, 소스 격리(한 소스 실패가 나머지 진행을 막지 않음).
- **스키마** — envelope 검증 성공/실패 케이스.
- **통합/E2E** — 실제 네트워크 호출은 별도 마크로 분리(CI에서 선택 실행, 평소 스킵).
- RED → GREEN → REFACTOR 순서. 외부 ToS·한도에 의존하는 부분은 모킹으로 결정론 유지.

---

## 16. 기술 스택 & 툴링

- **언어/런타임**: Python 3.14 (asdf `.tool-versions`로 핀)
- **핵심 의존성(Increment 1)**: `requests`, `pydantic`, `pyyaml`. 이후 증분: `feedparser`, `pykrx`, `OpenDartReader`, `fredapi` 등
- **개발 툴**: `pytest`, `responses`(HTTP 모킹), `ruff`(lint/format), `mypy`(타입), `coverage`
- **패키징**: `pyproject.toml`, src-layout 권장
- **CI**: GitHub Actions에서 lint+type+test 게이트

---

## 17. 완료 기준 (Acceptance Criteria)

1. `python -m mimir.collect --cadence daily`가 로컬에서 끝까지 동작하고, `data/`에 정규화 JSONL을 append하며, 재실행 시 중복이 생기지 않는다(멱등).
2. 최소 3개 소스(예: Stooq, SEC EDGAR, DART)가 어댑터로 동작하고 픽스처 단위테스트를 통과한다.
3. 한 소스를 강제로 실패시켜도 나머지 수집이 진행되고, 매니페스트에 실패가 기록된다.
4. `reports/status.html`이 데이터 현황을 보여준다.
5. cadence별 Actions 워크플로가 수집 후 데이터를 repo에 커밋한다(공개 repo, concurrency 가드, 시크릿 미커밋).
6. 백필 진입점이 과거 가격 이력을 적재한다.
7. 커버리지 80%+ , `ruff`·`mypy` 통과.
8. 소스별 `legal_status`/`rate_limit`이 메타데이터로 강제되고, GRAY 소스(pykrx)는 설정으로 off할 수 있다.

---

## 18. 가정 & 오픈 퀘스천

- **가정**: repo는 공개로 둔다(무료 분 무제한). 비공개 전환 시 2,000분/월 한도를 고려.
- **가정**: 초기 워치리스트는 소수 종목으로 시작하고 점진 확장.
- **오픈**: 일부 API 일일 한도(DART ~20k, ECOS ~100k)는 구현 시 콘솔에서 재확인.
- **오픈**: Finnhub 등 per-symbol API 보강은 Stooq로 부족할 때 추가(현재는 보류, YAGNI).

---

## 19. 미래 확장 seam

- 어댑터 패턴 덕에 소스 추가는 `sources/`에 파일 하나 + 레지스트리 등록으로 끝난다.
- 정규화 envelope가 S2(분석)의 입력 계약이 된다. S2는 dataset/symbol/ts로 질의한다.
- S5(매매)를 위해, 분석이 발행할 "시그널"도 같은 envelope 패턴을 따르되 별도 dataset(`signals`)으로 분리한다. 실행 엔진은 이를 읽기 전용 소비한다.
