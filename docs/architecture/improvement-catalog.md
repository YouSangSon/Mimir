# Mimir 발전 카탈로그 — 확장성·견고성·심화 (2026-06-13)

> **상태**: Increment 1–5 구현 완료 + 2026-06-16 hardening/A2/A3/A3b/A3c/AN1-SIGNAL-PLUGIN-ENTRYPOINTS/AN2-LLM-CLASSIFIER-CARDINALITY/AN3-ANALYSIS-PLUGIN-BUILTIN-GUARD/AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION/AN5-ANALYSIS-SIGNAL-SPECS-INJECTION/R1a/R1b/C2a-CAPTURED-NEWS-CACHE/R1c/R1d/R1e/R1f-SEC/R1g-SEC-STRUCTURED/R1h-SEC-TICKER/R1i-SEC-CIK/R1j-SEC-CIK-ERRORS/R1k-SEC-CIK-ENTRY-ERRORS/R1l-SEC-CIK-CLI-ERRORS/R1m-SEC-CIK-MISSING-PATH/R1n-SEC-CIK-CLI-PATH-CONTRACT/MR1/C3/OPS1/DCHTML/DOCHEALTH/ENV1/CFG1/CFG2/CFG3-CONFIG-GUARDRAILS/COV1-CONTRACT-COVERAGE/I18N1-PARITY-GUARD/BF-PREFLIGHT 구현 완료 + AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY 구현 완료 + R1o-SEC-WATCHLIST-FILING-FEEDS Draft
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
| **A1** | 설정 기반 시리즈·피드 (FRED/ECOS series, RSS feeds) | 확장성 | 백로그 + README 약속 | **✅ 구현 완료 (Increment 1)** | 코드 + 테스트 |
| **A4** | 데이터셋별 타입드 페이로드 스키마 (`dict[str,Any]` 제거) | 견고성 | 신규 | **✅ 구현 완료 (Increment 2)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-13-typed-payload-design.md) |
| **A2** | 시리즈 식별자 단일 진실원 (macro_regime ↔ 어댑터) | 확장성 | 백로그 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-macro-series-registry-design.md) |
| **A3** | 선언적 소스 등록 (`SourceSpec` built-in table) | 아키텍처 | README 약속(부분) | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-declarative-source-registration-design.md) |
| **A3b** | 외부 source plugin entry point (`mimir.sources`) | 확장성 | A3 보류 항목 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-source-entry-points-design.md) |
| **A3c** | 외부 source plugin 설정 namespace (`sources.plugins.<source_id>`) | 확장성 | A3b 보류 항목 | **✅ 구현 완료 (2026-06-17)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-17-plugin-settings-namespace-design.md) |
| **AN1-SIGNAL-PLUGIN-ENTRYPOINTS** | 외부 analysis signal plugin entry point (`mimir.analysis_signals`) + 설정 namespace (`analysis.plugins.<signal_id>`) | 확장성 | B2 후속 seam 명문화 | **✅ 구현 완료 (2026-06-23)** | 코드 + 테스트 · [spec](../decisions/tech-spec/analysis/AN1_signal_plugin_entrypoints_tech_spec_2026_06_23.md) |
| **AN2-LLM-CLASSIFIER-CARDINALITY** | LLM 감성 classifier verdict 수 검증 | 분석품질/견고성 | B2 구조화 출력 계약 | **✅ 구현 완료 (2026-06-23)** | 코드 + 테스트 · [spec](../decisions/tech-spec/analysis/AN2_LLM_classifier_cardinality_tech_spec_2026_06_23.md) |
| **AN3-ANALYSIS-PLUGIN-BUILTIN-GUARD** | `analysis.plugins`가 built-in signal id를 겨냥할 때 정확한 namespace warning | 운영/DX | AN1 plugin namespace 오용 방지 | **✅ 구현 완료 (2026-06-25)** | 코드 + 테스트 · [spec](../decisions/tech-spec/analysis/AN3_analysis_plugin_builtin_guard_tech_spec_2026_06_25.md) |
| **AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION** | signal `evaluate()` 예외를 signal/symbol 단위로 격리 | 견고성/운영 | AN1 plugin blast radius 축소 | **✅ 구현 완료 (2026-06-25)** | 코드 + 테스트 · [spec](../decisions/tech-spec/analysis/AN4_analysis_engine_signal_isolation_tech_spec_2026_06_25.md) |
| **AN5-ANALYSIS-SIGNAL-SPECS-INJECTION** | `build_signals(..., specs=...)` direct injection seam | 확장성/DX | AN1 entry point seam의 테스트·임베디드 사용성 | **✅ 구현 완료 (2026-06-25)** | 코드 + 테스트 · [spec](../decisions/tech-spec/analysis/AN5_analysis_signal_specs_injection_tech_spec_2026_06_25.md) |
| **AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY** | 잘못된 `Signal.evaluate()` 반환 타입을 scoring 전에 log+skip | 견고성/운영 | AN4/AN5 이후 plugin 반환 계약 blast radius 축소 | **✅ 구현 완료 (2026-06-25)** | [spec](../decisions/tech-spec/analysis/AN6_analysis_signal_result_boundary_tech_spec_2026_06_25.md) |
| **B1** | 시그널 백테스트·평가 하네스 (사후수익 적중률) | 분석심화 | 신규(최고가치) | **✅ 구현 완료 (Increment 4 + 리포트 합류)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-13-signal-backtest-design.md) |
| **B2** | LLM 뉴스 감성 시그널 (news_volume 대체, 하이브리드) | 분석심화 | 로드맵 + 백로그 R1 | **✅ seam 구현 (Increment 5, off-by-default)** | 코드 + 테스트 |
| **R1a** | 뉴스 mention alias matcher (`analysis.news.aliases`) | 분석품질 | 백로그 R1 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-news-mention-alias-design.md) |
| **R1b** | 뉴스 captured window (`captured_at` 기준 today/baseline) | 분석품질 | 백로그 R1 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-news-captured-window-design.md) |
| **C2a-CAPTURED-NEWS-CACHE** | captured news window 인메모리 cache | 성능/분석품질 | R1b 후속 스케일 gap | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../decisions/tech-spec/storage/C2a_captured_news_window_cache_tech_spec_2026_06_18.md) |
| **R1c** | 기본 news alias 데이터셋 (`analysis.news.use_default_aliases`) | 분석품질 | 백로그 R1 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-default-news-aliases-design.md) |
| **R1d** | Symbol-tagged RSS feeds (`sources.rss.feeds[].symbol`) | 분석품질/확장성 | 백로그 R1 후속 | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-symbol-tagged-rss-feeds-design.md) |
| **R1e** | 정적 RSS feed catalog (`sources.rss.catalogs`) | 분석품질/확장성 | R1d 보류 항목 | **✅ 구현 완료 (2026-06-17)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-17-rss-feed-catalog-design.md) |
| **R1f-SEC** | SEC EDGAR company filing RSS provider | 분석품질/확장성 | R1f 보류 항목의 안전한 일부 | **✅ 구현 완료 (2026-06-17)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-17-sec-edgar-rss-provider-design.md) |
| **R1g-SEC-STRUCTURED** | SEC structured disclosure RSS catalog | 분석품질/확장성 | R1e/R1f-SEC 후속 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-18-sec-structured-rss-catalog-design.md) |
| **R1h-SEC-TICKER** | SEC company filing RSS ticker input | 분석품질/확장성 | R1f-SEC 후속 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-18-sec-rss-ticker-input-design.md) |
| **R1i-SEC-CIK** | SEC ticker CIK local mapping lookup | 분석품질/확장성 | R1h 보류 항목의 안전한 일부 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../decisions/tech-spec/sources/R1i-SEC-CIK_sec_ticker_cik_map_tech_spec_2026_06_18.md) |
| **R1j-SEC-CIK-ERRORS** | SEC ticker CIK map file error surface | 견고성/DX | R1i 운영 오류 표면 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../decisions/tech-spec/sources/R1j-SEC-CIK-ERRORS_sec_ticker_cik_map_errors_tech_spec_2026_06_18.md) |
| **R1k-SEC-CIK-ENTRY-ERRORS** | SEC ticker CIK map entry error context | 견고성/DX | R1j 후속 운영 오류 표면 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../decisions/tech-spec/sources/R1k-SEC-CIK-ENTRY-ERRORS_sec_ticker_cik_map_entry_errors_tech_spec_2026_06_18.md) |
| **R1l-SEC-CIK-CLI-ERRORS** | SEC ticker CIK map CLI error surface | 운영/DX | R1j/R1k CLI 오류 표면 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../decisions/tech-spec/sources/R1l-SEC-CIK-CLI-ERRORS_sec_ticker_cik_map_cli_errors_tech_spec_2026_06_18.md) |
| **R1m-SEC-CIK-MISSING-PATH** | SEC ticker CIK map missing lookup path context | 운영/DX | R1i~R1l lookup-time 오류 표면 잔여 gap | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../decisions/tech-spec/sources/R1m-SEC-CIK-MISSING-PATH_sec_ticker_cik_missing_path_tech_spec_2026_06_18.md) |
| **R1n-SEC-CIK-CLI-PATH-CONTRACT** | SEC ticker CIK CLI stderr path contract | 운영/DX | R1m CLI 회귀 계약 고정 | **✅ 구현 완료 (2026-06-18)** | 테스트 + 문서 · [spec](../decisions/tech-spec/sources/R1n-SEC-CIK-CLI-PATH-CONTRACT_sec_ticker_cik_cli_path_contract_tech_spec_2026_06_18.md) |
| **R1o-SEC-WATCHLIST-FILING-FEEDS** | SEC watchlist company filing feed generation | 분석품질/확장성 | R1f generic discovery recheck의 SEC-only slice | **📐 Draft tech spec (2026-06-28)** | [spec](../decisions/tech-spec/sources/R1o-SEC-WATCHLIST-FILING-FEEDS_sec_watchlist_filing_feeds_tech_spec_2026_06_28.md) |
| **MR1** | 거시 개정 저장 정책 (`macro` last-write-wins) | 견고성/운영 | 백로그 MEDIUM | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-macro-revision-policy-design.md) |
| **H1** | 재생성 데이터 stale 제거 + pipeline scorecard 갱신 | 견고성/운영 | B1 후속 + 리뷰 발견 | **✅ 구현 완료 (2026-06-16 hardening)** | `replace_partition`, `run_evaluate`, daily report scorecard |
| **BF-MANIFEST** | 백필 실행 manifest 기록 | 견고성/운영 | 백로그 MEDIUM | **✅ 구현 완료 (2026-06-16)** | backfill success/failure run log |
| **BF-PREFLIGHT** | 백필 preflight failure manifest | 견고성/운영 | README + BF-MANIFEST 후속 | **✅ 구현 완료 (2026-06-18)** | registered unavailable source run log |
| **C1** | 데이터 신선도·품질 닥터 (`mimir doctor`) | 운영 | "무음 실패 금지" 약속 | **✅ 구현 완료 (Increment 3)** | 코드 + 테스트 |
| **DCHTML** | Doctor standalone HTML report | 운영가시성 | C1 선택 후속 수용 기준 | **✅ 구현 완료 (2026-06-18)** | HTML renderer + CLI + docs · [spec](../superpowers/specs/2026-06-18-doctor-html-report-design.md) |
| **DOCHEALTH** | README health metadata drift guard | 운영/DX | README 품질 badge 계약 | **✅ 구현 완료 (2026-06-18)** | README 수치 동기화 + 문서 회귀 테스트 · [spec](../decisions/tech-spec/docs/DOCHEALTH_readme_doc_health_tech_spec_2026_06_18.md) |
| **OPS1** | Scheduled dashboard publication (`reports/dashboard.html`) | 운영가시성 | README + 현행 spec | **✅ 구현 완료 (2026-06-17)** | workflow + 테스트 + docs · [spec](../superpowers/specs/2026-06-17-scheduled-dashboard-publication-design.md) |
| **ENV1** | Runtime `.env` autoload contract | 운영/DX | README 약속 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-18-dotenv-cli-autoload-design.md) |
| **CFG1** | `sources.yaml` CLI validation contract | 운영/DX | docs/reference config 약속 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-18-sources-config-cli-validation-design.md) |
| **CFG2** | `mimir doctor` sources config validation | 운영/DX | CFG1 후속 + doctor 운영 점검 계약 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../decisions/tech-spec/config/CFG2_doctor_sources_config_validation_tech_spec_2026_06_18.md) |
| **CFG3-CONFIG-GUARDRAILS** | watchlist schema 검증 + LLM headline cap 경계 | 견고성/비용 | CFG1/CFG2 후속 + 무료 원칙 비용 가드 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../decisions/tech-spec/config/CFG3_config_guardrails_tech_spec_2026_06_18.md) |
| **COV1-CONTRACT-COVERAGE** | 기존 계약 characterization 커버리지 (ECOS Q/A cycle·blank value, config 절대경로, price volume edge) | 견고성/테스트 | README/docs health guard가 추적하는 커버리지 게이트 + idempotency_key/partition 불변식 약속 | **✅ 구현 완료 (2026-06-19)** | 테스트 + 문서 (본 문서 §4) |
| **I18N1-PARITY-GUARD** | 리포트 i18n 키·placeholder 패리티 drift guard | 운영/DX | trilingual 리포트 약속 + DOCHEALTH류 drift guard 계약 | **✅ 구현 완료 (2026-06-19)** | 테스트 + 문서 (본 문서 §4) |
| **C2** | 파티션 인덱스 (git-as-DB rglob 스케일) | 성능 | 신규 | ⏸ 보류 | 본 문서 §6 |
| **C3** | pykrx retry/backoff 정책 | 견고성 | 백로그 LOW | **✅ 구현 완료 (2026-06-16)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-16-pykrx-retry-policy-design.md) |
| **D1** | 통합 `mimir` CLI (console_scripts) | DX | README 약속 | **✅ 구현 완료 (2026-06-18)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-18-cli-entrypoints-design.md) |
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

### AN1-SIGNAL-PLUGIN-ENTRYPOINTS. 외부 analysis signal plugin seam — **구현 완료 (2026-06-23)**

B2는 LLM 시그널 seam을 만들었지만, 그 seam을 repo 밖 package로 확장하는 공식 경로는 source 쪽 A3b/A3c만큼 문서화돼 있지 않았다. 결과적으로 "설치만 하면 시그널이 돈다"거나 "source plugin namespace를 재사용한다"는 잘못된 운영 추론이 생길 여지가 있었다.

구현 후 외부 signal plugin은 `mimir.analysis_signals` entry point와 `analysis.plugins.<signal_id>` opt-in namespace를 함께 사용한다. 설정 block이 비어 있으면 기본 `build_signals()` 경로는 entry point를 읽지 않으므로, installed package만으로는 import도 실행도 일어나지 않는다. Built-in 시그널이 먼저 실행되고, 설정된 plugin 시그널은 뒤에 append된다.

Plugin import가 깨지면 warning 후 skip한다. 반면 잘못된 object type, duplicate id, entry point/spec id mismatch, factory id mismatch는 loud failure다. 이 trust boundary는 source plugin과 동일하다. Signal plugin은 Mimir 프로세스 안에서 실행되고 sandbox가 없으므로, 설정·secret·저장 데이터 접근이 가능한 신뢰 코드로 취급해야 한다.

### AN2-LLM-CLASSIFIER-CARDINALITY. LLM classifier cardinality guard — **구현 완료 (2026-06-23)**

B2의 `HeadlineClassifier` 계약은 입력 headline마다 verdict 하나를 같은 순서로 반환하는 것이다. 그러나 구조화 출력 parser는 `verdicts`가 list인지까지만 검증하고, 입력 batch와 같은 길이인지는 런타임에서 확인해야 한다. 길이가 어긋난 batch를 평균내면 누락된 headline의 방향성을 숨기거나 존재하지 않는 headline을 score에 섞는 조용한 분석 오염이 된다.

구현 후 `LlmSentimentSignal.evaluate()`는 classifier 호출 직후 `len(verdicts) == len(texts)`를 검증한다. 불일치하면 warning에 actual/expected 개수와 symbol을 남기고 해당 symbol의 `llm_sentiment`만 `None`으로 생략한다. 정상 batch의 aggregate 수식, cap warning, classifier exception 격리, off-by-default LLM gate는 유지된다. retry, 새 네트워크 호출, 저장 schema, cache, Anthropic SDK 경로는 추가하지 않는다.

### AN3-ANALYSIS-PLUGIN-BUILTIN-GUARD. Built-in analysis plugin namespace warning — **구현 완료 (2026-06-25)**

AN1 이후 `analysis.plugins.<signal_id>`는 외부 analysis signal plugin 전용 opt-in namespace가 됐다. 그러나 사용자가 `analysis.plugins.news_volume`이나 `analysis.plugins.llm_sentiment`처럼 built-in signal id를 넣으면 generic missing plugin warning만 보여서, 실제 문제인 namespace 오용이 드러나지 않았다.

구현 후 builder는 unmatched plugin warning 전에 built-in analysis signal id를 먼저 분류한다. `news_volume`, `macro_regime`, `llm_sentiment`는 각각 `analysis.news`, `analysis.macro_regime`, `llm_sentiment_enabled` hint를 포함하고, 나머지 built-in signal은 built-in이 `analysis.plugins`를 읽지 않는다고 경고한다. Signal construction, entry point discovery, LLM off-by-default gate, retry/network/storage/cache 정책은 바꾸지 않는다.

### AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION. Analysis signal failure isolation — **구현 완료 (2026-06-25)**

AN1 이후 built-in과 외부 plugin signal은 같은 `Signal.evaluate(symbol, market, as_of, reader)` protocol로 engine에 들어온다. 이전 engine은 한 signal의 런타임 예외가 같은 symbol의 나머지 signal, 다음 symbol, 최종 `replace_partition()`까지 모두 막을 수 있었다. Plugin 신뢰 경계는 in-process trusted code이지만, 단일 signal/symbol 실패가 전체 analysis run을 중단하는 것은 운영 blast radius가 컸다.

구현 후 `AnalysisEngine.run()`은 각 signal 평가를 `Exception` 단위로 격리한다. 실패하면 `mimir.analysis.engine` logger가 signal id, watchlist market/symbol, traceback을 남기고 해당 결과만 생략한다. 같은 symbol의 다른 signal과 다음 symbol 평가는 계속되고, 모든 signal이 실패하거나 `None`이면 기존처럼 그 symbol의 insight는 생성하지 않는다. `KeyboardInterrupt`, `SystemExit` 같은 process-control 예외는 catch하지 않으며, retry/backoff, score formula, 저장 schema, plugin discovery 정책은 바꾸지 않는다.

### AN5-ANALYSIS-SIGNAL-SPECS-INJECTION. Analysis signal direct specs injection — **구현 완료 (2026-06-25)**

AN1의 entry point seam은 package 배포 단위에는 맞지만, 테스트·임베디드 호출자가 external signal specs를 주입하려면 private `_build_signals_from_specs()` helper에 의존해야 했다. Source builder 쪽 `build_sources(..., specs=...)`처럼 public injection seam이 있으면 packaging metadata 없이도 extension host가 결정론적으로 signal registry를 구성할 수 있다.

구현 후 `build_signals(..., specs=...)`는 entry point packaging 없이 external signal specs를 직접 주입하는 public seam이다. `specs`는 built-in replacement가 아니라 외부 plugin specs로만 해석한다. Built-in signal은 계속 먼저 생성되고, configured injected plugin signal만 그 뒤에 append된다. Injected spec도 `analysis.plugins.<signal_id>` 설정이 있어야 build되며, `specs is None`이면 기존 entry point discovery를 유지하고, `specs`가 제공되면 entry point를 읽지 않는다. Built-in id와 injected id가 중복되면 `ValueError`로 실패한다.

### AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY. Analysis signal result boundary — **구현 완료 (2026-06-25)**

AN4는 `Signal.evaluate()` 예외를 signal/symbol 단위로 격리했지만, Python `Protocol` annotation은 반환 타입을 런타임에서 강제하지 않는다. 외부 plugin이 `dict`, `str`, 임의 객체처럼 `None`도 `SignalResult`도 아닌 값을 반환하면 engine은 현재 그 값을 `score()`에 넘기고 scoring 단계에서 run을 중단할 수 있다.

설계된 AN6는 engine과 scorer 사이에 runtime boundary를 둔다. 반환값이 `None`이면 기존처럼 생략하고, `SignalResult`면 기존처럼 score에 넣고, 그 외 타입이면 signal id·watchlist market/symbol·반환 타입을 error log에 남긴 뒤 해당 signal 결과만 생략한다. Coercion, sandbox, scoring formula, plugin discovery, 저장 schema, retry/network 정책은 바꾸지 않는다.

### R1a. 뉴스 mention alias matcher — **구현 완료 (2026-06-16)**

공식 RSS feed는 제목에 티커를 잘 싣지 않는다. `news_volume`이 `AAPL` 같은 symbol만 찾으면 `Apple`이라고 쓰인 뉴스는 watchlist symbol과 연결되지 않는다.

`analysis.news.aliases`는 이 문제를 무료 경로에서 줄인다. 사용자가 `AAPL: ["Apple", "Apple Inc."]`처럼 회사명 alias를 선언하면 `NewsVolumeSignal`과 opt-in `LlmSentimentSignal`이 같은 matcher로 제목과 요약을 해석한다. Alias 설정만으로 LLM 호출이 켜지지는 않는다.

Matcher는 Unicode word boundary를 사용해 `A`가 `Apple` 안에서 매칭되거나 `삼성전자`가 `삼성전자우` 안에서 매칭되는 일을 막는다. Alias는 생성 시 tuple로 복사해 설정 dict/list가 나중에 mutate되어도 기존 signal 동작이 바뀌지 않는다.

R1c는 기본 watchlist의 핵심 symbol에 대해 보수적 기본 alias를 제공하고, 사용자가 `analysis.news.use_default_aliases: false`로 끌 수 있게 했다.

### R1b. 뉴스 captured window — **구현 완료 (2026-06-16)**

뉴스 레코드의 `ts`는 기사가 발행된 시간이고, `captured_at`은 Mimir가 그 기사를 저장한 시간이다. 기존 뉴스 시그널은 `ts` 날짜로 today와 baseline을 잘랐다. 그래서 어제 발행됐지만 오늘 처음 수집된 뉴스가 오늘 분석에서 빠질 수 있었다.

`DataReader.read_captured_window()`는 저장 파티션을 바꾸지 않고 `captured_at.date()`로 윈도우를 자른다. `NewsVolumeSignal`과 opt-in `LlmSentimentSignal`만 이 API를 사용한다. 가격, 공시, 거시 신호는 기존처럼 이벤트 날짜(`ts`) 기준 reader를 쓴다.

이 구현은 `read_all(Dataset.NEWS)` 후 필터링한다. JSONL 파티션은 여전히 `ts.date()` 기준이므로, `captured_at` 윈도우에 `read_window()` 파티션 프루닝을 쓰면 늦게 수집된 오래된 발행 기사를 읽기 전에 놓친다. C2a는 같은 `DataReader` 안에서 이 전체 scan을 한 번만 수행하도록 보강했다. 뉴스 데이터가 더 커져 cache rebuild 자체가 병목이 되면 `captured_at` persistent index나 보조 파티션을 별도 설계한다.

### C2a-CAPTURED-NEWS-CACHE. captured news window 인메모리 cache — **구현 완료 (2026-06-18)**

R1b 이후 `NewsVolumeSignal`은 한 symbol마다 today window와 baseline window를 각각 읽었다. LLM 감성 시그널을 켜면 같은 날짜의 NEWS scan이 한 번 더 생긴다. Watchlist가 커지면 한 분석 실행 안에서 같은 NEWS dataset을 반복해서 읽는 문제가 생긴다.

구현 후 `DataReader`는 dataset별 captured-date index를 메모리에 만든다. 첫 `read_captured_window(Dataset.NEWS, ...)` 호출은 기존처럼 `JsonlStore.read_all(Dataset.NEWS)`를 읽고, record를 `captured_at.date()`로 묶는다. 같은 `DataReader`의 다음 captured window 호출은 이 index를 재사용한다. `JsonlStore.revision`이 바뀌면 cache를 무효화해 같은 store 객체에 새 record가 append된 경우도 놓치지 않는다.

이 증분은 on-disk index가 아니다. 저장 경로, JSONL 직렬화, `idempotency_key`, NEWS partition 기준은 그대로 유지한다. 그래서 migration이나 rebuild command가 필요 없다.

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

이 네 feed는 broad SEC/XBRL feed다. 특정 ticker나 watchlist symbol 전용 feed가 아니므로 `symbol`을 붙이지 않는다. ticker→CIK 자동 조회는 R1i/R1j~R1n에서 구현됐고, watchlist 기반 SEC feed 자동 생성은 R1o Draft spec으로 승격했다.

### R1h-SEC-TICKER. SEC company filing RSS ticker input — **구현 완료 (2026-06-18)**

SEC Company Search RSS는 현재 `browse-edgar?action=getcompany&output=atom` URL의 `CIK=` query parameter에 ticker token을 넣어도 Atom feed를 반환한다. 이번 증분은 그 편의 입력을 `sources.rss.sec.company_filings[].ticker`로 노출한다.

구현 후 각 SEC company filing 항목은 `cik` 또는 `ticker` 중 정확히 하나를 받아야 한다. `cik`는 기존처럼 10자리로 zero-pad하고, `ticker`는 공백 제거 후 대문자로 정규화하며 letters/digits/dot/hyphen token만 허용한다. Resolver는 여전히 네트워크를 호출하지 않는다. SEC mapping file refresh/cache는 이후 `sources.rss.sec.ticker_cik_map_refresh.enabled`(기본 `false`)로 resolver 밖 build prep 단계에 off-by-default 구현됐다. watchlist 전체에서 feed를 자동 생성하지 않는다.

남은 generic discovery 부채는 generic live discovery, SEC 외 provider discovery, HTML RSS link crawling, vendor URL pattern inference다.

### R1i-SEC-CIK. SEC ticker CIK local mapping lookup — **구현 완료 (2026-06-18)**

R1h는 ticker token을 SEC Company Search RSS URL에 그대로 넣는 편의 입력을 제공했다. 그러나 같은 feed를 CIK로 명확히 만들고 싶으면 사용자가 직접 CIK를 찾아야 했다.

구현 후 `sources.rss.sec.ticker_cik_map_path`는 사용자가 내려받아 둔 SEC `company_tickers.json` 로컬 파일을 읽는다. `company_filings[].ticker`가 있고 mapping file에도 같은 ticker가 있으면 resolver는 URL의 `CIK=` 값을 10자리 CIK로 바꾼다. 같은 ticker가 서로 다른 CIK로 중복되면 ambiguous mapping으로 실패한다. 파일에 ticker가 없으면 feed를 조용히 ticker token으로 되돌리지 않고 실패한다.

이 증분은 resolver-time network call을 추가하지 않는다. 현재도 resolver는 네트워크를 호출하지 않는다. SEC mapping file refresh/cache는 이후 `sources.rss.sec.ticker_cik_map_refresh.enabled`(기본 `false`)로 off-by-default 구현됐다. 켜면 build 전에 TTL(`max_age_hours`) gate와 conditional GET으로 best-effort 갱신하고, 실패 시 기존 파일로 fallback한다. watchlist 전체에서 SEC feed를 자동 생성하지 않는 경계는 그대로다.

### R1o-SEC-WATCHLIST-FILING-FEEDS. SEC watchlist filing feed generation — **Draft tech spec (2026-06-28)**

RSS provider-policy recheck 결과, generic provider discovery는 계속 보류한다. SEC 외 provider discovery, HTML RSS link crawling, vendor URL pattern inference는 provider 정책과 ToS 검토가 더 필요하다.

다만 SEC 공식 Company Search RSS, 기존 `sources.rss.sec.company_filings`, 기존 local `company_tickers.json` lookup, off-by-default `ticker_cik_map_refresh`를 재사용하는 좁은 SEC-only slice는 설계할 근거가 충분하다. R1o Draft는 `sources.rss.sec.watchlist_company_filings`를 기본 `false` opt-in으로 두고, watchlist `us` symbols에서만 bounded SEC company filing feeds를 만드는 다음 구현 범위를 정의한다. 아직 production code는 없다.

### R1j-SEC-CIK-ERRORS. SEC ticker CIK map file error surface — **구현 완료 (2026-06-18)**

R1i는 로컬 mapping file lookup을 추가했지만, 파일이 없거나 JSON이 깨졌을 때 low-level `FileNotFoundError` 또는 `JSONDecodeError`가 그대로 노출될 수 있었다. 운영자는 이것을 설정 오류로 보고 어느 파일을 고쳐야 하는지 바로 알아야 한다.

구현 후 `load_sec_ticker_cik_map()`은 missing file, 읽기 실패, invalid JSON, non-object JSON을 `ValueError`로 정규화하고 오류 메시지에 path를 포함한다. mapping file을 자동 다운로드하거나 fallback하지 않는 R1i 경계는 그대로 유지한다.

### R1k-SEC-CIK-ENTRY-ERRORS. SEC ticker CIK map entry error context — **구현 완료 (2026-06-18)**

R1j는 파일 단위 오류를 정리했지만, 큰 SEC mapping file 안에서 특정 entry가 깨졌을 때 어느 entry를 고쳐야 하는지까지는 알려주지 않았다. 운영자는 수천 개 entry 중 문제 위치를 빠르게 찾아야 한다.

구현 후 `load_sec_ticker_cik_map()`은 SEC mapping entry의 JSON object shape와 `ticker`/`cik_str` 값을 검증할 때 파일 path와 entry key를 오류 메시지에 포함한다. 기존 validator를 재사용하므로 ticker token과 CIK 정규화 규칙은 config 입력과 mapping file 입력에서 계속 동일하다.

### R1l-SEC-CIK-CLI-ERRORS. SEC ticker CIK map CLI error surface — **구현 완료 (2026-06-18)**

R1j/R1k는 loader 오류 메시지를 정리했지만, `collect`/`run`/`backfill` CLI는 source build 단계의 `ValueError`를 잡지 않았다. 그래서 운영자는 좋은 설정 오류 메시지 대신 Python traceback을 볼 수 있었다.

구현 후 source build 단계의 `ValueError`는 `SourcesConfigError`로 감싸진다. CLI `main()`은 이 타입만 `[mimir] invalid sources.yaml:`로 출력한다. Fetch나 analysis 도중 생기는 downstream 오류는 계속 그대로 전파되므로, 실제 런타임 버그를 설정 오류로 오분류하지 않는다.

### R1m-SEC-CIK-MISSING-PATH. SEC ticker CIK map missing lookup path context — **구현 완료 (2026-06-18)**

R1j/R1k/R1l는 file-level, entry-level, CLI-level 오류 표면을 정리했지만, lookup-time missing ticker 오류는 여전히 `SEC ticker CIK map has no entry for ticker MSFT`처럼 어떤 mapping file을 썼는지 알려주지 않았다. 운영자는 여러 `company_tickers.json` snapshot 중 어느 파일을 보고 있는지 바로 알아야 한다.

구현 후 `load_sec_ticker_cik_map()`은 plain dict와 동등 비교가 계속 되는 dict-compatible wrapper를 반환하면서 내부에 `path` metadata를 보존한다. `_sec_company_filing_identifier()`는 loader-backed map에서 ticker가 없을 때만 `SEC ticker CIK map has no entry for ticker MSFT in <path>`를 만든다. 사용자가 직접 넘긴 plain mapping은 기존 pathless 오류 메시지를 유지한다.

### R1n-SEC-CIK-CLI-PATH-CONTRACT. SEC ticker CIK CLI stderr path contract — **구현 완료 (2026-06-18)**

R1m은 loader-backed missing ticker 오류에 mapping file 경로를 넣도록 구현했다. 하지만 `collect`, `run`, `backfill`의 CLI 회귀 테스트는 여전히 `SEC ticker CIK map has no entry for ticker MSFT` 같은 느슨한 substring만 확인했다. 이 상태에서는 향후 CLI가 경로를 빠뜨려도 테스트가 통과할 수 있었다.

구현 후 세 CLI 테스트는 모두 operator-facing stderr 계약을 직접 고정한다. 각 테스트는 `[mimir] invalid sources.yaml:` prefix를 계속 요구하고, 자신이 만든 로컬 `company_tickers.json`의 정확한 `str(path)`가 stderr에 포함되는지 확인한다. `backfill`은 `config_dir / "company_tickers.json"`을 사용해 config-relative 경로 계약도 함께 고정한다.

---

## 4. 견고성 (Robustness)

### A4. 타입드 페이로드 스키마 — **✅ 구현 완료 (Increment 2)**

`RawRecord.payload: dict[str, Any]`는 모든 다운스트림 시그널이 문자열 키(`payload["close"]`, `payload["value"]`)로 더듬게 한다. 스키마 드리프트가 조용히 실패한다. 데이터셋별 pydantic 페이로드 모델은 경계에서 드리프트를 잡는다. 가치 높으나 신규 → 설계. → [타입드 페이로드 설계문서](../superpowers/specs/2026-06-13-typed-payload-design.md).

**구현(Increment 2).** `mimir/core/payloads.py`에 데이터셋별 6개 모델(`PricePayload`/`FredMacroPayload`/`EcosMacroPayload`/`NewsPayload`/`SecFilingPayload`/`DartFilingPayload`, 모두 `frozen=True, extra="forbid"`) + 유니온 별칭 + 외부 디스패치(`PAYLOAD_BY_DATASET`/`parse_payload`, 봉투 `dataset` 기준). insights/historical/evaluation은 기존 `Insight`/`HistoricalInsight`/`BucketStat` 재사용(+`extra="forbid"`). `Record.payload`는 `Payload` 유니온(`model_validator(mode="before")`로 dict→모델 파싱), `RawRecord.payload`는 dict 유지. `JsonlStore` 직렬화 무변경 → 온디스크 JSONL 바이트 동일(오버라이트 재실행 git churn 0, 골든 round-trip으로 고정). 시그널은 내로잉 헬퍼로 타입드 접근. 닥터의 얕은 `check_payload_schema`는 경계 검증이 대체하여 제거.

### C1. 데이터 신선도·품질 닥터 — **구현 완료**

매니페스트는 *실행*을 기록하지만, "어제 가격 데이터가 비었다" 같은 *데이터 신선도*는 누구도 감시하지 않는다. `mimir doctor`는 워치리스트 대비 누락·정체(stale) 파티션과 스키마 이상을 플래그한다. "무음 실패 금지" 약속을 데이터 평면으로 확장. → [데이터 닥터 설계문서](../superpowers/specs/2026-06-13-data-doctor-design.md).

### DCHTML. Doctor standalone HTML report — **구현 완료 (2026-06-18)**

C1 데이터 닥터는 text와 JSON 출력으로 터미널과 자동화에는 충분했지만, 운영자가 링크나 artifact로 공유할 단일 HTML 산출물이 없었다. C1 설계문서의 선택 후속에도 `--html`과 en/ko/zh 라벨 렌더링이 남아 있었다.

구현 후 `mimir doctor --html reports/doctor.html --lang ko`는 같은 `DoctorReport`를 standalone HTML 파일로 쓴다. stdout은 기존 `--format text|json` 결과를 그대로 유지하고, WARN/CRITICAL exit code 정책도 바꾸지 않는다. HTML은 dataset, scope, severity label, detail을 escape하고, `Finding.message`는 사실 문자열로 유지해 자동화와 사람이 같은 진단 내용을 보게 한다.

### DOCHEALTH. README health metadata drift guard — **구현 완료 (2026-06-18)**

README 3종은 tests badge와 품질 표에 테스트 개수를 직접 표시한다. 이 값이 실제 pytest 수집 개수보다 뒤처지면 첫 화면의 품질 상태가 틀어진다.

구현 후 `tests/test_readme_docs.py`는 `pytest --collect-only -q`의 수집 개수를 기준으로 README 3종의 tests badge와 품질 표를 검증한다. 같은 테스트가 개선 카탈로그의 상단 상태와 결론에 최신 완료 ID가 들어 있는지도 확인한다. 그래서 테스트가 추가되거나 완료 증분이 늘어날 때 README와 카탈로그 요약이 함께 갱신된다.

### OPS1. Scheduled dashboard publication — **구현 완료 (2026-06-17)**

`mimir.dashboard`는 저장된 데이터, 최신 manifest, doctor finding을 읽어 `reports/dashboard.html`을 만들 수 있었다. 하지만 reusable scheduled workflow는 `python -m mimir.run` 뒤 바로 `git add data reports`를 실행했다. 그래서 scheduled run이 일일 리포트와 status page는 커밋해도 최신 dashboard를 생성하지 않았다.

구현 후 `_pipeline.yml`은 `Run pipeline` 뒤, `Commit data + reports` 앞에서 `python -m mimir.dashboard --data-root data --reports-root reports`를 실행한다. Hourly, daily, weekly, monthly caller는 모두 같은 reusable workflow를 호출하므로 cadence별 중복 없이 dashboard publish 계약을 공유한다.

Doctor WARN/CRITICAL은 dashboard health table에 표시한다. 그러나 scheduled workflow에 `python -m mimir.doctor`나 `--strict` hard gate는 넣지 않는다. Existing `mimir.run` collect failure gate는 그대로 유지하고, doctor finding을 배포 차단 정책으로 쓰는 문제는 별도 설계로 분리한다.

### BF-MANIFEST. 백필 실행 manifest 기록 — **구현 완료 (2026-06-16)**

`collect`는 소스별 성공/실패를 manifest에 남겼지만, `backfill`은 과거 데이터를 대량으로 적재하면서 실행 로그를 남기지 않았다. 이 격차는 README의 "무침묵 실패" 약속과 백로그의 "매니페스트는 후속" 항목으로 추적된다.

구현 후 `run_backfill()`은 성공 실행에 `fetched`, `stored`, `invalid`를 기록한다. upstream fetch, normalize, store 단계에서 예외가 나면 `ok=false` manifest를 먼저 남긴 뒤 예외를 다시 던진다. 그래서 호출자는 기존처럼 비정상 종료를 보면서도, 저장소에는 실패 흔적이 남는다.

### BF-PREFLIGHT. 백필 preflight failure manifest — **구현 완료 (2026-06-18)**

BF-MANIFEST 이후에도 `run_backfill()`은 source lookup 전에 실패하면 manifest를 남기지 못했다. 대표 사례는 `stooq`, `fred`, `dart`, `ecos`, `pykrx`처럼 등록된 source가 secret/package gate 때문에 `build_sources()`에서 제외되는 경우다.

구현 후 built-in `SourceSpec`는 static `SourceMeta`를 갖고, `run_backfill()`은 spec 목록을 한 번 로드해 build 결과와 preflight metadata를 함께 본다. 요청한 source id가 등록되어 있지만 사용할 수 없으면 `ok=false`, zero counts, secret/package gate reason을 manifest에 기록한 뒤 기존 `SystemExit("unknown or unavailable source: ...")`를 유지한다. 진짜 unknown source id는 cadence를 알 수 없으므로 manifest 없이 argument error로 남긴다.

### MR1. 거시 개정 저장 정책 — **구현 완료 (2026-06-16)**

FRED와 ECOS는 같은 관측일의 값을 나중에 고칠 수 있다. 기존 저장 정책은 같은 `idempotency_key`를 다시 받으면 첫 값을 유지했다. 그래서 공식 기관이 금리나 통계 값을 개정해도 `MacroRegimeSignal`은 오래된 값을 계속 읽을 수 있었다.

구현 후 source 수집과 backfill은 같은 helper인 `append_overwrite_enabled(dataset)`로 저장 정책을 고른다. 현재 `Dataset.MACRO`만 overwrite append를 쓰고, `prices`, `filings`, `news`는 기존 first-write-wins를 유지한다. `JsonlStore.append(overwrite=True)`는 새 key와 교체된 key를 모두 `stored`에 반영한다. 그래서 macro 값이 실제로 바뀌면 manifest와 backfill 반환값도 변경을 드러낸다.

### D1. 통합 `mimir` CLI — **구현 완료 (2026-06-18)**

README는 `mimir.collect`, `mimir.analyze`, `mimir.doctor` 같은 설치형 실행 파일을 CLI 표면으로 보여줬지만, `pyproject.toml`에는 console script 선언이 없었다. 즉 editable install 후 README에 적힌 명령이 생기지 않는 문서-패키지 계약 불일치가 있었다.

구현 후 `[project.scripts]`는 통합 명령 `mimir`와 dotted aliases(`mimir.collect`, `mimir.analyze`, `mimir.doctor` 등)를 제공한다. `mimir <subcommand>`는 기존 module-level `main(argv)`에 그대로 위임하므로 argparse help, 검증, exit code를 재정의하지 않는다. 기존 `python -m mimir.X` 경로와 workflow 명령도 유지한다.

### ENV1. Runtime `.env` autoload contract — **구현 완료 (2026-06-18)**

README는 `.env`가 runtime에 자동 로드되고, CI Secrets나 shell 환경변수가 `.env`보다 우선한다고 설명한다. `Settings.from_env()`는 `env=None`일 때 이 계약을 지켰지만, `collect`, `run`, `deliver`, `backfill` CLI 경로는 `os.environ`을 직접 넘겨 `.env` 로드를 우회했다. 그래서 Quick Start대로 `.env`에 키를 적은 로컬 사용자가 설치형 CLI를 실행하면 키가 없는 것처럼 source가 skip될 수 있었다.

구현 후 runtime 함수의 `env` 인자는 선택값이다. CLI는 기본 `env=None` 경로를 사용해 기존 `find_dotenv(usecwd=True)`와 `load_dotenv(..., override=False)` 동작을 탄다. 테스트와 library caller는 `env={...}`를 명시해 `.env`를 읽지 않는 deterministic 경로를 계속 쓸 수 있다. Secret 값은 manifest, report, 문서 출력에 추가로 노출하지 않는다.

### CFG1. `sources.yaml` CLI validation contract — **구현 완료 (2026-06-18)**

`docs/reference/config/sources.md`는 malformed `sources.yaml`을 CLI가 `[mimir] invalid sources.yaml:` 메시지로 실패시킨다고 약속한다. 기존 `collect`/`run`/`backfill`은 이 계약을 지켰지만, `analyze`는 raw pydantic `ValidationError`를 노출할 수 있었고 `deliver`/`dashboard`는 `lang`만 unchecked dict에서 읽어 `analysys:` 같은 typo를 숨길 수 있었다.

구현 후 `mimir.config.load_validated_sources_config()`가 raw dict load와 `parse_sources_config()` 검증을 한 번에 제공한다. 각 CLI `main()`은 이 helper 호출만 좁은 `try/except ValidationError`로 감싸고, runtime 함수 호출은 catch 밖에 둔다. 그래서 `analyze`/`deliver`/`dashboard`도 malformed config에 대해 friendly message와 exit code 1로 실패하면서, downstream data/model `ValidationError`는 `sources.yaml` 오류로 오분류하지 않는다.

### CFG2. `mimir doctor` sources config validation — **구현 완료 (2026-06-18)**

`mimir doctor`는 `--config-dir`을 받는 운영 점검 명령이다. 변경 전에는 같은 directory의 `watchlist.yaml`만 읽었기 때문에 `sources.yaml` 최상위 키 오타나 block schema 오류가 있어도 데이터 freshness 점검과 HTML 파일 쓰기를 계속할 수 있었다.

구현 후 `doctor_cli.main()`도 `load_validated_sources_config()`를 먼저 호출한다. `sources.yaml` schema가 깨져 있으면 `run_doctor()`를 실행하지 않고, `--html` 파일도 쓰지 않는다. 오류 표면은 다른 CLI와 같은 `[mimir] invalid sources.yaml:` prefix와 exit code 1이다. 이 변경은 source build를 실행하거나 SEC mapping file을 다운로드하지 않으며, doctor의 read-only 데이터 점검 경계는 그대로 유지한다.

### CFG3-CONFIG-GUARDRAILS. Watchlist schema + LLM headline cap — **구현 완료 (2026-06-18)**

CFG1/CFG2는 `sources.yaml`을 CLI와 doctor 경계에서 검증했다. 그러나 두 설정 입력이 여전히 무음 손상 또는 비용 위험을 안고 있었다. `watchlist.yaml`은 schema 검증 없이 읽혀 `us: AAPL` 같은 스칼라가 `["A", "A", "P", "L"]`로 풀릴 수 있었고, `llm_sentiment_max_headlines`는 정수 타입만 검증해 `0`·음수·`51`도 받았다.

구현 후 `_WatchlistConfig`(`extra="forbid"`, `us`/`kr`는 `list[StrictStr]`)가 비-매핑 최상위, 비-문자열 symbol, 공백 symbol을 거부하고 symbol 양끝 공백을 제거한다. `load_watchlist()`는 `ValidationError`를 path가 포함된 `WatchlistConfigError`로 감싸고, watchlist를 읽는 CLI는 `[mimir] invalid watchlist.yaml:` prefix와 exit code 1로 실패한다. `llm_sentiment_max_headlines`는 `SourcesConfig`와 `_TopLevelSourcesConfig` 두 모델 모두에서 `Field(default=50, ge=1, le=50)`로 제한해, raw YAML 검증 경로와 직접 생성 경로 양쪽에서 유료 LLM 호출량을 안전 범위로 묶는다. 기본값 `50`과 `llm_sentiment_enabled: false`는 유지하고, 새 네트워크 호출이나 저장 계약 변경은 없다.

### COV1-CONTRACT-COVERAGE. 기존 계약 characterization 커버리지 — **구현 완료 (2026-06-19)**

4차원 감사(견고성·문서계약·테스트·확장성) 결과 코드베이스는 성숙했고, 견고성·문서계약·확장성 차원은 이미 구현됐거나 근거와 함께 보류됐다. 남은 실질 작업은 *이미 옳지만 테스트로 고정되지 않은 계약*을 characterization 테스트로 박는 것이었다. 이 증분은 새 동작을 추가하지 않는다. 기존 코드가 이미 옳음을 확인하고 회귀를 막는다.

- **ECOS 비월간 cycle (`Q`/`A`)**: `EcosSource`의 idempotency_key는 원본 `TIME` token을 그대로 쓰고, `ts`는 분기 첫날·연초로 파싱된다. 기존 테스트는 월간(`M`)만 exercise했다. 분기(`2026Q2` → 4월 1일)와 연간(`2026` → 1월 1일)이 stable key와 올바른 partition day를 만드는지 고정했다. git-as-DB의 "idempotency_key/partition 불변" 약속을 비월간 cycle까지 확장한다.
- **ECOS 결측 관측값**: `DATA_VALUE`가 빈 문자열이거나 없는 row는 bogus float로 강제하지 않고 skip한다. 이 fail-soft 경로를 고정했다.
- **config 절대경로 보존**: `_resolve_sources_config_paths()`는 상대 `ticker_cik_map_path`만 config_dir 기준으로 재배치하고, 절대경로는 그대로 통과시켜야 한다. 절대경로 분기를 고정했다(R1m/R1n의 path-in-error 계약 보호).
- **price_momentum 결측 거래량**: 가격은 있고 거래량이 없을 때 volume surge 보정을 건너뛰고 base confidence를 유지하며 크래시하지 않는다. 이 방어 분기를 고정했다.

모든 테스트는 추가 즉시 GREEN이다(기존 코드가 옳으므로). 새 동작·네트워크 호출·저장 계약 변경은 없다.

### I18N1-PARITY-GUARD. 리포트 i18n 패리티 drift guard — **구현 완료 (2026-06-19)**

`mimir/report/i18n.py`는 en/ko/zh 리포트 UI 문자열을 `t(key, lang, **fmt)`로 제공하고, 키가 없으면 영어로, 그래도 없으면 key 자체로 fallback한다. 이 fallback은 런타임 크래시를 막는 안전장치지만, 동시에 *조용한 drift*를 가린다. 누군가 `en`에만 키를 추가하고 `ko`/`zh`에 빠뜨리면, 한국어·중국어 리포트가 오류 없이 영어 문자열을 노출한다. placeholder가 어긋나면(`{count}`를 한 언어에서 빠뜨림) `t()`가 값을 누락하거나 `KeyError`를 낸다. trilingual 리포트는 README가 한 약속이지만, 이 drift를 잡는 테스트가 없었다.

구현 후 `tests/report/test_i18n.py`가 세 가지를 고정한다. (1) `LANGS`의 모든 언어가 `en`과 동일한 키 집합을 갖는다(누락/잉여 키 = 조용한 영어 fallback 차단). (2) 각 키의 `{placeholder}` 집합이 언어 간 동일하다(렌더 시 값 누락·`KeyError` 차단). (3) `t()`의 문서화된 fallback 계약(unknown lang→en, unknown key→key)을 고정한다. 현재 패리티가 맞으므로 세 테스트는 추가 즉시 GREEN이고, 이후 번역 drift가 생기면 회귀로 잡는다. 이는 DOCHEALTH(README 수치 drift)·catalog ID guard와 같은 "조용한 문서/UI drift 금지" 계열이다. 런타임 코드·저장 계약 변경은 없다.

> **고려 후 보류 — LLM signal weight YAML 노출.** 확장성 감사는 `LlmSentimentSignal(weight=...)` 생성자 인자가 config로 배선되지 않음을 발견했다. 그러나 spec(2026-06-13-llm-sentiment-seam-design.md §5.1/§5.2)은 `weight`를 *생성자 기본값*(0.8)으로만 문서화하고 sources.yaml key로 약속하지 않는다. 다른 모든 시그널도 weight를 코드 상수로 둔다(`상수는 백테스트 B1로 보정`). llm_sentiment만 YAML로 노출하면 일관성 없는 순수 신규 튜닝 표면이 된다(catalog §0 "스코프 제조기" 회피). 따라서 구현하지 않고 §6 보류로 기록한다.

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
AN1-SIGNAL-PLUGIN-ENTRYPOINTS ─ analysis signal plugin entry points · mimir.analysis_signals
AN2-LLM-CLASSIFIER-CARDINALITY ─ llm_sentiment classifier batch length guard
AN3-ANALYSIS-PLUGIN-BUILTIN-GUARD ─ analysis.plugins built-in signal namespace warning
AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION ─ analysis signal evaluate exception isolation
AN5-ANALYSIS-SIGNAL-SPECS-INJECTION ─ build_signals direct SignalSpec injection
AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY ─ analysis signal invalid result type boundary
R1a ──────── news mention alias matcher · analysis.news.aliases
R1b ──────── news captured window · DataReader.read_captured_window
C2a-CAPTURED-NEWS-CACHE ─ captured news window in-memory cache
R1c ──────── default news aliases · analysis.news.use_default_aliases
R1d ──────── symbol-tagged RSS feeds · sources.rss.feeds[].symbol
R1e ──────── static RSS feed catalog · sources.rss.catalogs
R1f-SEC ─── SEC EDGAR company filing RSS provider
R1g-SEC-STRUCTURED ─ SEC structured disclosure RSS catalog
R1h-SEC-TICKER ─ SEC company filing RSS ticker input
R1i-SEC-CIK ─ SEC ticker CIK local mapping lookup
R1o-SEC-WATCHLIST-FILING-FEEDS ─ draft: opt-in SEC watchlist company filing feeds
R1j-SEC-CIK-ERRORS ─ SEC ticker CIK map file error surface
R1k-SEC-CIK-ENTRY-ERRORS ─ SEC ticker CIK map entry error context
R1l-SEC-CIK-CLI-ERRORS ─ SEC ticker CIK map CLI error surface
R1m-SEC-CIK-MISSING-PATH ─ SEC ticker CIK map missing lookup path context
R1n-SEC-CIK-CLI-PATH-CONTRACT ─ SEC ticker CIK CLI stderr path contract
D1 ───────── unified CLI entry points · mimir + mimir.<command>
ENV1 ─────── runtime .env autoload · CLI default env=None
CFG1 ─────── sources.yaml CLI validation · shared load_validated_sources_config
CFG2 ─────── mimir doctor sources.yaml schema validation
CFG3-CONFIG-GUARDRAILS ─ watchlist schema + llm_sentiment_max_headlines cap
COV1-CONTRACT-COVERAGE ─ ECOS Q/A cycle·blank value · config 절대경로 · price volume edge characterization
I18N1-PARITY-GUARD ─ report i18n key·placeholder parity drift guard
D2 ───────── GitHub Actions Node24-compatible action majors
	C3 ───────── pykrx retry/backoff · FetchError manifest surface
	BF-MANIFEST ─ backfill success/failure manifest
	BF-PREFLIGHT ─ backfill registered-unavailable preflight manifest
	OPS1 ─────── scheduled dashboard publication · reports/dashboard.html
DCHTML ───── doctor standalone HTML report · mimir doctor --html
DOCHEALTH ─ README health metadata drift guard
MR1 ──────── macro revision storage policy · Dataset.MACRO last-write-wins
```

각 증분은 자기 spec → plan → 구현 → finish 사이클을 가진다. 본 카탈로그는 그 지도(map)다.

---

## 6. 보류 항목 — 근거 명시

| 항목 | 보류 근거 |
|---|---|
| **C2 파티션 인덱스** | `read_window` 파티션 프루닝이 이미 일반 날짜 윈도우 핫패스를 처리한다. R1b의 captured-window 반복 scan은 C2a 인메모리 cache로 완화했다. persistent index나 보조 파티션은 데이터가 수년 누적되고 cache rebuild 자체가 병목이라는 측정이 나온 뒤 설계한다. 엄밀한 설계와 측정 기반 unblock 기준은 [설계문서](../superpowers/specs/2026-06-19-captured-date-persistent-index-design.md)로 승격했고, unblock 선행 조건인 **측정 계기는 구현됐다**: `DataReader._captured_date_index`가 재빌드 시 records/days/elapsed_ms를 DEBUG 로그로 남긴다. on-disk index 구현은 이 측정이 병목 임계를 넘을 때 착수한다(아직 미도달). |
| **R1f Generic provider RSS discovery** | R1f-SEC는 공식 SEC Company Search Atom URL 조립을 해결했고, R1g-SEC-STRUCTURED는 SEC의 broad XBRL feed catalog를 정적으로 추가했다. R1h-SEC-TICKER는 SEC Company Search RSS의 ticker token 입력을 추가했다. R1i-SEC-CIK는 사용자가 제공한 로컬 SEC `company_tickers.json` lookup과 ambiguity failure policy를 추가했다. R1j-SEC-CIK-ERRORS, R1k-SEC-CIK-ENTRY-ERRORS, R1l-SEC-CIK-CLI-ERRORS, R1m-SEC-CIK-MISSING-PATH, R1n-SEC-CIK-CLI-PATH-CONTRACT는 잘못된 로컬 파일, 개별 entry, CLI 출력, missing ticker lookup, CLI stderr 회귀 계약의 오류 표면을 정리했다. SEC mapping file refresh/cache는 [설계문서](../superpowers/specs/2026-06-19-sec-ticker-cik-map-cache-design.md) 후 **off-by-default로 구현됐다**(`sources.rss.sec.ticker_cik_map_refresh.enabled`; 기본 `false` → 네트워크 0, 켜면 conditional GET + TTL + fallback). R1o-SEC-WATCHLIST-FILING-FEEDS는 SEC 공식 source만 쓰는 watchlist feed generation slice를 Draft spec으로 승격했다. 남은 부채는 generic live discovery, SEC 외 provider discovery, HTML RSS link crawling, vendor URL pattern inference처럼 provider 정책과 ToS 검토가 더 필요한 범위다. |
| **D3 spec/ro드맵 번역** | 내부 설계문서와 상세 reference docs는 Korean-first/KO-only로 유지한다(백로그 재확인). 사용자 진입 문서(README ×3)는 이미 trilingual이고, 향후 번역이 필요하면 내부 specs 전체가 아니라 bounded reference-doc translation slice로 별도 설계한다. |
| **LLM signal weight YAML 노출** | `LlmSentimentSignal(weight=...)` 생성자 인자는 spec에서 *생성자 기본값*(0.8)으로만 문서화되고 sources.yaml key로 약속되지 않았다. 모든 시그널 weight는 코드 상수이며 백테스트(B1)로 보정 대상이다. llm_sentiment만 YAML로 노출하면 일관성 없는 순수 신규 튜닝 표면이 되므로(catalog §0) 보류한다. signal weight 튜닝이 실제 요구되면 모든 시그널을 아우르는 별도 설계로 다룬다. |

---

## 7. 안티-발견 (확인됨, 손대지 않음)

건강한 코드베이스의 증거 — 다음은 검토했고 **고칠 것이 없다**:

- 레이어 그래프 순환 없음 · 파일 크기 건전(최대 ~150줄) · 타입 검증은 pyproject.toml strict config와 README 테스트 배지와 docs health guard가 추적한다.
- `idempotency_key`는 소스 prefix로 교차충돌 없음 · 파티션은 자정 UTC라 안정.
- 시크릿은 env/`.env`(gitignore)만 · ECOS 키 URL 유출은 이미 레다크션 처리.
- `http_get` 429/5xx 재시도 + 4xx 빠른 실패 · 소스 격리(한 소스 실패가 전체를 멈추지 않음).
- CI와 수집 pipeline은 Node24 호환 `actions/checkout@v6`·`actions/setup-python@v6`를 사용하며, workflow guard 테스트가 major 회귀를 잡는다.
- `pykrx`는 GRAY·선택 소스 상태를 유지하면서 OHLCV 호출 실패를 짧게 재시도하고, 소진 시 `FetchError`로 manifest에 실패 원인을 남긴다.
- 재생성 데이터셋은 `replace_partition`으로 당일 파티션 전체 교체 · 가격/공시/뉴스 원천 데이터는 append-only · 거시 원천 데이터는 공식 개정값을 last-write-wins로 반영.
- 백필은 성공과 실패를 manifest에 기록한다. 등록된 source가 secret/package gate 때문에 fetch 전에 unavailable이어도 `ok=false` manifest를 남기고, 실패는 기록 후 다시 예외를 던져 비정상 종료 신호를 유지한다.

**결론.** 본 작업은 *확장성 천장 제거 + 성숙기 피드백 루프 + 운영 가시성 강화*를 만드는 흐름이다. A3, A3b, A3c, AN1-SIGNAL-PLUGIN-ENTRYPOINTS, AN2-LLM-CLASSIFIER-CARDINALITY, AN3-ANALYSIS-PLUGIN-BUILTIN-GUARD, AN4-ANALYSIS-ENGINE-SIGNAL-ISOLATION, AN5-ANALYSIS-SIGNAL-SPECS-INJECTION, AN6-ANALYSIS-SIGNAL-RESULT-BOUNDARY, R1a, R1b, C2a-CAPTURED-NEWS-CACHE, R1c, R1d, R1e, R1f-SEC, R1g-SEC-STRUCTURED, R1h-SEC-TICKER, R1i-SEC-CIK, R1j-SEC-CIK-ERRORS, R1k-SEC-CIK-ENTRY-ERRORS, R1l-SEC-CIK-CLI-ERRORS, R1m-SEC-CIK-MISSING-PATH, R1n-SEC-CIK-CLI-PATH-CONTRACT, MR1, D1, D2, ENV1, CFG2, CFG3-CONFIG-GUARDRAILS, COV1-CONTRACT-COVERAGE, I18N1-PARITY-GUARD, C3, BF-MANIFEST, BF-PREFLIGHT, OPS1, DCHTML, DOCHEALTH까지 구현되었다. R1o-SEC-WATCHLIST-FILING-FEEDS는 Draft spec이다. 남은 신규 아키텍처 부채는 generic provider RSS discovery와 persistent partition/captured-date index다.
