# Mimir 개선 백로그 (S1–S4 감사, 2026-05-31)

4-차원 병렬 리뷰(정확성·견고성·아키텍처/성능·보안/테스트) 종합. `[x]`는 `feat/s1-s4-hardening`에서 처리됨, `[ ]`는 후속.

## 🔴 CRITICAL
- [x] **SEC-1 ECOS 키 유출**: ECOS가 키를 URL 경로에 넣고, `http_get`이 에러에 URL을 포함 → 매니페스트/status.html/CI/repo 커밋으로 유출. → `http_get`이 에러 메시지에서 자격증명을 레다크션. (`base.py`, `ecos.py`)
- [x] **C1 ⭐별점 방향성 미반영**: `max(abs(net),attention)==attention`이라 stars가 활동량만 반영. → `stars=방향 확신(abs(net))`, `attention`을 별도 필드로 분리. 중립이면 저별점. (`scorer.py`, `schema.py`, `daily_report.py`)

## 🟠 HIGH
- [x] **R2 텔레그램 미보호**: `send_ping`이 네트워크 예외 시 실행 크래시 + 토큰 URL 노출. → `try/except requests.RequestException → False`.
- [x] **Orch 어댑터 mid-generator 예외**: `sec_edgar`/`dart`가 누락 필드에 인덱싱/브래킷 접근 → 소스 배치 전체 손실. → `.get()` + skip.
- [x] **H3 RSS `ts=now` 폴백**: 발행일 없는 항목이 dedup 무력화·뉴스량 부풀림. → 발행일 없으면 skip.
- [x] **H2 과거패턴 look-ahead**: `price_series`가 `as_of` 무시. → `until=as_of` 전달 + `triggered_today`를 as_of 기준으로.
- [x] **R1 news_volume 실데이터 무력(부분 해소)**: 티커가 공식 피드 헤드라인에 안 나오는 문제를 줄이기 위해 `analysis.news.aliases` 회사명 alias matcher를 추가. `news_volume`과 opt-in `llm_sentiment`가 같은 matcher를 사용한다. 짧은 티커/한글 인접어 오매칭은 단어 경계로 방지. 남은 한계: `captured_at` 윈도우, 종목별 feed, 기본 alias 사전은 후속.
- [x] **R2b DART/SEC 페이지네이션·백필**: DART는 `total_page` 루프(MAX_PAGES 가드)로 전 페이지 순회; SEC는 `ctx` 주입 + 백필 시 `files[]` 아카이브 페이징 + `filingDate >= since` 필터(50건 캡 제거). (Inc.3)
- [x] **P-H1 DataReader 전체 재스캔**: → `JsonlStore.read_window(since,until)` 파티션 프루닝(S2 핫패스), S4는 PRICES 1회 읽어 symbol 버킷팅(load-once). (실행당 캐시는 `run.py` 단일 프로세스로 부분 완화)
- [x] **E1 재생성 데이터 stale 잔존**: insights/historical/evaluation이 당일 재실행에서 0건 또는 더 작은 결과를 만들면 이전 레코드가 남아 다음 리포트에 노출될 수 있었다. → `JsonlStore.replace_partition(dataset, day, records)`를 추가하고 세 엔진이 당일 파티션을 전체 교체한다. 빈 결과면 파티션 파일을 삭제한다.
- [x] **E2 평가 루프 미실행**: production pipeline이 `collect -> analyze -> history -> deliver`만 실행해 `evaluation` scorecard가 갱신되지 않았다. → `mimir.run`에 `run_evaluate`를 `history` 뒤, `deliver` 앞에 추가하고 daily report가 같은 실행의 `Dataset.EVALUATION`을 읽는다.

## 🟡 MEDIUM
- [x] **429 처리**: `http_get`이 429를 치명적 4xx로 처리(백오프 없음). → 429/503 재시도 가능 처리(가능하면 `Retry-After`).
- [x] **SEC UA 검증**: 기본 UA(@ 없음)는 403 가능. → `build_sources`에서 UA에 `@` 없으면 경고 로그.
- [x] **cadence 미이스케이프 + deliver --cadence choices 없음**: → `html.escape(cadence)` + `choices`.
- [x] **백필 격리/매니페스트**: `backfill`에 레코드별 `NormalizationError` 가드 추가(skip+count). (매니페스트는 후속)
- [x] **ECOS 페이지네이션**: `list_total_count` 기반 인덱스 페이지 루프(MAX_PAGES 가드)로 100행 캡 제거. (Inc.3)
- [x] **dedup first-write-wins (재생성 데이터셋)**: insights/historical/evaluation은 `replace_partition`으로 당일 파티션을 전체 교체한다. 같은 날 재실행은 최신 계산만 남기고, 빈 결과면 이전 결과를 삭제한다. 거시 개정(FRED/ECOS, orchestrator append-only)은 후속.
- [x] **MIN_OCCURRENCES가 horizon별 n 미보장**: `summarize(min_n=)` + 엔진 `MIN_HORIZON_N=2`로 horizon별 최소 표본 게이트.
- [x] **HTML lang attribute 주입 가능성**: `sources.yaml`의 `lang`이 `<html lang="...">` 속성에 그대로 들어갔다. → `normalize_lang()`으로 `en|ko|zh`만 허용하고 나머지는 `en`으로 정규화.
- [x] **시그널 점수 범위 미검증**: `SignalResult.strength/confidence`와 `HeadlineVerdict.confidence`가 주석으로만 0..1을 약속했다. → pydantic `Field(ge=0, le=1)`로 경계 검증.
- [x] **JsonlStore since-only window 하한 무시**: `read_window(since=...)`가 fallback scan에서 하한을 적용하지 않았다. → `since`와 `until`을 모두 레코드 날짜 필터에 적용.

## 🟢 LOW / 유지보수
- [x] **macro_regime 인플레이스 정렬**: `series.sort()` → `sorted()` (불변성 규칙).
- [x] **테스트 공백 보강**: XSS 이스케이프 테스트, DART 비-000 상태, http_get 재시도 소진, telegram non-200/예외, orchestrator `invalid` 카운팅.
- [x] **DataReader 레이어링**: `analysis/reader.py` → `storage/reader.py` 이동(레이어 역전 해소).
- [x] **`_load_yaml` 4중복 + watchlist 폴백 중복**: → `mimir/config.py`(load_yaml/load_watchlist/load_sources_config)로 통합.
- [x] **워크플로 4중복**: `_pipeline.yml`(workflow_call) + 4개 thin caller로 ~190줄 중복 제거.
- [x] **단일 파이프라인 진입점**: `mimir/run.py run_pipeline`(collect→analyze→history→evaluate→deliver 단일 프로세스).
- [x] **news_volume 단어경계 + alias 매칭**: 짧은 티커 오매칭을 제거하고, `analysis.news.aliases`로 회사명 alias를 설정할 수 있게 했다. 공식 피드 ticker 부재는 설정 alias로 일부 완화된다. 발행일/captured_at 윈도우와 종목별 feed는 후속.
- [x] **설정 기반 시리즈/피드 + macro series 단일 진실원**: FRED/ECOS series·RSS feeds를 `sources.yaml`의 `sources:` 블록으로 노출하고, macro rate-series와 doctor cadence를 `mimir/core/macro_series.py`로 통합. `analysis.macro_regime.rate_series`로 수집 대상과 분석 해석 대상을 분리한다.
- [ ] **pykrx 타임아웃/재시도 없음**(BaseSource 미사용). GRAY라 LOW. **[후속]**
- [ ] **GH Actions Node20 deprecation**: `actions/checkout@v4`·`setup-python@v5`가 Node20(2026-06-16 Node24 강제). 동작엔 문제 없음 — 안정 신버전 나오면 범프. **[후속, LOW]**

## 후속(Increment 3 후보)
SEC `files[]` 백필 + DART/ECOS 페이지네이션(H-C), 거시 개정 last-write-wins(orchestrator per-dataset 정책), 종목별 news feed 또는 기본 alias 데이터셋, pykrx 타임아웃, 매니페스트 백필.

## 안티-파인딩(확인됨, 수정 불필요)
volume-surge는 현재 봉을 자기 평균에서 제외(정확) · forward_returns는 의도된 event-study(누수 아님) · 가격/공시/거시 ts는 자정 UTC라 파티션 안정 · idempotency_key는 소스 prefix로 교차충돌 없음 · 시크릿은 env만·.env gitignore·.env.example 플레이스홀더 · 워치리스트 심볼 URL 주입 안전 · 워크플로 커맨드 인젝션 없음 · 레이어 그래프는 순환 없음 · 파일 크기 건전.

> 2026-06-16 정정: 예전에는 재생성 데이터셋의 `append(overwrite=True)`를 충분한 last-write-wins로 봤지만, 빈 결과/축소 결과에서 stale 레코드가 남는 반례가 확인됐다. 이 항목은 안티-파인딩에서 제거하고 E1로 수정 완료했다.
