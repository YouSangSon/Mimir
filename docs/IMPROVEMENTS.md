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
- [x] **R1 news_volume 실데이터 무력(해소 진행)**: 티커가 공식 피드 헤드라인에 안 나오는 문제를 줄이기 위해 `analysis.news.aliases` 회사명 alias matcher, 보수적 기본 alias 데이터셋, `sources.rss.feeds[].symbol` 기반 종목별 RSS feed 매칭을 추가. `news_volume`과 opt-in `llm_sentiment`가 같은 matcher를 사용한다. 두 뉴스 시그널은 발행일(`ts`)이 아니라 수집일(`captured_at`) 기준 윈도우로 오늘과 baseline을 읽는다. 짧은 티커/한글 인접어 오매칭은 단어 경계로 방지.
- [x] **R2b DART/SEC 페이지네이션·백필**: DART는 `total_page` 루프(MAX_PAGES 가드)로 전 페이지 순회; SEC는 `ctx` 주입 + 백필 시 `files[]` 아카이브 페이징 + `filingDate >= since` 필터(50건 캡 제거). (Inc.3)
- [x] **P-H1 DataReader 전체 재스캔**: → `JsonlStore.read_window(since,until)` 파티션 프루닝(S2 핫패스), S4는 PRICES 1회 읽어 symbol 버킷팅(load-once). (실행당 캐시는 `run.py` 단일 프로세스로 부분 완화)
- [x] **E1 재생성 데이터 stale 잔존**: insights/historical/evaluation이 당일 재실행에서 0건 또는 더 작은 결과를 만들면 이전 레코드가 남아 다음 리포트에 노출될 수 있었다. → `JsonlStore.replace_partition(dataset, day, records)`를 추가하고 세 엔진이 당일 파티션을 전체 교체한다. 빈 결과면 파티션 파일을 삭제한다.
- [x] **E2 평가 루프 미실행**: production pipeline이 `collect -> analyze -> history -> deliver`만 실행해 `evaluation` scorecard가 갱신되지 않았다. → `mimir.run`에 `run_evaluate`를 `history` 뒤, `deliver` 앞에 추가하고 daily report가 같은 실행의 `Dataset.EVALUATION`을 읽는다.

## 🟡 MEDIUM
- [x] **429 처리**: `http_get`이 429를 치명적 4xx로 처리(백오프 없음). → 429/503 재시도 가능 처리(가능하면 `Retry-After`).
- [x] **SEC UA 검증**: 기본 UA(@ 없음)는 403 가능. → `build_sources`에서 UA에 `@` 없으면 경고 로그.
- [x] **cadence 미이스케이프 + deliver --cadence choices 없음**: → `html.escape(cadence)` + `choices`.
- [x] **백필 격리/매니페스트**: `backfill`에 레코드별 `NormalizationError` 가드 추가(skip+count). 성공 실행은 `fetched/stored/invalid`를 manifest에 기록하고, 실패 실행은 `ok=false` manifest를 남긴 뒤 예외를 다시 던진다.
- [x] **ECOS 페이지네이션**: `list_total_count` 기반 인덱스 페이지 루프(MAX_PAGES 가드)로 100행 캡 제거. (Inc.3)
- [x] **dedup first-write-wins (재생성 데이터셋)**: insights/historical/evaluation은 `replace_partition`으로 당일 파티션을 전체 교체한다. 같은 날 재실행은 최신 계산만 남기고, 빈 결과면 이전 결과를 삭제한다.
- [x] **거시 개정 last-write-wins**: FRED/ECOS 같은 `macro` source는 같은 관측 key가 다시 오면 최신 레코드로 교체한다. `prices`, `filings`, `news`는 기존 first-write-wins를 유지한다.
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
- [x] **README CLI 계약과 package scripts 불일치**: README가 `mimir.collect` 계열 실행 파일을 문서화했지만 `pyproject.toml`에는 console script가 없었다. → 통합 `mimir <subcommand>`와 dotted aliases(`mimir.collect`, `mimir.analyze`, `mimir.doctor` 등)를 `[project.scripts]`로 등록하고 기존 `python -m mimir.X` 경로는 유지.
- [x] **README `.env` 자동 로드 계약과 CLI 경로 불일치**: README는 `.env`가 runtime에 자동 로드된다고 설명했지만 `collect`/`run`/`deliver`/`backfill` CLI가 `os.environ`을 직접 넘겨 `.env` 로드를 우회했다. → runtime `env` 인자를 선택값으로 바꾸고 CLI는 기본 `env=None` 경로를 사용한다. 명시 `env={...}` 테스트와 실제 환경변수 우선 정책은 유지한다.
- [x] **`sources.yaml` CLI 검증 drift**: `collect`/`run`/`backfill`은 malformed `sources.yaml`을 `[mimir] invalid sources.yaml:`로 보고했지만 `analyze`는 raw pydantic 오류를 노출하고 `deliver`/`dashboard`는 typo를 무시할 수 있었다. → `mimir.config.load_validated_sources_config()`로 CLI 경계 검증을 공유하고, `analyze`/`deliver`/`dashboard`도 같은 friendly message + exit code 1로 실패한다. runtime/downstream `ValidationError`는 오분류하지 않도록 catch 범위를 유지한다.
- [x] **`mimir doctor` 설정 검증 누락**: `doctor`는 운영 점검 명령인데도 `--config-dir`의 `sources.yaml` schema 오류를 보지 않고 데이터 점검을 계속할 수 있었다. → `doctor_cli.main()`도 `load_validated_sources_config()`를 먼저 호출하고, malformed config에서는 HTML 파일을 쓰기 전에 `[mimir] invalid sources.yaml:`와 exit code 1로 실패한다.
- [x] **news_volume 단어경계 + alias 매칭 + captured window + 종목별 RSS feed**: 짧은 티커 오매칭을 제거하고, 기본 watchlist용 보수적 회사명 alias와 `analysis.news.aliases` 사용자 alias를 지원한다. 공식 피드 ticker 부재는 기본/사용자 alias로 일부 완화된다. 사용자가 종목별 RSS feed를 알고 있으면 `sources.rss.feeds[].symbol`로 연결할 수 있다. 뉴스 신호의 today/baseline은 `captured_at` 기준으로 읽어 늦게 수집된 발행 기사를 실행일 분석에 포함한다.
- [x] **설정 기반 시리즈/피드 + macro series 단일 진실원**: FRED/ECOS series·RSS feeds를 `sources.yaml`의 `sources:` 블록으로 노출하고, macro rate-series와 doctor cadence를 `mimir/core/macro_series.py`로 통합. `analysis.macro_regime.rate_series`로 수집 대상과 분석 해석 대상을 분리한다.
- [x] **GH Actions Node20 deprecation**: `actions/checkout@v4`·`setup-python@v5`가 Node20 세대 action이라 2026-06-16 Node24 기본 전환에 걸릴 수 있었다. → `checkout@v6`·`setup-python@v6`로 올리고, `tests/test_workflows.py`가 workflow action major를 검증한다.
- [x] **pykrx 일시 실패 재시도**: `pykrx`는 `BaseSource`를 직접 쓰지 않는 library source라 공통 `http_get` 정책을 상속하지 못했다. → OHLCV 호출 경계에 throttle + 짧은 지수 backoff retry를 추가하고, 소진 시 `FetchError`로 ticker와 마지막 오류를 manifest에 남긴다. GRAY·선택 소스 정책은 유지한다.
- [x] **backfill preflight failure manifest**: registered source가 secret/package gate 때문에 fetch 전에 제외되면 manifest 없이 `SystemExit`만 남았다. → built-in `SourceSpec`에 static `SourceMeta`를 연결하고, backfill이 registered-but-unavailable source를 `ok=false` manifest로 기록한다. Unknown source id는 cadence를 알 수 없어 argument error로 유지한다.
- [x] **doctor HTML report**: C1 데이터 닥터 spec은 선택 후속으로 `--html`과 3언어 라벨을 남겼지만 CLI는 text/JSON만 지원했다. → `mimir doctor --html <path> --lang en|ko|zh`가 standalone HTML을 쓰고, 기존 stdout 형식과 exit code는 유지한다.
- [x] **README health metadata drift**: README 3종의 tests badge와 상태 표가 실제 pytest 수집 개수보다 뒤처질 수 있었다. → `tests/test_readme_docs.py`가 `pytest --collect-only` 결과와 README badge/table 값을 비교하고, 개선 카탈로그의 최신 완료 ID도 회귀 테스트로 고정한다.
- [x] **captured news window 반복 스캔 완화**: `DataReader.read_captured_window()`가 같은 분석 실행에서 NEWS 전체를 여러 번 다시 읽을 수 있었다. → `DataReader`가 `captured_at.date()`별 인메모리 index를 만들고 `JsonlStore.revision`이 바뀔 때만 다시 만든다. 늦게 수집된 뉴스 포함 의미와 `data/news/YYYY/MM/DD.jsonl` 저장 구조는 유지한다.
- [x] **SEC ticker CIK map 오류 표면**: `ticker_cik_map_path`가 가리키는 로컬 파일이 없거나 JSON이 깨졌을 때 low-level 예외가 그대로 노출될 수 있었다. → missing file, 읽기 실패, invalid JSON, non-object JSON을 path가 포함된 설정 오류로 정규화한다.
- [x] **SEC ticker CIK map entry 오류 위치**: 큰 `company_tickers.json` 파일에서 개별 entry가 깨지면 어느 entry를 고쳐야 하는지 알기 어려웠다. → non-object entry, invalid ticker, missing/invalid `cik_str` 오류에 파일 경로와 entry key를 포함한다.
- [x] **SEC ticker CIK map CLI 오류 표면**: loader가 만든 설정 오류가 `collect`/`run`/`backfill` CLI에서는 raw `ValueError` traceback으로 노출될 수 있었다. → source build 단계의 `ValueError`를 `SourcesConfigError`로 감싸고 CLI는 `[mimir] invalid sources.yaml:` 형식으로 출력한다.
- [x] **SEC ticker CIK map missing ticker 경로 누락**: 로컬 `company_tickers.json`을 성공적으로 읽은 뒤에도, 없는 ticker lookup 오류는 어떤 파일을 참조했는지 알려주지 않았다. → loader가 반환하는 dict-compatible mapping에 path metadata를 보존하고, missing ticker 오류가 loader-backed map에서만 `... in <path>`를 포함하도록 정리한다.
- [x] **SEC ticker CIK CLI 경로 계약 테스트 누락**: R1m이 lookup 오류 메시지에 mapping file 경로를 넣었지만, `collect`/`run`/`backfill` CLI 테스트는 여전히 `ticker MSFT` 부분문자열만 확인해 운영자-facing stderr 계약을 고정하지 못했다. → 세 CLI 회귀 테스트가 `[mimir] invalid sources.yaml:` prefix와 `company_tickers.json`의 정확한 `str(path)`를 함께 요구하도록 강화했다.
- [x] **설정 가드레일 (watchlist schema + LLM headline cap)**: `watchlist.yaml`은 schema 검증이 없어 `us: AAPL` 같은 스칼라가 글자 단위(`["A", "A", "P", "L"]`)로 풀릴 수 있었고, `llm_sentiment_max_headlines`는 정수 타입만 검증해 `0`·음수·`51`도 받았다. → `_WatchlistConfig`(`extra="forbid"`, `list[StrictStr]`)가 비-매핑 최상위·비-문자열·공백 symbol을 거부하고 공백을 제거하며, `load_watchlist()`는 path 포함 `WatchlistConfigError`로 실패하고 CLI는 `[mimir] invalid watchlist.yaml:`로 보고한다. `llm_sentiment_max_headlines`는 두 모델 모두에서 `Field(ge=1, le=50)`로 제한한다. 기본값과 저장 계약은 유지한다. ([tech spec](decisions/tech-spec/config/CFG3_config_guardrails_tech_spec_2026_06_18.md))
- [x] **기존 계약 characterization 커버리지 (COV1)**: 이미 옳지만 테스트로 고정되지 않은 계약들을 characterization 테스트로 박았다. ECOS 비월간 cycle(`Q`/`A`)이 stable idempotency_key와 올바른 partition day(분기 첫날·연초)를 만드는지, 빈/결측 `DATA_VALUE` row를 skip하는지, `_resolve_sources_config_paths()`가 절대 `ticker_cik_map_path`를 그대로 통과시키는지, price_momentum이 거래량 결측 시 surge 보정을 건너뛰고 크래시하지 않는지를 고정한다. 새 동작·네트워크 호출·저장 계약 변경은 없다(모든 테스트는 추가 즉시 GREEN). 함께 검토한 LLM signal weight YAML 노출은 spec이 생성자 기본값으로만 약속했고 다른 시그널과 일관성을 깨므로 보류했다([catalog §6](architecture/improvement-catalog.md)).
- [x] **`mimir evaluate` 미사용 `--config-dir` 인자 제거**: `evaluate` CLI는 저장된 insights/prices만 읽으므로 config를 읽지 않는데도 `--config-dir`을 선언하고 README 3종이 이를 문서화해, 아무 동작도 하지 않는 인자를 약속하는 doc↔code 불일치였다(D1/ENV1/CFG1과 같은 "정직한 CLI" 계열). → `evaluate.py`에서 인자를 제거하고 README 3종 사용법에서도 뺀다. 파이프라인은 `run_evaluate()` 함수를 직접 호출하므로 영향 없고, 테스트도 이 인자를 쓰지 않는다.
- [x] **리포트 i18n 패리티 drift guard (I18N1)**: `mimir/report/i18n.py`의 `t()`는 키가 없으면 영어로, placeholder가 어긋나면 값 누락·`KeyError`로 빠질 수 있었지만, en/ko/zh 패리티를 잡는 테스트가 없어 번역 drift 시 조용히 영어가 새거나 렌더가 깨질 수 있었다(trilingual 리포트 약속 위반). → `tests/report/test_i18n.py`가 (1) 모든 언어의 키 집합 동일, (2) 키별 `{placeholder}` 집합 동일, (3) `t()` 문서화된 fallback(unknown lang→en, unknown key→key)을 고정한다. DOCHEALTH류 "조용한 문서/UI drift 금지" 계열이며 런타임 코드 변경은 없다.
- [x] **SignalResult 경계 검증 완성 (A4 후속)**: A4 타입드 페이로드는 저장 데이터셋 모델을 `frozen+extra="forbid"`로 만들었지만, INSIGHTS 페이로드에 중첩 저장되어 매 read마다 재검증되는 `SignalResult`만 `extra="forbid"` 없이 남고 `weight`도 무경계였다. 그래서 drift 키가 조용히 버려지고, 음수 weight가 `scorer.score()`의 부호 있는 방향 합산(`DIRECTION_SIGN*strength*confidence*weight`)을 뒤집을 수 있었다. → `SignalResult`에 `extra="forbid"`와 `weight: Field(ge=0.0)`를 추가하고 회귀 테스트(`tests/analysis/signals/test_signal_result.py`)를 더했다. weight는 점수가 아니라 곱셈자이므로 상한은 두지 않는다. 저장 레이아웃·기존 record 무변경.
- [x] **리포트 HTML helper 중복 제거**: `_esc`(html escape)·HTML `_stars`·`SEVERITY_COLOR`가 `daily_report`/`dashboard`/`doctor_html`에 복사돼 있어 severity 색이 조용히 어긋날 drift 리스크가 있었다(이미 `DIRECTION_COLOR`는 공유 중이라 패턴 선례 존재). → 공유 모듈 `mimir/report/html.py`(`esc`/`stars`/`SEVERITY_COLOR`)로 통합. plain-text digest의 `_stars`(빈 별 없음)와 단일 사용 `_SEVERITY_RANK`는 그대로 둔다. 순수 리팩터로 렌더 동작·테스트 무변경.
- [x] **스코어러 중립 시그널 희석 제거 (C1 후속)**: `score()`가 `net`(별점·방향의 기반)을 *전체* weight로 나눠, 항상 NEUTRAL인 활동 시그널(`news_volume`)이 실제 방향 시그널의 확신(별점)을 희석했다(같은 강세 근거가 활동 시그널 추가만으로 5★→3★). C1 원칙("별점=방향 확신")과 어긋난다. → `net`을 *방향* 시그널 weight로만 정규화한다. 중립 시그널은 계속 `attention`(활동량)에 기여하고, `|net|≤1`은 유지된다. 회귀 테스트로 "중립 추가가 방향 별점을 낮추지 않음"을 고정. 이는 모든 insight 별점에 영향하는 제품 변경이라 사용자 승인 후 적용했다.
- [x] **historical `triggered_today` 날짜 미검증**: `HistoricalEngine.run()`이 `triggered_today=(len(series)-1) in idxs`로 *최신 bar가 이벤트인지*만 봤다. price series는 `until=as_of`로 잘리므로 주말·공휴일·가격 미수집 실행에서는 `series[-1].day < as_of`가 되어, 과거 이벤트가 "오늘 발생(Triggered today)" 배지를 잘못 달 수 있었다. → `triggered_today=(len(series)-1) in idxs and series[-1].day == as_of`로 날짜를 함께 검증한다. evaluation engine은 같은 감사에서 look-ahead·hit-rate·edge·min_n·partition replacement가 모두 정확함을 증거와 함께 확인했다(무결함). 회귀 테스트로 event-on-as_of=True, as_of-after-last-bar=False를 고정.
- [x] **SEC ticker→CIK mapping refresh (off-by-default 구현)**: R1i는 운영자가 직접 내려받은 로컬 `company_tickers.json`만 읽었다(다운로드·freshness 없음). catalog §6 보류 항목을 [설계문서](superpowers/specs/2026-06-19-sec-ticker-cik-map-cache-design.md) 후, 프로젝트의 off-by-default 외부호출 규율(B2 LLM seam과 동일)로 구현했다. `sources.rss.sec.ticker_cik_map_refresh.enabled`(기본 false)일 때만 동작: TTL 게이트(`max_age_hours`), conditional GET(ETag/If-Modified-Since→304 생략), fair-access User-Agent(`MIMIR_SEC_USER_AGENT`), 실패·비-JSON·비-object 시 기존 파일 fallback. resolver는 그대로 네트워크 0 — refresh는 `build_sources` prep step에서만 일어난다. 기본 경로는 네트워크 0, 저장 계약 무변경. 6개 회귀 테스트(disabled/TTL/download/304/failure/non-object)는 녹화 fake로 무네트워크.
- [x] **captured-date scan 측정 계기 (C2 unblock 선행)**: persistent index(C2) 보류의 unblock 조건은 "scan 재빌드가 병목이라는 *측정*"인데 그 측정 수단이 없었다. → `DataReader._captured_date_index`가 재빌드할 때 `records`/`days`/`elapsed_ms`를 DEBUG 로그(`mimir.storage.reader`)로 남긴다. 이로써 보류 항목이 "측정 부재로 막힘"에서 "계기 완비, 임계 도달 시 착수"로 전진한다. 한 reader revision당 1회만 scan/log됨을 회귀 테스트(records=3, days=2, rebuild 1회)로 고정. 저장 계약·동작 무변경(로그만 추가).

## 후속 후보
- Captured-date persistent index나 보조 파티션은 아직 보류한다. 현재 구현은 한 `DataReader` 안에서 NEWS 전체 스캔을 한 번으로 줄이는 인메모리 cache다. 데이터가 수년치로 커지고, `read_captured_window()` 재빌드 자체가 병목이라는 측정이 나오면 on-disk index schema, rebuild command, stale-index fallback을 별도 설계한다.
- Provider별 RSS discovery는 SEC 일부만 안전하게 해소됐다. `sources.rss.sec.company_filings`는 사용자가 CIK 또는 ticker를 명시하면 SEC Company Search Atom feed URL을 조립한다. `sources.rss.sec.ticker_cik_map_path`는 사용자가 제공한 SEC `company_tickers.json` 로컬 파일로 ticker를 10자리 CIK로 정규화한다. `sources.rss.catalogs`의 `sec_structured_*` id는 SEC가 공개한 broad SEC/XBRL feed를 정적으로 고른다. 이 feed들은 symbol-specific feed가 아니다. 남은 작업은 SEC mapping file live download/cache, SEC 외 provider, HTML RSS link crawling, vendor URL pattern inference처럼 provider 정책과 ToS 검토가 더 필요한 범위다.

## 안티-파인딩(확인됨, 수정 불필요)
volume-surge는 현재 봉을 자기 평균에서 제외(정확) · forward_returns는 의도된 event-study(누수 아님) · 가격/공시/거시 ts는 자정 UTC라 파티션 안정 · idempotency_key는 소스 prefix로 교차충돌 없음 · 시크릿은 env만·.env gitignore·.env.example 플레이스홀더 · 워치리스트 심볼 URL 주입 안전 · 워크플로 커맨드 인젝션 없음 · 레이어 그래프는 순환 없음 · 파일 크기 건전.

> 2026-06-16 정정: 예전에는 재생성 데이터셋의 `append(overwrite=True)`를 충분한 last-write-wins로 봤지만, 빈 결과/축소 결과에서 stale 레코드가 남는 반례가 확인됐다. 이 항목은 안티-파인딩에서 제거하고 E1로 수정 완료했다.
