# S4. Mimir Historical / Event-Analog — 설계문서

> **스펙 ID**: S4
> **작성일**: 2026-05-31
> **상태**: 구현 진행
> **선행**: [S1 Collector](2026-05-31-collector-design.md) · [S2 Analysis](2026-05-31-analysis-design.md) · [로드맵](../../architecture/roadmap.md)

---

## 1. 개요

S4는 백필된 가격 이력에서 **이벤트 스터디(event-study)** 를 수행한다: 특정 이벤트(급락·거래량 급증 등)가 과거에 발생한 시점들을 찾아, 그 *이후* 수익률 분포를 계산해 "과거에 이런 일이 있었을 때 보통 어떻게 됐나"를 정량화한다. 결과는 `historical` 데이터셋으로 저장되고, 향후 리포트(S3)에 합류한다.

**한 줄 요약**: 가격 이력 → 이벤트 탐지 → 과거 발생 시점의 사후수익(1/5/20일) 분포 → HistoricalInsight.

## 2. 범위

### 포함
- `events` — 가격 시계열에서 이벤트 인덱스 탐지: 급락(일간수익률 ≤ −임계), 거래량 급증(이동평균 대비 비율)
- `analog` — 이벤트 시점들의 사후수익(forward return)을 horizon별로 계산·요약(n, 중앙값, 양(+)비율)
- `schema` — HistoricalInsight envelope (`source="mimir_historical"`, `dataset="historical"`)
- `engine` — 워치리스트 종목별·이벤트별로 base-rate 통계 + "오늘 트리거 여부"
- `history` CLI (`python -m mimir.history [--symbol S]`)

### 제외(후속)
- 거시/공시 이벤트 기반 cross-sectional 분석(어떤 *종목군*이 움직였나) — 데이터 축적 후
- 통계적 유의성 검정·룩어헤드 정밀 보정 — v1은 단순 분포 통계 + 면책

## 3. 설계 원칙
- **읽기 전용**: S1 `prices`만 소비(백필 이력 포함).
- **결정론·룩어헤드 회피**: 사후수익은 이벤트일 *이후* 종가만 사용. 최근 이벤트는 horizon 데이터가 없으면 통계에서 제외(트리거 표식만).
- **정직한 표본**: 표본 수 `n`을 항상 노출. `n`이 임계 미만이면 인사이트 생략.
- **면책**: "과거 성과가 미래를 보장하지 않음 / not financial advice".

## 4. 아키텍처
```
historical/
  events.py    detect_sharp_drops(series, threshold) · detect_volume_spikes(series, ratio, window)
  analog.py    forward_returns(series, idxs, horizons) · summarize(...) -> ForwardStats
  schema.py    HistoricalInsight + to_record
  engine.py    HistoricalEngine.run(watchlist, as_of) -> list[HistoricalInsight] (+저장)
  series.py    price_series(reader, symbol) -> list[Bar(date, close, volume)]
history.py     CLI
```
흐름: `history` → 종목별 `price_series` → 이벤트 탐지 → `analog.summarize` → HistoricalInsight → `historical` JSONL.

## 5. 핵심 타입
```python
class Bar(NamedTuple): day: date; close: float; volume: float | None
class HorizonStat(BaseModel): horizon: int; n: int; median_return: float; pct_positive: float
class HistoricalInsight(BaseModel):
    symbol; market; as_of; event_type; occurrences; triggered_today: bool
    horizons: list[HorizonStat]; examples: list[str]; disclaimer
```
- forward return(이벤트 i, horizon h) = `(close[i+h] - close[i]) / close[i]`; `i+h`가 범위를 벗어나면 제외.
- summarize: horizon별 표본 모아 median·pct_positive 계산.

## 6. 이벤트 (v1)
| 이벤트 | 정의 | 기본값 |
|---|---|---|
| **sharp_drop** | 일간수익률 ≤ −threshold | 5% |
| **volume_spike** | 거래량 > ratio × 직전 window 평균 | 2.0×, 20일 |

`MIN_OCCURRENCES = 3`: 과거 발생이 3회 미만이면 해당 이벤트 인사이트 생략.

## 7. 출력 (HistoricalInsight envelope)
```jsonc
{ "source":"mimir_historical", "dataset":"historical", "market":"US", "symbol":"AAPL",
  "ts":"2026-05-31T00:00:00Z", "idempotency_key":"historical:AAPL:sharp_drop:2026-05-31",
  "payload": { "event_type":"sharp_drop", "occurrences":12, "triggered_today":false,
    "horizons":[{"horizon":1,"n":12,"median_return":0.004,"pct_positive":0.58}, ...],
    "examples":["2024-08-05: -6.1% then +3.2% (5d)", ...],
    "disclaimer":"Past performance does not guarantee future results. Not financial advice." } }
```
`Dataset` enum에 `HISTORICAL = "historical"` 추가.

## 8. 테스트(TDD, 80%+)
- `events`: 합성 시계열에서 급락·거래량 급증 인덱스 정확 탐지.
- `analog`: 알려진 시계열에서 forward return·중앙값·양비율 계산 검증; 룩어헤드 경계(범위 밖 제외).
- `engine`: 시드 가격 이력 → MIN_OCCURRENCES 충족 시 인사이트 저장, 미만이면 생략.
- `schema`: to_record 라운드트립.

## 9. 완료 기준
1. `python -m mimir.history --symbol AAPL`가 백필 가격으로 동작하고 `data/historical/...`에 멱등 저장.
2. 이벤트 2종 + analog 요약 + 엔진 단위/통합 테스트 통과.
3. 표본 `n` 노출, MIN_OCCURRENCES 미만 생략, 룩어헤드 회피.
4. 과거성과 면책 포함.
5. 커버리지 80%+, ruff·mypy --strict clean.
