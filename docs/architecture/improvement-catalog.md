# Mimir 발전 카탈로그 — 확장성·견고성·심화 (2026-06-13)

> **상태**: Increment 1–5 구현 완료 + 2026-06-16 hardening/A2/A3 구현 완료
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
| **B1** | 시그널 백테스트·평가 하네스 (사후수익 적중률) | 분석심화 | 신규(최고가치) | **✅ 구현 완료 (Increment 4 + 리포트 합류)** | 코드 + 테스트 · [spec](../superpowers/specs/2026-06-13-signal-backtest-design.md) |
| **B2** | LLM 뉴스 감성 시그널 (news_volume 대체, 하이브리드) | 분석심화 | 로드맵 + 백로그 R1 | **✅ seam 구현 (Increment 5, off-by-default)** | 코드 + 테스트 |
| **H1** | 재생성 데이터 stale 제거 + pipeline scorecard 갱신 | 견고성/운영 | B1 후속 + 리뷰 발견 | **✅ 구현 완료 (2026-06-16 hardening)** | `replace_partition`, `run_evaluate`, daily report scorecard |
| **C1** | 데이터 신선도·품질 닥터 (`mimir doctor`) | 운영 | "무음 실패 금지" 약속 | **✅ 구현 완료 (Increment 3)** | 코드 + 테스트(179) |
| **C2** | 파티션 인덱스 (git-as-DB rglob 스케일) | 성능 | 신규 | ⏸ 보류 | 본 문서 §6 |
| **C3** | pykrx 타임아웃·재시도 (BaseSource 미사용) | 견고성 | 백로그 LOW | ⏸ 보류(GRAY/옵션) | 본 문서 §6 |
| **D1** | 통합 `mimir` CLI (console_scripts) | DX | 신규 | ⏸ 보류 | 본 문서 §6 |
| **D2** | GH Actions Node20→24 범프 | CI | 백로그 LOW | ⏸ 보류(안정 신버전 대기) | 본 문서 §6 |

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

외부 package entry-point는 아직 보류다. 지금 구현은 내장 소스 등록을 데이터화해 builder 분기 증가를 멈추는 slice다.

---

## 3. 분석 심화 (Analytical depth)

### B1. 시그널 백테스트·평가 하네스 — **구현 완료**

Mimir는 시그널을 *발행*하지만, 그 시그널이 실제로 무언가를 예측하는지 **측정하지 않는다.** S4 event-study는 "과거에 이런 일이 있었다"를 보지만, "우리 인사이트의 과거 적중률"이라는 피드백 루프는 없다. 백테스트 하네스는 Mimir를 "시그널 발행"에서 "*검증된* 시그널 발행"으로 끌어올리고, 신뢰 가능한 S5(자동매매)의 토대가 된다. 분석/실행 분리 원칙 준수(읽기 전용). → [백테스트 설계문서](../superpowers/specs/2026-06-13-signal-backtest-design.md).

**구현(Increment 4 + 2026-06-16 hardening).** `mimir.evaluate`가 저장된 `insights`와 `prices`만 읽어 `evaluation` 데이터셋을 만든다. `mimir.run`은 `collect -> analyze -> history -> evaluate -> deliver` 순서로 실행해 리포트가 같은 실행에서 갱신된 scorecard를 읽는다. `daily_report`와 `dashboard`는 시그널 성적표를 표로 보여준다. 표본 부족으로 모든 버킷이 사라지면 `JsonlStore.replace_partition`이 당일 evaluation 파티션을 삭제해 오래된 scorecard가 남지 않는다.

### B2. LLM 뉴스 감성 시그널 — **seam 구현 완료 (off-by-default)**

로드맵은 "규칙 기반 → 하이브리드(LLM 후속)"를 명시하고, 백로그 R1은 `news_volume`이 실데이터에서 거의 무력함을 인정한다(공식 피드에 티커 부재). LLM 감성 시그널이 가장 큰 분석 가치다. **그러나** 유료 API 호출을 기본값으로 켜면 프로젝트의 **무료(free) 원칙**과 충돌한다. 따라서 *seam과 off-by-default 스캐폴드를 설계*하되 기본 파이프라인에서 유료 호출을 발생시키지 않는다(GRAY 소스와 동일한 토글 철학). → [LLM seam 설계문서](../superpowers/specs/2026-06-13-llm-sentiment-seam-design.md).

**구현(Increment 5).** `NewsSentimentSignal`과 classifier seam은 구현됐지만, 실제 LLM 호출은 `[llm]` extra, `ANTHROPIC_API_KEY`, `llm_sentiment_enabled: true`가 모두 맞을 때만 켜진다. 기본 pipeline은 여전히 무료 경로다.

---

## 4. 견고성 (Robustness)

### A4. 타입드 페이로드 스키마 — **✅ 구현 완료 (Increment 2)**

`RawRecord.payload: dict[str, Any]`는 모든 다운스트림 시그널이 문자열 키(`payload["close"]`, `payload["value"]`)로 더듬게 한다. 스키마 드리프트가 조용히 실패한다. 데이터셋별 pydantic 페이로드 모델은 경계에서 드리프트를 잡는다. 가치 높으나 신규 → 설계. → [타입드 페이로드 설계문서](../superpowers/specs/2026-06-13-typed-payload-design.md).

**구현(Increment 2).** `mimir/core/payloads.py`에 데이터셋별 6개 모델(`PricePayload`/`FredMacroPayload`/`EcosMacroPayload`/`NewsPayload`/`SecFilingPayload`/`DartFilingPayload`, 모두 `frozen=True, extra="forbid"`) + 유니온 별칭 + 외부 디스패치(`PAYLOAD_BY_DATASET`/`parse_payload`, 봉투 `dataset` 기준). insights/historical/evaluation은 기존 `Insight`/`HistoricalInsight`/`BucketStat` 재사용(+`extra="forbid"`). `Record.payload`는 `Payload` 유니온(`model_validator(mode="before")`로 dict→모델 파싱), `RawRecord.payload`는 dict 유지. `JsonlStore` 직렬화 무변경 → 온디스크 JSONL 바이트 동일(오버라이트 재실행 git churn 0, 골든 round-trip으로 고정). 시그널은 내로잉 헬퍼로 타입드 접근. 닥터의 얕은 `check_payload_schema`는 경계 검증이 대체하여 제거.

### C1. 데이터 신선도·품질 닥터 — **구현 완료**

매니페스트는 *실행*을 기록하지만, "어제 가격 데이터가 비었다" 같은 *데이터 신선도*는 누구도 감시하지 않는다. `mimir doctor`는 워치리스트 대비 누락·정체(stale) 파티션과 스키마 이상을 플래그한다. "무음 실패 금지" 약속을 데이터 평면으로 확장. → [데이터 닥터 설계문서](../superpowers/specs/2026-06-13-data-doctor-design.md).

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
```

각 증분은 자기 spec → plan → 구현 → finish 사이클을 가진다. 본 카탈로그는 그 지도(map)다.

---

## 6. 보류 항목 — 근거 명시

| 항목 | 보류 근거 |
|---|---|
| **C2 파티션 인덱스** | `read_window` 파티션 프루닝이 이미 핫패스를 처리. 인덱스는 데이터가 수년 누적된 *뒤*의 최적화 — 지금은 시기상조(YAGNI). 신선도 닥터(C1)가 먼저 스케일 신호를 준다. |
| **C3 pykrx 타임아웃** | GRAY·옵션 소스. A3는 pykrx 생성 gate만 데이터화했고, pykrx fetch 자체는 아직 `BaseSource`를 쓰지 않는다. 영향 LOW라 단독 작업은 보류. |
| **D1 통합 CLI** | 순수 DX. 5개 `python -m mimir.X`는 동작에 문제없음. console_scripts entry-point는 좋지만 약속에 추적되지 않음 → 보류. |
| **D2 Node20→24** | 백로그 LOW. 동작 무해. `actions/checkout`·`setup-python`의 *안정* 신버전이 나오면 범프 — 지금 강제 범프는 CI 불안정 risk. |
| **D3 spec/ro드맵 번역** | 내부 설계문서는 KO-only 유지(백로그 결정). 사용자 문서(README ×3)는 이미 trilingual. |

---

## 7. 안티-발견 (확인됨, 손대지 않음)

건강한 코드베이스의 증거 — 다음은 검토했고 **고칠 것이 없다**:

- 레이어 그래프 순환 없음 · 파일 크기 건전(최대 ~150줄) · mypy strict 통과.
- `idempotency_key`는 소스 prefix로 교차충돌 없음 · 파티션은 자정 UTC라 안정.
- 시크릿은 env/`.env`(gitignore)만 · ECOS 키 URL 유출은 이미 레다크션 처리.
- `http_get` 429/5xx 재시도 + 4xx 빠른 실패 · 소스 격리(한 소스 실패가 전체를 멈추지 않음).
- 재생성 데이터셋은 `replace_partition`으로 당일 파티션 전체 교체 · 원천 데이터는 append-only.

**결론.** 본 작업은 *확장성 천장 제거 + 성숙기 피드백 루프*를 만드는 흐름이다. A3까지 구현되었고, 남은 신규 아키텍처 부채는 외부 source plugin entry-point와 `news_volume` 실데이터 한계다.
