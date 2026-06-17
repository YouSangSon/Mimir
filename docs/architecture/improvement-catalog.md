# Mimir 발전 카탈로그 — 확장성·견고성·심화 (2026-06-13)

> **상태**: Increment 1–5 구현 완료 + 2026-06-16 hardening/A2/A3/A3b/A3c/R1a/R1b/R1c/R1d/R1e/R1f-SEC/R1g-SEC-STRUCTURED/MR1/C3/OPS1 구현 완료
> **목적**: S1–S4가 완성된 코드베이스에서 "원래 스코프 이상으로 더 확장성 있고, 개선·발전할 수 있는 점"을 식별하고, 각 항목을 **지금 구현 / 지금 설계(spec) / 보류**로 분류한다.
> **선행**: [로드맵](roadmap.md) · [개선 백로그](../IMPROVEMENTS.md)

---

## 0. 분류 기준 — "추적 가능성(traceability)" 단일 질문

건강한 코드베이스에서 "개선 항목 찾기"는 자칫 *스코프 제조기*가 된다. 그래서 모든 후보에 단 하나의 판별 질문을 적용한다:

> **이 항목은 *이미 존재하는 프로젝트 약속*(백로그 항목 · 로드맵 단계 · README가 한 약속)으로 추적되는가, 아니면 순수 신규(net-new)인가?**

- **추적됨 → 지금 구현.** 약속을 지키는 일이므로 YAGNI에 위배되지 않는다.
- **신규(가치 높음) → 지금 *설계*.** 엄밀한 spec + 보류 근거(ADR)가 산출물이다. 코드를 지르지 않는다.
- **신규(가치 낮음/시기상조) → 보류.** 근거와 함께 명시만 한다.

이 분류는 [ADR-0001](adr/0001-incremental-extensibility-and-deferral.md)에 결정으로 박제했다.

---

## 1. 한눈에 보기

| ID | 항목 | 차원 | 추적성 | 결정 | 산출물 |
|---|---|---|---|---|---|
| **A1** | 설정 기반 시리즈·피드 (FRED/ECOS series, RSS feeds) | 확장성 | 백로그 + README 약속 | **✅ 구현 완료 (Increment 1)** | 코드 + 테스트(144) |
| **A4** | 데이터셋별 타입드 페이로드 스키마 (`dict[str,Any]` 제거) | 견고성 | 신규 | **✅ 구현 완료 (Increment 2)** | 코드 + 테스트(293) · [spec](../superpowers/specs/2026-06-13-typed-payload-design.md) |
| **A2** | 시리즈 식별자 단일 진실원 (macro_regime ↔ 어댑터) | 확장성 | 백로그 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-macro-series-registry-design.md) |
| **A3** | 선언적 소스 등록 (`SourceSpec` built-in table) | 아키텍처 | README 약속(부분) | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-declarative-source-registration-design.md) |
| **A3b** | 외부 source plugin entry point (`mimir.sources`) | 확장성 | A3 보류 항목 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-source-entry-points-design.md) |
| **A3c** | 외부 source plugin 설정 namespace (`sources.plugins.<source_id>`) | 확장성 | A3b 보류 항목 | **✅ 구현 완료 (2026-06-17)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-17-plugin-settings-namespace-design.md) |
| **B1** | 시그널 백테스트·평가 하네스 (사후수익 적중률) | 분석심화 | 신규(최고가치) | **✅ 구현 완료 (Increment 4 + 리포트 합류)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-13-signal-backtest-design.md) |
| **B2** | LLM 뉴스 감성 시그널 (news_volume 대체, 하이브리드) | 분석심화 | 로드맵 + 백로그 R1 | **✅ seam 구현 (Increment 5, off-by-default)** | 코드 + 테스트 |
| **R1a** | 뉴스 mention alias matcher (`analysis.news.aliases`) | 분석품질 | 백로그 R1 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-news-mention-alias-design.md) |
| **R1b** | 뉴스 captured window (`captured_at` 기준 today/baseline) | 분석품질 | 백로그 R1 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-news-captured-window-design.md) |
| **R1c** | 기본 news alias 데이터셋 (`analysis.news.use_default_aliases`) | 분석품질 | 백로그 R1 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-default-news-aliases-design.md) |
| **R1d** | Symbol-tagged RSS feeds (`sources.rss.feeds[].symbol`) | 분석품질/확장성 | 백로그 R1 후속 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md) |
| **R1e** | 정적 RSS feed catalog (`sources.rss.catalogs`) | 분석품질/확장성 | R1d 보류 항목 | **✅ 구현 완료 (2026-06-17)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-17-rss-feed-catalog-design.md) |
| **R1f-SEC** | SEC EDGAR company filing RSS provider | 분석품질/확장성 | R1f 보류 항목의 안전한 일부 | **✅ 구현 완료 (2026-06-17)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md) |
| **R1g-SEC-STRUCTURED** | SEC structured disclosure RSS catalog | 분석품질/확장성 | R1e/R1f-SEC 후속 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md) |
| **R1h-SEC-TICKER** | SEC company filing RSS ticker input | 분석품질/확장성 | R1f-SEC 후속 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-18-sec-rss-ticker-input-design.md) |
| **MR1** | 거시 개정 저장 정책 (`macro` last-write-wins) | 견고성/운영 | 백로그 MEDIUM | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-macro-revision-policy-design.md) |
| **H1** | 재생성 데이터 stale 제거 + pipeline scorecard 갱신 | 견고성/운영 | B1 후속 + 리뷰 발견 | **✅ 구현 완료 (2026-06-16 hardening)** | `replace_partition`, `run_evaluate`, daily report scorecard |
| **BF-MANIFEST** | 백필 실행 manifest 기록 | 견고성/운영 | 백로그 MEDIUM | **✅ 구현 완료 (2026-06-16)** | backfill success/failure run log |
| **C1** | 데이터 신선도·품질 닥터 (`mimir doctor`) | 운영 | "무음 실패 금지" 약속 | **✅ 구현 완료 (Increment 3)** | 코드 + 테스트(179) |
| **OPS1** | Scheduled dashboard publication (`reports/dashboard.html`) | 운영가시성 | README + 현행 spec | **✅ 구현 완료 (2026-06-17)** | workflow + 테스트 + docs · [spec](../superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md) |
| **C2** | 파티션 인덱스 (git-as-DB rglob 스케일) | 성능 | 신규 | ⏸ 보류 | 본 문서 §6 |
| **C3** | pykrx retry/backoff 정책 | 견고성 | 백로그 LOW | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-pykrx-retry-policy-design.md) |
| **D1** | 통합 `mimir` CLI (console_scripts) | DX | 신규 | ⏸ 보류 | 본 문서 §6 |
| **D2** | GH Actions Node20→24 범프 | CI | 백로그 LOW | **✅ 구현 완료 (2026-06-16)** | workflow + 테스트 · [spec](../superpowers/specs/2026-06-16-github-actions-node24-design.md) |

🛠 = 코드 구현 · 📐 = 설계문서 · ⏸ = 보류(근거 명시)

---

## 2. 확장성 (Extensibility)

### A1. 설정 기반 시리즈·피드 — **지금 구현**

**증상.** 세 어댑터 모두 *생성자에 설정 인자를 이미 받지만*, `build_sources(settings)`가 인자 없이 생성해 **그 seam이 죽어 있다**:

| 어댑터 | 죽은 seam | 하드코딩 기본값 |
|---|---|---|
| `FredSource(series=)` | 미전달 | `DEFAULT_SERIES = ["DGS10","FEDFUNDS","CPIAUCSL"]` |
| `EcosSource(series=)` | 미전달 | `DEFAULT_SERIES = [EcosSeries("722Y001","M","0101000")]` |
| `RssSource(feeds=)` | 미전달 | `DEFAULT_FEEDS = [SEC press releases]` |

A1 이전에는 FRED 시리즈 하나를 추가하려면 **파이썬 코드를 고쳐야 했다.** README는 "소스 추가 = 파일 하나 + 등록"을 약속했지만 실제로는 *파일 + Settings 필드 + builder 분기 + 하드코딩 시리즈*가 필요했다. 이 격차가 확장성 천장이었다.

**근거(추적성).** 백로그 "설정 기반 시리즈/피드"(`IMPROVEMENTS.md` LOW) + README의 확장성 약속. 순수 신규가 아니라 *이미 설계됐으나 배선되지 않은* 기능.

**결정.** **Increment 1로 구현.** `config/sources.yaml`이 어댑터별 블록(`fred.series`/`ecos.series`/`rss.feeds`)을 선언하고, `build_sources(settings, config)`가 검증된 설정을 생성자에 전달한다. → 사용자가 YAML만으로 커버리지를 넓힌다. 상세: [config-driven 설계문서](../superpowers/specs/2026-06-13-config-driven-extensibility-design.md).

**불변식(테스트로 고정).** 설정 배선은 `idempotency_key` 포맷·파티션 레이아웃을 **바꾸지 않는다**. 빈/부재 설정은 **오늘의 기본값을 그대로 재현**한다. git-as-DB에서 키가 조용히 바뀌면 이미 커밋된 데이터가 고아가 되거나 중복된다 — 이 리팩터가 "저위험"에서 "고위험"으로 바뀌는 유일한 경로.

### A2. 시리즈 식별자 단일 진실원 — **구현 완료 (2026-06-16)**

이전 구현에서는 `MacroRegimeSignal.RATE_SERIES = {"FEDFUNDS","DGS10","722Y001.0101000"}`가 FRED/ECOS가 발행하는 시리즈 식별자를 **두 번째로** 하드코딩했다. A1로 사용자가 시리즈를 바꿔도 거시 시그널은 그것을 몰랐다. 이 결합은 **source→signal 경계를 가로지르므로**, A1보다 위험하고 별도 증분으로 처리했다.

**구현.** `mimir/core/macro_series.py`가 기본 FRED 시리즈, 기본 ECOS 시리즈, macro-regime rate-series, doctor macro cadence를 한 곳에서 제공한다. `FredSource`, `EcosSource`, `MacroRegimeSignal`, doctor expectation은 이 모듈을 읽는다. `sources.yaml`의 `analysis.macro_regime.rate_series`는 수집된 macro series 중 어떤 시리즈를 금리 regime 신호로 해석할지 명시한다. 수집 대상(`sources.fred/ecos.series`)과 분석 해석 대상(`analysis.macro_regime.rate_series`)은 분리되어, CPI처럼 수집은 하되 rate signal로 쓰면 안 되는 series를 안전하게 다룬다.

### A3. 선언적 소스 등록 — **구현 완료 (2026-06-16)**

`build_sources`의 `if settings.X_api_key:` 사다리는 `BUILTIN_SOURCE_SPECS` 테이블로 이동했다. 각 `SourceSpec`은 source id, 생성자, secret gate, optional package gate, 설치 힌트를 한 곳에 선언한다.

이 구현은 public `build_sources(settings, config=None)` 진입점을 유지한다. SEC EDGAR와 RSS는 keyless로 계속 생성되고, Stooq/DART/FRED/ECOS는 secret이 없으면 warning 후 skip된다. pykrx는 `importlib.util.find_spec("pykrx")` gate를 통과할 때만 생성된다.

### A3b. 외부 source plugin entry point — **구현 완료 (2026-06-16)**

A3는 내장 소스를 데이터화했지만, 외부 package가 source를 추가하려면 여전히 Mimir repo를 수정해야 했다. A3b는 `mimir.sources` entry-point group을 추가해 이 한계를 제거한다.

외부 package는 `SourceSpec` 객체 하나 또는 `tuple[SourceSpec, ...]`를 entry point로 노출한다. `build_sources()`는 built-in spec을 먼저 두고 plugin spec을 이름순으로 뒤에 붙인다. Plugin load 실패는 warning 후 skip하고, 잘못된 object type, source id 중복, `source.meta.id` 불일치는 `ValueError`로 실패한다. `Registry`가 맡는 cadence, GRAY, `disabled_ids` 필터링은 그대로 유지한다.

### A3c. 외부 source plugin 설정 namespace — **구현 완료 (2026-06-17)**

A3b는 외부 package가 source를 주입할 수 있게 했지만, plugin별 설정을 `sources.yaml`에 둘 안전한 자리가 없었다. `sources:` 전체를 열어 두면 built-in 설정 typo를 잡는 fail-fast 정책이 깨진다.

구현 후 plugin 설정은 `sources.plugins.<source_id>` 아래에 둔다. `source_id`는 `SourceSpec.id`와 같다. Core parser는 plugin block이 mapping인지 검증하고, raw dict를 `SourcesConfig.plugin_settings`에 보존한다. Plugin factory는 `cfg.parse_plugin_config("acme_news", AcmeNewsConfig)`처럼 자신이 소유한 pydantic 모델로 schema를 검증한다.

Matching `SourceSpec.id`가 없는 plugin config는 warning을 남긴다. `sources.plugins.rss`처럼 built-in source id를 plugin namespace에 쓰면 warning을 남긴다. Built-in source 설정은 계속 `sources.rss`, `sources.fred`, `sources.ecos` 같은 typed block을 쓴다.

---

## 3. 분석 심화 (Analytical depth)

### B1. 시그널 백테스트·평가 하네스 — **구현 완료**

Mimir는 시그널을 *발행*하지만, 그 시그널이 실제로 무언가를 예측하는지 **측정하지 않는다.** S4 event-study는 "과거에 이런 일이 있었다"를 보지만, "우리 인사이트의 과거 적중률"이라는 피드백 루프는 없다. 백테스트 하네스는 Mimir를 "시그널 발행"에서 "*검증된* 시그널 발행"으로 끌어올리고, 신뢰 가능한 S5(자동매매)의 토대가 된다. 분석/실행 분리 원칙 준수(읽기 전용). → [백테스트 설계문서](../superpowers/specs/2026-06-13-signal-backtest-design.md).

**구현(Increment 4 + 2026-06-16 hardening).** `mimir.evaluate`가 저장된 `insights`와 `prices`만 읽어 `evaluation` 데이터셋을 만든다. `mimir.run`은 `collect -> analyze -> history -> evaluate -> deliver` 순서로 실행해 리포트가 같은 실행에서 갱신된 scorecard를 읽는다. `daily_report`와 `dashboard`는 시그널 성적표를 표로 보여준다. 표본 부족으로 모든 버킷이 사라지면 `JsonlStore.replace_partition`이 당일 evaluation 파티션을 삭제해 오래된 scorecard가 남지 않는다.

### B2. LLM 뉴스 감성 시그널 — **seam 구현 완료 (off-by-default)**

로드맵은 "규칙 기반 → 하이브리드(LLM 후속)"를 명시하고, 백로그 R1은 `news_volume`이 실데이터에서 거의 무력함을 인정한다(공식 피드에 티커 부재). LLM 감성 시그널이 가장 큰 분석 가치다. **그러나** 유료 API 호출을 기본값으로 켜면 프로젝트의 **무료(free) 원칙**과 충돌한다. 따라서 *seam과 off-by-default 스캐폴드를 설계*하되 기본 파이프라인에서 유료 호출을 발생시키지 않는다(GRAY 소스와 동일한 토글 철학). → [LLM seam 설계문서](../superpowers/specs/2026-06-13-llm-sentiment-seam-design.md).

**구현(Increment 5).** `NewsSentimentSignal`과 classifier seam은 구현됐지만, 실제 LLM 호출은 `[llm]` extra, `ANTHROPIC_API_KEY`, `llm_sentiment_enabled: true`가 모두 맞을 때만 켜진다. 기본 pipeline은 여전히 무료 경로다.

### R1a. 뉴스 mention alias matcher — **구현 완료 (2026-06-16)**

공식 RSS feed는 제목에 티커를 잘 싣지 않는다. `news_volume`이 `AAPL` 같은 symbol만 찾으면 `Apple`이라고 쓰인 뉴스는 watchlist symbol과 연결되지 않는다.

`analysis.news.aliases`는 이 문제를 무료 경로에서 줄인다. 사용자가 `AAPL: ["Apple", "Apple Inc."]`처럼 회사명 alias를 선언하면 `NewsVolumeSignal`과 opt-in `LlmSentimentSignal`이 같은 matcher로 제목과 요약을 해석한다. Alias 설정만으로 LLM 호출이 켜지지는 않는다.

Matcher는 Unicode word boundary를 사용해 `A`가 `Apple` 안에서 매칭되거나 `삼성전자`가 `삼성전자우` 안에서 매칭되는 일을 막는다. Alias는 생성 시 tuple로 복사해 설정 dict/list가 나중에 mutate되어도 기존 signal 동작이 바뀌지 않는다.

R1c는 기본 watchlist의 핵심 symbol에 대해 보수적 기본 alias를 제공하고, 사용자가 `analysis.news.use_default_aliases: false`로 끌 수 있게 했다.

### R1b. 뉴스 captured window — **구현 완료 (2026-06-16)**

뉴스 레코드의 `ts`는 기사가 발행된 시간이고, `captured_at`은 Mimir가 그 기사를 저장한 시간이다. 기존 뉴스 시그널은 `ts` 날짜로 today와 baseline을 잘랐다. 그래서 어제 발행됐지만 오늘 처음 수집된 뉴스가 오늘 분석에서 빠질 수 있었다.

`DataReader.read_captured_window()`는 저장 파티션을 바꾸지 않고 `captured_at.date()`로 윈도우를 자른다. `NewsVolumeSignal`과 opt-in `LlmSentimentSignal`만 이 API를 사용한다. 가격, 공시, 거시 신호는 기존처럼 이벤트 날짜(`ts`) 기준 reader를 쓴다.

이 구현은 `read_all(Dataset.NEWS)` 후 필터링한다. JSONL 파티션은 여전히 `ts.date()` 기준이므로, `captured_at` 윈도우에 `read_window()` 파티션 프루닝을 쓰면 늦게 수집된 오래된 발행 기사를 읽기 전에 놓친다. 뉴스 데이터가 커지면 `captured_at` 보조 인덱스나 파티션을 별도 설계한다.

### R1d. Symbol-tagged RSS feeds — **구현 완료 (2026-06-16)**

Alias matcher는 뉴스 제목과 요약에 회사명이나 티커가 있을 때만 동작한다. 하지만 사용자가 이미 종목별 RSS feed URL을 알고 있으면, feed 자체가 symbol 관계를 말해준다.

`sources.rss.feeds[].symbol`은 이 관계를 설정으로 표현한다. `RssSource`는 symbol-tagged feed에서 온 record의 top-level symbol을 채운다. Symbol이 없는 feed는 기존 `rss:{link}` idempotency key를 유지하고, symbol이 있는 feed는 `rss:{symbol}:{link}` key를 쓴다. 그래서 같은 기사 URL이 여러 종목 feed에 나타나도 한쪽 symbol이 dedup으로 사라지지 않는다.

`NewsMentionMatcher`는 제목과 요약을 보기 전에 record symbol을 먼저 확인한다. `NewsVolumeSignal`과 opt-in `LlmSentimentSignal`이 같은 matcher를 쓰므로, 두 신호 모두 symbol-tagged RSS feed를 활용한다. 남는 한계는 feed URL 자동 탐색이다. Mimir는 아직 provider별 live endpoint discovery나 feed 추천을 제공하지 않는다.

### R1e. 정적 RSS feed catalog — **구현 완료 (2026-06-17)**

R1d는 운영자가 URL을 이미 알고 있을 때 강력하다. 하지만 SEC 같은 공식 feed도 매 환경에서 URL과 publisher, market을 반복해서 복사해야 했다. 이 반복은 작지만 운영 설정을 어긋나게 만든다.

`sources.rss.catalogs`는 검증된 공식 feed를 id로 고르게 한다. R1e 당시의 초기 내장 catalog id는 `sec_press_releases`였다. Resolver는 catalog id를 기존 `RssFeed` 객체로 확장하고, 네트워크를 호출하지 않는다.

Catalog feed는 manual `sources.rss.feeds`보다 먼저 붙는다. 같은 `(url, symbol)` 쌍이 두 번 나오면 실패한다. 같은 URL이라도 symbol이 다르면 서로 다른 종목 관계이므로 허용한다.

이 구현은 live discovery가 아니다. HTML scraping, vendor URL pattern 추측, SEC structured disclosure feed 추가는 별도 증분으로 분리했다. SEC Company Search Atom 조립은 아래 R1f-SEC에서 별도 처리한다.

### R1f-SEC. SEC EDGAR RSS provider — **구현 완료 (2026-06-17)**

R1f 전체 live discovery는 여전히 provider별 정책 검토가 필요하다. 하지만 SEC Company Search의 Atom feed는 공식 문서로 추적되고, 사용자가 CIK를 명시하면 URL을 크롤링 없이 조립할 수 있다.

구현 후 `sources.rss.sec.company_filings`는 CIK, optional symbol, optional form list를 받아 `browse-edgar?action=getcompany&output=atom` feed로 확장한다. Resolver는 네트워크를 호출하지 않는다. Fetch 시점에는 `RssSource`가 `MIMIR_SEC_USER_AGENT`를 `User-Agent` header로 보낸다.

R1h 전까지 남은 generic discovery 부채는 SEC ticker 입력 편의, SEC ticker→CIK 자동 조회, SEC 외 provider, HTML RSS link crawling, vendor URL pattern inference였다.

### R1g-SEC-STRUCTURED. SEC structured disclosure RSS catalog — **구현 완료 (2026-06-18)**

SEC는 structured disclosure submission을 위한 공식 RSS feed를 따로 제공한다. 이 feed들은 US GAAP/IFRS tagged filing, mutual fund risk/return filing, Inline XBRL filing, 전체 XBRL filing처럼 넓은 SEC/XBRL 범주를 다룬다.

구현 후 `sources.rss.catalogs`는 `sec_structured_usgaap`, `sec_structured_risk_return`, `sec_structured_inline_xbrl`, `sec_structured_all_xbrl`을 지원한다. Resolver는 기존 정적 catalog와 같은 방식으로 id를 `RssFeed(publisher="SEC", market="US")`로 확장한다. 네트워크를 호출하지 않고, SEC HTML을 크롤링하지 않으며, URL pattern도 추측하지 않는다.

이 네 feed는 broad SEC/XBRL feed다. 특정 ticker나 watchlist symbol 전용 feed가 아니므로 `symbol`을 붙이지 않는다. ticker→CIK 자동 조회와 watchlist 기반 SEC feed 자동 생성은 여전히 deferred item이다.

### R1h-SEC-TICKER. SEC company filing RSS ticker input — **구현 완료 (2026-06-18)**

SEC Company Search RSS는 현재 `browse-edgar?action=getcompany&output=atom` URL의 `CIK=` query parameter에 ticker token을 넣어도 Atom feed를 반환한다. 이번 증분은 그 편의 입력을 `sources.rss.sec.company_filings[].ticker`로 노출한다.

구현 후 각 SEC company filing 항목은 `cik` 또는 `ticker` 중 정확히 하나를 받아야 한다. `cik`는 기존처럼 10자리로 zero-pad하고, `ticker`는 공백 제거 후 대문자로 정규화하며 letters/digits/dot/hyphen token만 허용한다. Resolver는 여전히 네트워크를 호출하지 않는다. SEC mapping file을 다운로드하거나 cache하지 않고, watchlist 전체에서 feed를 자동 생성하지 않는다.

남은 generic discovery 부채는 SEC mapping file 기반 ticker→CIK 자동 조회·cache·ambiguity policy, SEC 외 provider, HTML RSS link crawling, vendor URL pattern inference다.

---

## 4. 견고성 (Robustness)

### A4. 타입드 페이로드 스키마 — **✅ 구현 완료 (Increment 2)**

`RawRecord.payload: dict[str, Any]`는 모든 다운스트림 시그널이 문자열 키(`payload["close"]`, `payload["value"]`)로 더듬게 한다. 스키마 드리프트가 조용히 실패한다. 데이터셋별 pydantic 페이로드 모델은 경계에서 드리프트를 잡는다. 가치 높으나 신규 → 설계. → [타입드 페이로드 설계문서](../superpowers/specs/2026-06-13-typed-payload-design.md).

**구현(Increment 2).** `mimir/core/payloads.py`에 데이터셋별 6개 모델(`PricePayload`/`FredMacroPayload`/`EcosMacroPayload`/`NewsPayload`/`SecFilingPayload`/`DartFilingPayload`, 모두 `frozen=True, extra="forbid"`) + 유니온 별칭 + 외부 디스패치(`PAYLOAD_BY_DATASET`/`parse_payload`, 봉투 `dataset` 기준). insights/historical/evaluation은 기존 `Insight`/`HistoricalInsight`/`BucketStat` 재사용(+`extra="forbid"`). `Record.payload`는 `Payload` 유니온(`model_validator(mode="before")`로 dict→모델 파싱), `RawRecord.payload`는 dict 유지. `JsonlStore` 직렬화 무변경 → 온디스크 JSONL 바이트 동일(오버라이트 재실행 git churn 0, 골든 round-trip으로 고정). 시그널은 내로잉 헬퍼로 타입드 접근. 닥터의 얕은 `check_payload_schema`는 경계 검증이 대체하여 제거.

### C1. 데이터 신선도·품질 닥터 — **구현 완료**

매니페스트는 *실행*을 기록하지만, "어제 가격 데이터가 비었다" 같은 *데이터 신선도*는 누구도 감시하지 않는다. `mimir doctor`는 워치리스트 대비 누락·정체(stale) 파티션과 스키마 이상을 플래그한다. "무음 실패 금지" 약속을 데이터 평면으로 확장. → [데이터 닥터 설계문서](../superpowers/specs/2026-06-13-data-doctor-design.md).

### OPS1. Scheduled dashboard publication — **구현 완료 (2026-06-17)**

`mimir.dashboard`는 저장된 데이터, 최신 manifest, doctor finding을 읽어 `reports/dashboard.html`을 만들 수 있었다. 하지만 reusable scheduled workflow는 `python -m mimir.run` 뒤 바로 `git add data reports`를 실행했다. 그래서 scheduled run이 일일 리포트와 status page는 커밋해도 최신 dashboard를 생성하지 않았다.

구현 후 `_pipeline.yml`은 `Run pipeline` 뒤, `Commit data + reports` 앞에서 `python -m mimir.dashboard --data-root data --reports-root reports`를 실행한다. Hourly, daily, weekly, monthly caller는 모두 같은 reusable workflow를 호출하므로 cadence별 중복 없이 dashboard publish 계약을 공유한다.

Doctor WARN/CRITICAL은 dashboard health table에 표시한다. 그러나 scheduled workflow에 `python -m mimir.doctor`나 `--strict` hard gate는 넣지 않는다. Existing `mimir.run` collect failure gate는 그대로 유지하고, doctor finding을 배포 차단 정책으로 쓰는 문제는 별도 설계로 분리한다.

### BF-MANIFEST. 백필 실행 manifest 기록 — **구현 완료 (2026-06-16)**

`collect`는 소스별 성공/실패를 manifest에 남겼지만, `backfill`은 과거 데이터를 대량으로 적재하면서 실행 로그를 남기지 않았다. 이 격차는 README의 "무침묵 실패" 약속과 백로그의 "매니페스트는 후속" 항목으로 추적된다.

구현 후 `run_backfill()`은 성공 실행에 `fetched`, `stored`, `invalid`를 기록한다. upstream fetch, normalize, store 단계에서 예외가 나면 `ok=false` manifest를 먼저 남긴 뒤 예외를 다시 던진다. 그래서 호출자는 기존처럼 비정상 종료를 보면서도, 저장소에는 실패 흔적이 남는다.

### MR1. 거시 개정 저장 정책 — **구현 완료 (2026-06-16)**

FRED와 ECOS는 같은 관측일의 값을 나중에 고칠 수 있다. 기존 저장 정책은 같은 `idempotency_key`를 다시 받으면 첫 값을 유지했다. 그래서 공식 기관이 금리나 통계 값을 개정해도 `MacroRegimeSignal`은 오래된 값을 계속 읽을 수 있었다.

구현 후 source 수집과 backfill은 같은 helper인 `append_overwrite_enabled(dataset)`로 저장 정책을 고른다. 현재 `Dataset.MACRO`만 overwrite append를 쓰고, `prices`, `filings`, `news`는 기존 first-write-wins를 유지한다. `JsonlStore.append(overwrite=True)`는 새 key와 교체된 key를 모두 `stored`에 반영한다. 그래서 macro 값이 실제로 바뀌면 manifest와 backfill 반환값도 변경을 드러낸다.

---

## 5. 증분 실행 순서 (Sequencing)

브레인스토밍 원칙 — *여러 독립 서브시스템은 분해하고, 첫 번째를 전체 사이클로 돌린다.* 한 spec/plan/branch에 5개 서브시스템을 묶으면 리뷰 불가능한 거대 변경이 된다.

```
Increment 1 (지금) ── 설정 기반 소스 척추 (A1)
   spec → plan → 구현(subagent-driven) → finish
        ▼
Increment 2 ── 타입드 페이로드 (A4)            ✅ 구현 완료 (Record.payload 유니온; 바이트 동일)
Increment 3 ── 데이터 닥터 (C1)               ✅ 구현 완료 (read-only `mimir doctor`)
Increment 4 ── 시그널 백테스트 하네스 (B1)   ✅ 구현 완료 (engine+CLI+pipeline+daily report scorecard)
Increment 5 ── LLM 감성 seam (B2)            ✅ seam 구현 (off-by-default)
Hardening ─── stale 재생성 데이터 제거 · lang 정규화 · SignalResult 범위 검증
A2 ───────── macro series registry · analysis.macro_regime.rate_series
A3 ───────── built-in source registry · SourceSpec construction table
A3b ──────── external source plugin entry points · mimir.sources
A3c ──────── source plugin settings namespace · sources.plugins.<source_id>
R1a ──────── news mention alias matcher · analysis.news.aliases
R1b ──────── news captured window · DataReader.read_captured_window
R1c ──────── default news aliases · analysis.news.use_default_aliases
R1d ──────── symbol-tagged RSS feeds · sources.rss.feeds[].symbol
R1e ──────── static RSS feed catalog · sources.rss.catalogs
R1f-SEC ─── SEC EDGAR company filing RSS provider
R1g-SEC-STRUCTURED ─ SEC structured disclosure RSS catalog
R1h-SEC-TICKER ─ SEC company filing RSS ticker input
D2 ───────── GitHub Actions Node24-compatible action majors
C3 ───────── pykrx retry/backoff · FetchError manifest surface
BF-MANIFEST ─ backfill success/failure manifest
OPS1 ─────── scheduled dashboard publication · reports/dashboard.html
MR1 ──────── macro revision storage policy · Dataset.MACRO last-write-wins
```

각 증분은 자기 spec → plan → 구현 → finish 사이클을 가진다. 본 카탈로그는 그 지도(map)다.

---

## 6. 보류 항목 — 근거 명시

| 항목 | 보류 근거 |
|---|---|
| **C2 파티션 인덱스** | `read_window` 파티션 프루닝이 이미 핫패스를 처리. 인덱스는 데이터가 수년 누적된 *뒤*의 최적화 — 지금은 시기상조(YAGNI). 신선도 닥터(C1)가 먼저 스케일 신호를 준다. |
| **D1 통합 CLI** | 순수 DX. 5개 `python -m mimir.X`는 동작에 문제없음. console_scripts entry-point는 좋지만 약속에 추적되지 않음 → 보류. |
| **R1f Generic provider RSS discovery** | R1f-SEC는 공식 SEC Company Search Atom URL 조립을 해결했고, R1g-SEC-STRUCTURED는 SEC의 broad XBRL feed catalog를 정적으로 추가했다. R1h-SEC-TICKER는 SEC Company Search RSS의 ticker token 입력을 추가했다. SEC mapping file 기반 ticker→CIK 조회·cache·ambiguity policy, SEC 외 provider, HTML RSS link crawling, vendor URL pattern inference는 provider 정책과 ToS 검토가 더 필요하다. |
| **D3 spec/ro드맵 번역** | 내부 설계문서는 KO-only 유지(백로그 결정). 사용자 문서(README ×3)는 이미 trilingual. |

---

## 7. 안티-발견 (확인됨, 손대지 않음)

건강한 코드베이스의 증거 — 다음은 검토했고 **고칠 것이 없다**:

- 레이어 그래프 순환 없음 · 파일 크기 건전(최대 ~150줄) · mypy strict 통과.
- `idempotency_key`는 소스 prefix로 교차충돌 없음 · 파티션은 자정 UTC라 안정.
- 시크릿은 env/`.env`(gitignore)만 · ECOS 키 URL 유출은 이미 레다크션 처리.
- `http_get` 429/5xx 재시도 + 4xx 빠른 실패 · 소스 격리(한 소스 실패가 전체를 멈추지 않음).
- CI와 수집 pipeline은 Node24 호환 `actions/checkout@v6`·`actions/setup-python@v6`를 사용하며, workflow guard 테스트가 major 회귀를 잡는다.
- `pykrx`는 GRAY·선택 소스 상태를 유지하면서 OHLCV 호출 실패를 짧게 재시도하고, 소진 시 `FetchError`로 manifest에 실패 원인을 남긴다.
- 재생성 데이터셋은 `replace_partition`으로 당일 파티션 전체 교체 · 가격/공시/뉴스 원천 데이터는 append-only · 거시 원천 데이터는 공식 개정값을 last-write-wins로 반영.
- 백필은 성공과 실패를 manifest에 기록한다. 실패는 기록 후 다시 예외를 던져 비정상 종료 신호를 유지한다.

**결론.** 본 작업은 *확장성 천장 제거 + 성숙기 피드백 루프 + 운영 가시성 강화*를 만드는 흐름이다. A3, A3b, A3c, R1a, R1b, R1c, R1d, R1e, R1f-SEC, R1g-SEC-STRUCTURED, MR1, D2, C3, BF-MANIFEST, OPS1까지 구현되었다. 남은 신규 아키텍처 부채는 generic provider RSS discovery다.
