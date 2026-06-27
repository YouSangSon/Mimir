# S2. Mimir Analysis & Scoring — 설계문서

> **스펙 ID**: S2
> **작성일**: 2026-05-31
> **상태**: 구현 완료 · LLM seam/A2 macro registry 확장 반영. 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **선행**: [S1 Collector](2026-05-31-collector-design.md) · [로드맵](../../architecture/roadmap.md)

---

## 1. 개요

S2는 S1이 저장한 정규화 JSONL을 읽어, 워치리스트 종목별로 **방향성 ⭐별점 인사이트**를 만든다. 네트워크를 타지 않고 로컬 데이터만 소비하며, 결과를 새 `insights` 데이터셋(같은 envelope)으로 저장한다. S3가 이를 읽어 리포트·텔레그램으로, S5가 시그널로 소비한다.

**한 줄 요약**: 저장된 데이터 → 시그널 플러그인 → 방향성 가중 스코어러 → ⭐1~5 인사이트(근거 포함) → `insights` JSONL.

**확정 결정(사용자)**: 스코어링은 **하이브리드**(규칙 기반 우선, LLM은 off-by-default 방향성 시그널로 현재 존재). ⭐는 **방향성 포함**(강세/약세 + 확신도). 첫 시그널 4종: 공시 이벤트·뉴스 볼륨 급증·가격 모멘텀/거래량·거시 레짐.

---

## 2. 범위

### 포함
- `DataReader` — S1 JSONL을 dataset/symbol/날짜윈도우로 조회 (네트워크 없음)
- `Signal` 프로토콜 + 4종 시그널 (filing_event, news_volume, price_momentum, macro_regime)
- 방향성 가중 `scorer` — SignalResult들을 합산해 direction + ⭐(1~5) + confidence + 근거
- `Insight` 스키마 + `to_record` (envelope, `source="mimir_analysis"`, `dataset="insights"`)
- `AnalysisEngine` — 종목별 시그널 수집 → 스코어 → 저장 (데이터 없는 시그널 graceful skip)
- `analyze` CLI (`python -m mimir.analyze --date YYYY-MM-DD`)
- 면책 문구 포함
- `llm_sentiment` 시그널 seam — `llm_sentiment_enabled` + `ANTHROPIC_API_KEY` + `[llm]` extra가 모두 있을 때만 활성화되는 off-by-default 방향성 시그널

### 제외 (다음 스펙)
- 풍부한 HTML 리포트·텔레그램 다이제스트 → S3
- 과거 유사사례 매칭 → S4

---

## 3. 설계 원칙

| 원칙 | 적용 |
|---|---|
| **읽기 전용 소비** | S1 envelope만 읽음. 네트워크·수집 책임 없음 |
| **시그널 격리** | 각 시그널은 독립 단위. 데이터 없으면 `None` 반환(graceful skip) |
| **투명성** | 모든 시그널이 `reason`을 남기고, 인사이트는 근거 목록을 보존 |
| **방향성** | direction은 주로 가격·거시에서, 공시·뉴스는 주목도(confidence) 기여 |
| **확장(하이브리드)** | LLM 감성은 같은 `Signal` 인터페이스의 `llm_sentiment`로 구현되어 있으며, 비용/키 조건을 만족할 때만 활성화 |
| **면책** | 인사이트에 "not financial advice" 고지 항상 포함 |

---

## 4. 아키텍처

```
analysis/
  reader.py        DataReader: read(dataset, symbol?, since?, until?) -> list[Record]
  signals/
    base.py        SignalDirection, SignalResult, Signal 프로토콜
    filing_event.py    중요 공시(8-K / 주요사항) -> 주목도(NEUTRAL)
    news_volume.py     심볼 언급 뉴스 급증 -> 주목도(NEUTRAL)
    price_momentum.py  최근 수익률 부호 -> 강세/약세, 거래량 급등 -> confidence
    macro_regime.py    정책금리 추세 -> 시장 lean(상승=약세, 하락=강세)
  scorer.py        score(results) -> InsightScore(direction, stars, confidence, attention, reasons)
  schema.py        Insight + to_record
  engine.py        AnalysisEngine.run(watchlist, as_of) -> list[Insight] (+저장)
  builder.py       build_signals()
analyze.py         CLI
```

### 데이터 흐름
```
analyze --date D
  → watchlist 로드, DataReader(JsonlStore), build_signals()
  → 종목별: 각 시그널 evaluate(symbol, market, D, reader) (None은 건너뜀)
  → score(results) → Insight
  → store.append(to_record(insight))  # data/insights/YYYY/MM/DD.jsonl
```

---

## 5. 핵심 타입

```python
class SignalDirection(StrEnum): BULLISH; BEARISH; NEUTRAL

class SignalResult(BaseModel):
    signal: str            # 시그널 id
    direction: SignalDirection
    strength: float        # 0..1 신호의 크기
    confidence: float      # 0..1 신뢰도
    reason: str            # 투명한 근거
    weight: float = 1.0    # 합산 가중치

class Signal(Protocol):
    id: str
    def evaluate(self, symbol, market, as_of, reader) -> SignalResult | None: ...
```

### 스코어링 (방향성 가중)
```
directional_weight = Σ weight  (방향 시그널만; bullish/bearish)
total_weight       = Σ weight  (모든 시그널)
net       = Σ sign(dir)·strength·confidence·weight / directional_weight   # -1..1 방향 확신
attention = Σ strength·confidence·weight / total_weight                   # 0..1 전체 활동량
direction = BULLISH(net>ε) | BEARISH(net<-ε) | NEUTRAL
stars     = clamp(round(1 + 4·|net|), 1, 5)
confidence= Σ confidence·weight / total_weight
```
`sign`: BULLISH=+1, BEARISH=-1, NEUTRAL=0. 가격(weight 1.0)·거시(0.3)·LLM 감성(0.8, off-by-default)은 방향 기여, 공시(0.8)·뉴스(0.5)는 NEUTRAL로 attention만 기여한다. 별점은 방향 확신 `|net|`만 반영하므로, 방향 없는 활동(공시·뉴스량)이 많아도 stars는 올라가지 않는다.

---

## 6. 시그널 명세 (v1, 규칙 기반)

| 시그널 | 입력 | direction | strength | confidence | None 조건 |
|---|---|---|---|---|---|
| **filing_event** | `filings`(3일) | NEUTRAL | 중요 공시 수/3 | 0.6 | 공시 없음 |
| **news_volume** | `news`(오늘 vs 7일 baseline), 제목/요약에 심볼 매칭 | NEUTRAL | 급증비/3 | 0.5 | 매칭 0 |
| **price_momentum** | `prices`(약 7세션) | 수익률 부호(±2% 임계) | \|수익률\|/10% | 0.6, 거래량 급등시 0.85 | 가격<2점 |
| **macro_regime** | `macro`(60일, 정책금리) | 상승=BEARISH/하락=BULLISH | \|Δ\|/1.0ppt | 0.4 | 시계열<2점 |

중요 공시: US `8-K`(및 `/A`), KR `report_nm`에 "주요사항" 포함.

---

## 7. 출력 (Insight envelope)

```jsonc
{ "schema_version":1, "source":"mimir_analysis", "dataset":"insights",
  "market":"US", "symbol":"AAPL", "ts":"2026-05-31T00:00:00Z", "captured_at":"...",
  "idempotency_key":"insight:AAPL:2026-05-31",
  "payload": {
    "symbol":"AAPL", "market":"US", "as_of":"2026-05-31",
    "direction":"bullish", "stars":4, "confidence":0.78,
    "signals":[ {signal,direction,strength,confidence,reason,weight}, ... ],
    "reasons":["[price_momentum] +6.2% over 6 sessions with volume surge", ...],
    "disclaimer":"For information only. Not financial advice." } }
```

`Dataset` enum에 `INSIGHTS = "insights"` 추가. 저장은 S1의 `JsonlStore`를 그대로 재사용(멱등·날짜 파티션).

---

## 8. 에러 처리
- 시그널은 데이터가 없으면 `None`(예외 아님) — graceful skip.
- 한 종목에서 모든 시그널이 None이면 인사이트 미생성(스킵).
- 잘못된/누락 payload 필드는 시그널 내부에서 방어(없으면 skip), 엔진은 종목별로 독립.

---

## 9. 테스트 (TDD, 80%+)
- **reader**: 시드된 store에서 dataset/symbol/윈도우 필터.
- **시그널 4종**: tmp store + DataReader에 크래프트 레코드 → direction/strength/None 케이스.
- **scorer**: 강세/약세/중립 혼합 입력 → direction·stars 검증.
- **engine**: 가격 레코드 시드 → run → bullish 인사이트 저장 확인.
- **schema**: to_record 라운드트립.

---

## 10. 완료 기준
1. `python -m mimir.analyze --date D`가 저장된 데이터로 동작하고 `data/insights/...`에 멱등 저장.
2. 4종 시그널 + 스코어러 + 엔진 단위/통합 테스트 통과.
3. 데이터 없는 시그널은 graceful skip(예외 없음), 모든 시그널 None이면 종목 스킵.
4. 인사이트에 방향성·⭐(1~5)·confidence·근거·면책 포함.
5. 커버리지 80%+, ruff·mypy --strict clean.

---

## 11. 현재 LLM seam과 남은 운영 고도화

`llm_sentiment`는 같은 `Signal` 인터페이스를 구현하는 off-by-default 방향성 시그널로 현재 코드에 존재한다. 기본 경로는 유료 LLM 호출 0건이며, `llm_sentiment_enabled`, `ANTHROPIC_API_KEY`, `[llm]` extra가 모두 있을 때만 build된다. 현재 구현은 persistent LLM sentiment cache dataset을 제공하지 않는다. 남은 미래 작업은 모델 품질 개선, 비용 관측, cache 설계처럼 별도 spec이 필요한 운영 고도화다.
