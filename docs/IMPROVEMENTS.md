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
- [ ] **R2b DART/SEC 페이지네이션·백필**: DART는 시장 전체 100건만(워치리스트 누락); SEC는 `backfill_since` 무시 + 50건 캡(`files[]` 미사용). → DART는 corp_code별 조회 또는 `total_page` 루프; SEC는 `ctx` 주입 + `files[]` 페이징. **[후속: 소스 리워크]**
- [ ] **P-H1 DataReader 전체 재스캔**: 매 호출 전 파티션 재파싱. S2 O(M·N), S4 O(M²·N). → (a) `since/until`로 파티션 경로 프루닝, (b) S4 `price_series`는 load-once/symbol-group, (c) 실행당 read 캐시. **[후속: 저장/리더 리팩터]**

## 🟡 MEDIUM
- [x] **429 처리**: `http_get`이 429를 치명적 4xx로 처리(백오프 없음). → 429/503 재시도 가능 처리(가능하면 `Retry-After`).
- [x] **SEC UA 검증**: 기본 UA(@ 없음)는 403 가능. → `build_sources`에서 UA에 `@` 없으면 경고 로그.
- [x] **cadence 미이스케이프 + deliver --cadence choices 없음**: → `html.escape(cadence)` + `choices`.
- [ ] **백필 격리/매니페스트 없음**: `backfill`이 레코드별 가드·매니페스트 없음. → orchestrator 경로 재사용 또는 가드 추가. **[후속]**
- [ ] **ECOS 페이지네이션**: 100행 캡(일간/장기 백필 손실). → `list_total_count` 루프. **[후속]**
- [ ] **dedup first-write-wins**: 같은 키 다른 payload(거시 개정·당일 인사이트 갱신) 무시. → 개정 가능 데이터셋은 last-write-wins(captured_at 기준) 또는 키에 리비전. **[후속: 정책 결정]**
- [ ] **MIN_OCCURRENCES가 horizon별 n 미보장**: h=20 중앙값이 n=1~2일 수 있음. → `summarize`에서 horizon별 최소 n 게이트. **[후속]**

## 🟢 LOW / 유지보수
- [x] **macro_regime 인플레이스 정렬**: `series.sort()` → `sorted()` (불변성 규칙).
- [x] **테스트 공백 보강**: XSS 이스케이프 테스트, DART 비-000 상태, http_get 재시도 소진, telegram non-200/예외, orchestrator `invalid` 카운팅.
- [ ] **DataReader 레이어링**: `analysis/`에 있는 저장 관심사 → `storage/`로 이동. **[후속]**
- [ ] **`_load_yaml` 4중복 + watchlist 폴백 중복**: → `mimir/config.py`로 통합. **[후속]**
- [ ] **워크플로 4중복**: `collect-*.yml` 거의 동일 → `workflow_call` 재사용. **[후속]**
- [ ] **단일 파이프라인 진입점 부재**: collect→analyze→history→deliver가 YAML에만. → `mimir/run.py run_pipeline` + 실행당 read 캐시. **[후속]**
- [ ] **설정 기반 시리즈/피드**: FRED/ECOS series·RSS feeds·macro RATE_SERIES 하드코딩, adapter/signal 간 시리즈 식별자 중복. → `sources.yaml`에 노출 + 단일 상수 모듈. **[후속]**
- [ ] **pykrx 타임아웃/재시도 없음**(BaseSource 미사용). GRAY라 LOW. **[후속]**

## 안티-파인딩(확인됨, 수정 불필요)
volume-surge는 현재 봉을 자기 평균에서 제외(정확) · forward_returns는 의도된 event-study(누수 아님) · 가격/공시/거시 ts는 자정 UTC라 파티션 안정 · idempotency_key는 소스 prefix로 교차충돌 없음 · 시크릿은 env만·.env gitignore·.env.example 플레이스홀더 · 워치리스트 심볼 URL 주입 안전 · 워크플로 커맨드 인젝션 없음 · 레이어 그래프는 순환 없음 · 파일 크기 건전.
