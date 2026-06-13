# Mimir 발전 카탈로그 — 확장성·견고성·심화 (2026-06-13)

> **상태**: 승인 대기 → 증분 실행 중
> **목적**: S1–S4가 완성된 건강한 코드베이스(122 테스트 · 95% 커버리지 · mypy strict)에서 "원래 스코프 이상으로 더 확장성 있고, 개선·발전할 수 있는 점"을 빠짐없이 식별하고, 각 항목을 **지금 구현 / 지금 설계(spec) / 보류**로 분류한다.
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
| **A4** | 데이터셋별 타입드 페이로드 스키마 (`dict[str,Any]` 제거) | 견고성 | 신규 | 📐 설계 (Increment 2) | [spec](../superpowers/specs/2026-06-13-typed-payload-design.md) |
| **A2** | 시리즈 식별자 단일 진실원 (macro_regime ↔ 어댑터) | 확장성 | 백로그 | 📐 설계 (후속) | [spec](../superpowers/specs/2026-06-13-config-driven-extensibility-design.md) §9 |
| **A3** | 선언적 소스 등록 (if-사다리 → 레지스트리/entry-point) | 아키텍처 | README 약속(부분) | 📐 설계 (후속) | [spec](../superpowers/specs/2026-06-13-config-driven-extensibility-design.md) §8 |
| **B1** | 시그널 백테스트·평가 하네스 (사후수익 적중률) | 분석심화 | 신규(최고가치) | 📐 설계 | [spec](../superpowers/specs/2026-06-13-signal-backtest-design.md) |
| **B2** | LLM 뉴스 감성 시그널 (news_volume 대체, 하이브리드) | 분석심화 | 로드맵 + 백로그 R1 | 📐 설계 (off-by-default seam) | [spec](../superpowers/specs/2026-06-13-llm-sentiment-seam-design.md) |
| **C1** | 데이터 신선도·품질 닥터 (`mimir doctor`) | 운영 | "무음 실패 금지" 약속 | 📐 설계 (fast-follow 후보) | [spec](../superpowers/specs/2026-06-13-data-doctor-design.md) |
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

오늘 FRED 시리즈 하나를 추가하려면 **파이썬 코드를 고쳐야 한다.** README는 "소스 추가 = 파일 하나 + 등록"을 약속했지만 실제로는 *파일 + Settings 필드 + builder 분기 + 하드코딩 시리즈*다. 이 격차가 확장성 천장이다.

**근거(추적성).** 백로그 "설정 기반 시리즈/피드"(`IMPROVEMENTS.md` LOW) + README의 확장성 약속. 순수 신규가 아니라 *이미 설계됐으나 배선되지 않은* 기능.

**결정.** **Increment 1로 구현.** `config/sources.yaml`이 어댑터별 블록(`fred.series`/`ecos.series`/`rss.feeds`)을 선언하고, `build_sources(settings, config)`가 검증된 설정을 생성자에 전달한다. → 사용자가 YAML만으로 커버리지를 넓힌다. 상세: [config-driven 설계문서](../superpowers/specs/2026-06-13-config-driven-extensibility-design.md).

**불변식(테스트로 고정).** 설정 배선은 `idempotency_key` 포맷·파티션 레이아웃을 **바꾸지 않는다**. 빈/부재 설정은 **오늘의 기본값을 그대로 재현**한다. git-as-DB에서 키가 조용히 바뀌면 이미 커밋된 데이터가 고아가 되거나 중복된다 — 이 리팩터가 "저위험"에서 "고위험"으로 바뀌는 유일한 경로.

### A2. 시리즈 식별자 단일 진실원 — **지금 설계 (Increment 2)**

`MacroRegimeSignal.RATE_SERIES = {"FEDFUNDS","DGS10","722Y001.0101000"}`가 FRED/ECOS가 발행하는 시리즈 식별자를 **두 번째로** 하드코딩한다. A1로 사용자가 시리즈를 바꾸면 거시 시그널은 그것을 모른다. 이 결합은 **source→signal 경계를 가로지르며**, 설정을 시그널 빌더까지 배선해야 한다 — A1보다 위험하고 별도 증분이 옳다. (Increment 1은 시그널 디스패치를 건드리지 않는다.)

### A3. 선언적 소스 등록 — **지금 설계**

`build_sources`의 `if settings.X_api_key:` 사다리는 소스마다 분기를 늘린다. 완전한 선언적 레지스트리(소스 메타 테이블 또는 `importlib.metadata` entry-point)는 진짜 "파일 하나" 확장을 준다. 그러나 이는 *신규 아키텍처*다 — A1(설정 배선)만 지금 하고, 사다리 제거는 설계로 남긴다.

---

## 3. 분석 심화 (Analytical depth)

### B1. 시그널 백테스트·평가 하네스 — **지금 설계 (최고 가치)**

Mimir는 시그널을 *발행*하지만, 그 시그널이 실제로 무언가를 예측하는지 **측정하지 않는다.** S4 event-study는 "과거에 이런 일이 있었다"를 보지만, "우리 인사이트의 과거 적중률"이라는 피드백 루프는 없다. 백테스트 하네스는 Mimir를 "시그널 발행"에서 "*검증된* 시그널 발행"으로 끌어올리고, 신뢰 가능한 S5(자동매매)의 토대가 된다. 분석/실행 분리 원칙 준수(읽기 전용). → [백테스트 설계문서](../superpowers/specs/2026-06-13-signal-backtest-design.md).

### B2. LLM 뉴스 감성 시그널 — **지금 설계 (off-by-default seam)**

로드맵은 "규칙 기반 → 하이브리드(LLM 후속)"를 명시하고, 백로그 R1은 `news_volume`이 실데이터에서 거의 무력함을 인정한다(공식 피드에 티커 부재). LLM 감성 시그널이 가장 큰 분석 가치다. **그러나** 유료 API 호출을 기본값으로 켜면 프로젝트의 **무료(free) 원칙**과 충돌한다. 따라서 *seam과 off-by-default 스캐폴드를 설계*하되 기본 파이프라인에서 유료 호출을 발생시키지 않는다(GRAY 소스와 동일한 토글 철학). → [LLM seam 설계문서](../superpowers/specs/2026-06-13-llm-sentiment-seam-design.md).

---

## 4. 견고성 (Robustness)

### A4. 타입드 페이로드 스키마 — **지금 설계**

`RawRecord.payload: dict[str, Any]`는 모든 다운스트림 시그널이 문자열 키(`payload["close"]`, `payload["value"]`)로 더듬게 한다. 스키마 드리프트가 조용히 실패한다. 데이터셋별 pydantic 페이로드 모델은 경계에서 드리프트를 잡는다. 가치 높으나 신규 → 설계. → [타입드 페이로드 설계문서](../superpowers/specs/2026-06-13-typed-payload-design.md).

### C1. 데이터 신선도·품질 닥터 — **지금 설계 (fast-follow 후보)**

매니페스트는 *실행*을 기록하지만, "어제 가격 데이터가 비었다" 같은 *데이터 신선도*는 누구도 감시하지 않는다. `mimir doctor`는 워치리스트 대비 누락·정체(stale) 파티션과 스키마 이상을 플래그한다. "무음 실패 금지" 약속을 데이터 평면으로 확장. → [데이터 닥터 설계문서](../superpowers/specs/2026-06-13-data-doctor-design.md).

---

## 5. 증분 실행 순서 (Sequencing)

브레인스토밍 원칙 — *여러 독립 서브시스템은 분해하고, 첫 번째를 전체 사이클로 돌린다.* 한 spec/plan/branch에 5개 서브시스템을 묶으면 리뷰 불가능한 거대 변경이 된다.

```
Increment 1 (지금) ── 설정 기반 소스 척추 (A1)
   spec → plan → 구현(subagent-driven) → finish
        ▼
Increment 2 ── 타입드 페이로드 (A4)            [A2 시리즈 단일 진실원은 config spec §9에 설계]
Increment 3 ── 데이터 닥터 (C1)
Increment 4 ── 시그널 백테스트 하네스 (B1)   [분석/실행 분리의 신뢰 토대]
Increment 5 ── LLM 감성 seam (B2)            [사용자가 키·비용 승인 시 승격]
```

각 증분은 자기 spec → plan → 구현 → finish 사이클을 가진다. 본 카탈로그는 그 지도(map)다.

---

## 6. 보류 항목 — 근거 명시

| 항목 | 보류 근거 |
|---|---|
| **C2 파티션 인덱스** | `read_window` 파티션 프루닝이 이미 핫패스를 처리. 인덱스는 데이터가 수년 누적된 *뒤*의 최적화 — 지금은 시기상조(YAGNI). 신선도 닥터(C1)가 먼저 스케일 신호를 준다. |
| **C3 pykrx 타임아웃** | GRAY·옵션 소스. `BaseSource`를 안 써서 타임아웃이 없지만 영향 LOW. A3(선언적 등록)에서 자연 해소될 항목 — 단독 작업 비효율. |
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
- `append(overwrite=)` 재생성 데이터셋 last-write-wins · 원천 데이터 append-only.

**결론.** 본 작업은 *버그 수정*이 아니라 *확장성 천장 제거 + 성숙기 피드백 루프 설계*다. 그래서 구현은 추적 가능한 A1에 한정하고, 나머지는 엄밀한 설계로 남긴다.
