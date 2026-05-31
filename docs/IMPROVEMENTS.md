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
- [ ] **R1 news_volume 실데이터 무력**: 티커가 공식 피드 헤드라인에 안 나옴 + 짧은 티커 오매칭 + 발행일 윈도우. → 회사명 alias 맵 + 단어경계 매칭 + `captured_at` 윈도우 또는 종목별 피드. (LLM 시그널로 대체 가능 — 하이브리드 후속) **[후속: 설계 필요]**
- [x] **R2b DART/SEC 페이지네이션·백필**: DART는 `total_page` 루프(MAX_PAGES 가드)로 전 페이지 순회; SEC는 `ctx` 주입 + 백필 시 `files[]` 아카이브 페이징 + `filingDate >= since` 필터(50건 캡 제거). (Inc.3)
- [x] **P-H1 DataReader 전체 재스캔**: → `JsonlStore.read_window(since,until)` 파티션 프루닝(S2 핫패스), S4는 PRICES 1회 읽어 symbol 버킷팅(load-once). (실행당 캐시는 `run.py` 단일 프로세스로 부분 완화)

## 🟡 MEDIUM
- [x] **429 처리**: `http_get`이 429를 치명적 4xx로 처리(백오프 없음). → 429/503 재시도 가능 처리(가능하면 `Retry-After`).
- [x] **SEC UA 검증**: 기본 UA(@ 없음)는 403 가능. → `build_sources`에서 UA에 `@` 없으면 경고 로그.
- [x] **cadence 미이스케이프 + deliver --cadence choices 없음**: → `html.escape(cadence)` + `choices`.
- [x] **백필 격리/매니페스트**: `backfill`에 레코드별 `NormalizationError` 가드 추가(skip+count). (매니페스트는 후속)
- [x] **ECOS 페이지네이션**: `list_total_count` 기반 인덱스 페이지 루프(MAX_PAGES 가드)로 100행 캡 제거. (Inc.3)
- [x] **dedup first-write-wins (재생성 데이터셋)**: insights/historical은 `append(overwrite=True)`로 last-write-wins(당일 재실행=최신). 거시 개정(FRED/ECOS, orchestrator append-only)은 후속.
- [x] **MIN_OCCURRENCES가 horizon별 n 미보장**: `summarize(min_n=)` + 엔진 `MIN_HORIZON_N=2`로 horizon별 최소 표본 게이트.

## 🟢 LOW / 유지보수
- [x] **macro_regime 인플레이스 정렬**: `series.sort()` → `sorted()` (불변성 규칙).
- [x] **테스트 공백 보강**: XSS 이스케이프 테스트, DART 비-000 상태, http_get 재시도 소진, telegram non-200/예외, orchestrator `invalid` 카운팅.
- [x] **DataReader 레이어링**: `analysis/reader.py` → `storage/reader.py` 이동(레이어 역전 해소).
- [x] **`_load_yaml` 4중복 + watchlist 폴백 중복**: → `mimir/config.py`(load_yaml/load_watchlist/load_sources_config)로 통합.
- [x] **워크플로 4중복**: `_pipeline.yml`(workflow_call) + 4개 thin caller로 ~190줄 중복 제거.
- [x] **단일 파이프라인 진입점**: `mimir/run.py run_pipeline`(collect→analyze→history→deliver 단일 프로세스).
- [x] **news_volume 단어경계 매칭**: 짧은 티커 오매칭 제거(`\b{ticker}\b`). 단 공식 피드 ticker 부재/발행일 윈도우는 alias·종목별 피드·LLM 시그널로 후속.
- [ ] **설정 기반 시리즈/피드**: FRED/ECOS series·RSS feeds·macro RATE_SERIES 하드코딩, adapter/signal 간 시리즈 식별자 중복. → `sources.yaml`에 노출 + 단일 상수 모듈. **[후속]**
- [ ] **pykrx 타임아웃/재시도 없음**(BaseSource 미사용). GRAY라 LOW. **[후속]**
- [ ] **GH Actions Node20 deprecation**: `actions/checkout@v4`·`setup-python@v5`가 Node20(2026-06-16 Node24 강제). 동작엔 문제 없음 — 안정 신버전 나오면 범프. **[후속, LOW]**

## 후속(Increment 3 후보)
SEC `files[]` 백필 + DART/ECOS 페이지네이션(H-C), 거시 개정 last-write-wins(orchestrator per-dataset 정책), news alias/종목별 피드 또는 LLM 시그널, 설정 기반 series/feeds, pykrx 타임아웃, 매니페스트 백필.

## 안티-파인딩(확인됨, 수정 불필요)
volume-surge는 현재 봉을 자기 평균에서 제외(정확) · forward_returns는 의도된 event-study(누수 아님) · 가격/공시/거시 ts는 자정 UTC라 파티션 안정 · idempotency_key는 소스 prefix로 교차충돌 없음 · 시크릿은 env만·.env gitignore·.env.example 플레이스홀더 · 워치리스트 심볼 URL 주입 안전 · 워크플로 커맨드 인젝션 없음 · 레이어 그래프는 순환 없음 · 파일 크기 건전.
