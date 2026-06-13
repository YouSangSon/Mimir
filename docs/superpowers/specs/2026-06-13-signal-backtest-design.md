# Increment 4. 시그널 백테스트·평가 하네스 — 설계

> **스펙 ID**: INC4 (카탈로그 B1)
> **작성일**: 2026-06-13
> **상태**: 설계(미구현) — 사용자 승인 시 plan→구현 승격
> **선행**: [발전 카탈로그](../../architecture/improvement-catalog.md) · [S4 Historical](2026-05-31-historical-design.md)

---

## 1. 목적

Mimir는 매일 `insights` 데이터셋에 시그널을 *발행*한다(`Insight`: `direction`/`stars`/`confidence`/구성 `signals`). 그러나 그 시그널이 **실제로 forward return(사후수익)을 예측하는지** 측정하는 피드백 루프가 없다. S4(event-study)는 "과거에 이런 *가격 이벤트*가 있었을 때 보통 어떻게 됐나"를 보지만, "우리 *인사이트*의 과거 적중률"은 보지 않는다.

INC4는 발행된 인사이트를 **읽기 전용으로** 다시 채점한다: 각 인사이트를 그 `as_of` *이후*의 실제 가격과 대조해 **방향 적중률(directional hit-rate)** 과 **평균 사후수익**을 horizon(1/5/20 거래봉)별로 집계한다. 결과는 새 `evaluation` 데이터셋으로 저장된다. 이로써 Mimir는 "시그널 발행"에서 "*검증된* 시그널 발행"으로 올라가며, 이것이 미래 S5(자동매매)의 신뢰 토대가 된다.

**한 줄 요약**: 발행된 `insights` + `prices` 이력 → as_of 이후 사후수익 대조 → 시그널/방향/별점별 적중률·평균수익(n) → `EvaluationReport`.

## 2. 범위

### 포함
- `evaluation/metrics.py` — S4의 `forward_returns`를 **재사용**해 방향 인지(direction-aware) 적중률·평균수익을 계산. 신규 집계 단위: `per-signal`, `per-direction`, `per-star`.
- `evaluation/schema.py` — `EvaluationReport`/`BucketStat` envelope (`source="mimir_evaluation"`, `dataset="evaluation"`).
- `evaluation/engine.py` — 저장된 `insights`(≤ as_of) × `prices`(≤ as_of) → 버킷별 통계 → `evaluation` JSONL 저장.
- `mimir/evaluate.py` — CLI (`python -m mimir.evaluate [--date YYYY-MM-DD]`), `history.py` 미러.
- 리포트 합류: `deliver.py`가 `Dataset.EVALUATION`을 읽어 `daily_report`에 "시그널 성적표" 섹션 추가.

### 제외(후속)
- 슬리피지·수수료·체결 모델, 포지션 사이징, 손익 시뮬레이션 — S4가 유의성 검정을 미룬 것과 동일하게 보류.
- 통계적 유의성 검정(t-검정·신뢰구간) — v1은 단순 분포 통계 + 면책.
- S5 실행 레이어 자체 — 본 스펙은 *track record를 만드는 것*까지만. (§11)

## 3. 설계 원칙 (하드 원칙 준수)

| 원칙 | 본 설계에서의 구현 |
|---|---|
| **free** | 네트워크 호출 없음. 저장된 `insights`+`prices` JSONL만 소비. 추가 유료 서비스 0. |
| **legal** | 원천 수집이 아니라 *이미 저장된* 데이터의 재집계이므로 per-source 라이선스 영향 없음. |
| **analysis/execution 분리** | **읽기 전용** 모듈. `DataReader`로만 읽고 order/broker API를 **절대** 호출하지 않음. 평가는 read-only 신호일 뿐. |
| **no silent failures** | 모든 버킷이 표본 부족으로 게이팅되면 빈 성공이 아니라 "insufficient sample"을 명시(§7). horizon별 `n`을 항상 노출. |
| **immutability** | 입력 `Record`/`Insight`를 변형하지 않고 새 `BucketStat`/`EvaluationReport`를 생성. pydantic v2 frozen 스타일. |
| **룩어헤드 회피** | 각 인사이트는 `as_of` *직후* 봉부터만 평가(§5). S4의 정보 장벽과 동일 원리. |

## 4. 아키텍처

```
mimir/evaluation/
  metrics.py   anchor_index(series, as_of) · evaluate_bucket(...) -> BucketStat | None
               └ forward_returns(series, [anchor], h)  ← S4 analog.py 재사용 (재구현 금지)
  schema.py    BucketStat · EvaluationReport · to_record  (envelope)
  engine.py    EvaluationEngine.run(as_of) -> EvaluationReport (+저장, overwrite=True)
mimir/evaluate.py   CLI (history.py 미러)
```

흐름:
```
evaluate → DataReader.read(INSIGHTS, until=as_of)        # 발행된 모든 인사이트
         → DataReader.read(PRICES,   until=as_of)        # 가격 이력 (룩어헤드 차단)
         → 인사이트별: anchor = as_of 직후 첫 봉 인덱스
         → forward_returns(series, [anchor], h)          # S4 원시 사후수익 재사용
         → 방향 부호 적용 → 버킷(signal/direction/star)에 적립
         → evaluate_bucket → BucketStat (n ≥ MIN_EVAL_N 인 horizon만)
         → EvaluationReport → data/evaluation/YYYY/MM/DD.jsonl
```

S4와의 의존 관계: `mimir.historical.analog.forward_returns`, `mimir.historical.series.bars_from_records`/`price_series`를 **그대로 import 해서 재사용**한다. 사후수익 산식(`(close[i+h]-close[i])/close[i]`, `i+h < len` 경계)을 **복제하지 않는다**.

## 5. 룩어헤드 규율 (핵심)

인사이트는 `as_of`(date)로 키잉되지만 `forward_returns`는 정수 인덱스를 받는다. 둘을 잇는 단 하나의 함수가 룩어헤드 장벽이다.

```python
def anchor_index(series: list[Bar], as_of: date) -> int | None:
    """Index of the first bar STRICTLY AFTER as_of (entry point for evaluation).

    The insight's information set ends at as_of's close, so the earliest price
    we may score against is the next available bar. Returns None if no such bar
    exists yet (too-recent insight) → that insight contributes nothing.
    """
    for i, bar in enumerate(series):
        if bar.day > as_of:
            return i
    return None
```

- **S4 대비 정확한 표현**: S4는 `price_series(reader, symbol, until=as_of)`로 *탐지*가 미래를 못 보게 한다. INC4는 인사이트의 정보 집합이 이미 `as_of`에서 끝났으므로 *평가 진입(entry)* 을 `as_of` **직후**부터 시작한다 — 같은 정보 장벽을 *평가 시점*에 적용.
- anchor를 구한 뒤 `forward_returns(series, [anchor], h)`에 그대로 넘긴다. `j = anchor + h ≥ len(series)`면 S4의 경계 검사가 자동으로 그 관측을 탈락시킨다 → **너무 최근이라 forward 봉이 없는 인사이트는 관측 단위에서 자연 제외**(추가 코드 불필요).
- 따라서 룩어헤드는 두 겹으로 차단된다: (a) `until=as_of`로 series를 자르고, (b) anchor가 `as_of` *직후*를 가리킨다.

## 6. 메트릭 정의 (방향 인지 — 가장 정밀해야 할 절)

> **주의**: S4의 `summarize`/`pct_positive`(= 사후수익 > 0 비율)는 **방향 무관**이라 hit-rate에 부적합하다. -8%를 맞춘 *bearish* 인사이트는 적중이지만 수익은 음수다. 그래서 `forward_returns`(원시 수익 + 경계 검사)만 재사용하고, hit-rate/평균은 아래 부호 적용 식으로 새로 정의한다.

한 horizon `h`의 버킷(관측 집합 `O`)에 대해, 각 관측 `o`는 (인사이트 방향 `d`, 사후수익 `r`)을 가진다. **방향 부호화 수익(directional edge)**:

```
sign(d) = DIRECTION_SIGN[d]   # bullish=+1, bearish=-1, neutral=0  (signals/base.py 재사용)
e(o)    = sign(d) * r
```

| 메트릭 | 산식 | 비고 |
|---|---|---|
| `n` | `len(O)`  (해당 horizon에서 forward 봉이 존재하는 관측 수) | 항상 노출 |
| `hit_rate` | `|{ o ∈ O : e(o) > 0 }| / n` | 방향이 맞았으면 적중. `e=0`(neutral 또는 r=0)은 분자 비포함 |
| `mean_fwd_return` | `(1/n) · Σ e(o)` | **부호화 수익의 평균 = "방향 엣지"**. pure-bullish 버킷에선 원시 평균과 동일 |

**neutral 처리(명시)**: `neutral` 방향 인사이트는 `sign=0 → e=0`이라 hit에 절대 기여하지 않는다. 이들이 분모 `n`을 부풀려 적중률을 희석하는 것을 막기 위해, **방향 버킷팅에서 neutral 관측은 hit-rate/mean 계산 표본에서 제외**한다(별도 `neutral_n`으로만 노출). 즉 적중률은 *방향성 있는 콜*에 대해서만 계산한다.

**평균 수익 규약(명시)**: per-star·per-signal 버킷은 bullish/bearish가 **섞인다**. 원시 평균 사후수익은 서로 상쇄되어 오해를 부른다. 따라서 세 차원 모두에서 단일하게 **부호화 수익 `e`의 평균**을 쓴다(= 방향 엣지). 이는 pure-bullish 버킷에서 원시 평균과 일치하므로 별도 분기가 필요 없다.

**거래봉 단위 명시**: horizon은 *거래봉(trading bars)* 수이지 달력일이 아니다(주말·공휴일 자동 스킵 — series가 봉 단위이므로).

### 6.1 집계 차원 (3종)

| 차원(`dimension`) | 버킷 키(`key`) | 키 출처 |
|---|---|---|
| `per_signal` | `SignalResult.signal` (예: `"momentum"`) | 인사이트의 **구성 시그널**. 한 인사이트가 여러 버킷에 기여 |
| `per_direction` | `Insight.direction` (`bullish`/`bearish`) | 인사이트 단위(집계 방향) |
| `per_star` | `str(Insight.stars)` (`"1"`..`"5"`) | 인사이트 단위 |

- **per-signal이 가능한 이유(명시)**: `Insight.to_record`가 `payload`에 `model_dump(mode="json")`로 `signals: list[SignalResult]`를 직렬화해 저장한다. 평가 시 `Insight.model_validate(record.payload)`로 복원하면 구성 시그널이 살아 돌아온다. per-signal 버킷팅은 각 `SignalResult`의 **자기 `direction`**(집계 인사이트 방향이 아님)으로 부호화한다 — 한 인사이트가 여러 시그널 버킷에 동시에 기여한다.
- **market 처리**: 버킷은 시장 혼합을 피하기 위해 `market`(US/KR)별로 분리해 집계하고, `BucketStat.market`에 노출한다. 시장 무관 합산은 하지 않는다(가격 스케일·통화·세션이 달라 의미가 흐려짐).

### 6.2 표본 게이팅

```python
MIN_EVAL_N = 5   # horizon별 관측 수가 이 미만이면 그 horizon 통계를 버림 (S4 MIN_HORIZON_N 미러)
```
- horizon 단위로 게이팅: `n < MIN_EVAL_N`인 horizon은 `BucketStat.horizons`에서 제외.
- 모든 horizon이 탈락한 버킷은 리포트에서 생략.
- S4의 `MIN_HORIZON_N=2`보다 보수적으로 5를 택함(적중률은 비율 통계라 소표본 변동이 더 위험).

## 7. 핵심 타입 & 출력

```python
# evaluation/schema.py
from datetime import date
from pydantic import BaseModel
from mimir.core.source import Market
from mimir.analysis.signals.base import SignalDirection

DISCLAIMER = "Backtest hit-rate is descriptive, not predictive. Not financial advice."
EVALUATION_SOURCE = "mimir_evaluation"

class HorizonEval(BaseModel):
    horizon: int          # trading bars (1/5/20)
    n: int                # directional observations with a forward bar
    hit_rate: float       # |{ e > 0 }| / n
    mean_fwd_return: float# mean of signed return e
    neutral_n: int        # observations excluded from hit-rate (sign=0)

class BucketStat(BaseModel):
    dimension: str        # "per_signal" | "per_direction" | "per_star"
    key: str              # e.g. "momentum" | "bullish" | "4"
    market: Market
    horizons: list[HorizonEval]

class EvaluationReport(BaseModel):
    as_of: date
    insights_evaluated: int     # total insights read (≤ as_of)
    buckets: list[BucketStat]   # gated; may be [] on cold-start
    sufficient: bool            # False when every bucket was gated out
    disclaimer: str = DISCLAIMER
```

`Dataset` enum에 `EVALUATION = "evaluation"` 추가. envelope(`to_record`)는 **버킷 단위 1 레코드**(symbol 무관 집계이므로 `symbol=None` — `Record.symbol: str | None`):

```python
def to_record(stat: BucketStat, as_of: date, captured_at: datetime) -> Record:
    return Record(
        source=EVALUATION_SOURCE,
        dataset=Dataset.EVALUATION,
        market=stat.market,
        symbol=None,
        ts=datetime(as_of.year, as_of.month, as_of.day, tzinfo=UTC),
        captured_at=captured_at,
        idempotency_key=f"evaluation:{stat.dimension}:{stat.key}:{stat.market.value}:{as_of.isoformat()}",
        payload=stat.model_dump(mode="json"),
    )
```

```jsonc
// data/evaluation/2026/06/13.jsonl  (한 줄 예시)
{ "source":"mimir_evaluation", "dataset":"evaluation", "market":"US", "symbol":null,
  "ts":"2026-06-13T00:00:00Z",
  "idempotency_key":"evaluation:per_signal:momentum:US:2026-06-13",
  "payload": { "dimension":"per_signal", "key":"momentum", "market":"US",
    "horizons":[
      {"horizon":1,"n":31,"hit_rate":0.55,"mean_fwd_return":0.003,"neutral_n":4},
      {"horizon":5,"n":28,"hit_rate":0.61,"mean_fwd_return":0.012,"neutral_n":4}
    ] } }
```

저장은 `JsonlStore.append(records, overwrite=True)` — 같은 날 재실행 시 최신 계산이 last-write-wins(insights/historical과 동일 정책).

**콜드스타트(명시)**: 발행 이력이 짧아 모든 버킷이 게이팅되면 `sufficient=False`, `buckets=[]`로 저장하고 CLI/리포트가 "표본 부족(insufficient sample)"을 출력한다 — "어떤 시그널도 안 통한다"로 오독되는 빈 성공을 만들지 않는다(no silent failure).

## 8. 엔진 의사코드

```python
class EvaluationEngine:
    def __init__(self, reader: DataReader, store: JsonlStore) -> None:
        self._reader, self._store = reader, store

    def run(self, as_of: date, captured_at: datetime | None = None) -> EvaluationReport:
        captured_at = captured_at or datetime.now(UTC)
        insights = [Insight.model_validate(r.payload)
                    for r in self._reader.read(Dataset.INSIGHTS, until=as_of)]
        # 가격은 종목별 1회 적재 후 버킷 (S4 engine.py의 by_symbol 패턴 재사용)
        bars_by_symbol = self._load_bars(until=as_of)          # bars_from_records 재사용

        acc: dict[tuple[str, str, Market], list[Obs]] = defaultdict(list)
        for ins in insights:
            series = bars_by_symbol.get(ins.symbol, [])
            anchor = anchor_index(series, ins.as_of)
            if anchor is None:
                continue                                       # 너무 최근 → 관측 없음
            self._accumulate(acc, ins, series, anchor)         # 3차원 버킷에 적립
        buckets = [s for s in (evaluate_bucket(k, obs) for k, obs in acc.items()) if s]
        report = EvaluationReport(as_of=as_of, insights_evaluated=len(insights),
                                  buckets=buckets, sufficient=bool(buckets))
        self._store.append([to_record(b, as_of, captured_at) for b in buckets], overwrite=True)
        return report
```

`evaluate_bucket`은 horizon별로 `forward_returns(series, [anchor]…)` 결과를 모아 §6 산식을 적용하고 `MIN_EVAL_N` 게이팅 후 `BucketStat`을 만든다(없으면 `None`).

## 9. 리포트 합류 (실제 seam)

- `mimir/deliver.py`: 기존 `reader.read(Dataset.HISTORICAL, since=as_of, until=as_of)` 옆에 `reader.read(Dataset.EVALUATION, since=as_of, until=as_of)` 추가 → `BucketStat` 복원.
- `mimir/report/daily_report.py`: `build_report_html(...)`에 `evaluation: list[BucketStat] | None = None` 파라미터 추가 + `_evaluation_section`(시그널 성적표 표) 생성, `historical_section` 아래 배치.
- `mimir/report/i18n.py`: 신규 키 `evaluation_section_heading`, `evaluation_bucket_row`(예: `"{key}: {horizon}d hit {hit}% / edge {edge}% (n={n})"`)를 en/ko/zh 3종 추가(기존 `historical_*` 패턴 미러).
- 텔레그램 다이제스트(`digest.py`)에는 별점 4~5 시그널의 5d 적중률 한 줄 요약을 옵션으로 노출(과밀 방지 위해 상위 N개만).

## 10. 수용 기준

1. `python -m mimir.evaluate --date 2026-06-13`이 네트워크 없이 저장된 `insights`+`prices`만으로 동작하고 `data/evaluation/YYYY/MM/DD.jsonl`에 멱등(overwrite) 저장.
2. **방향 인지 정확성**: bearish 인사이트가 음의 사후수익을 냈을 때 hit으로 집계됨(부호화 수익 `e>0`). neutral 관측은 hit-rate 분모에서 제외되고 `neutral_n`에만 카운트.
3. **룩어헤드 회피**: 인사이트는 `as_of` *직후* 봉부터만 평가. `as_of`와 같은 날/이전 종가는 평가 진입점이 될 수 없음(테스트로 고정).
4. **표본 게이팅**: `n < MIN_EVAL_N` horizon은 출력에서 제외. 모든 버킷 탈락 시 `sufficient=False` + "insufficient sample" 표기(빈 성공 금지).
5. **재사용 검증**: 사후수익 계산이 `mimir.historical.analog.forward_returns`를 호출(재구현 아님) — import 추적으로 확인.
6. per-signal/per-direction/per-star 3차원 모두 산출, market별 분리, `n` 항상 노출, 면책 포함.
7. 리포트에 "시그널 성적표" 섹션이 en/ko/zh로 렌더.
8. 커버리지 80%+, `ruff` clean, `mypy --strict` clean, 모든 파일 <800줄.

## 11. 테스트 계획 (TDD, 합성 데이터 · 네트워크 없음)

| 대상 | 케이스 |
|---|---|
| `anchor_index` | as_of와 동일/이전 날짜는 anchor 아님(직후 첫 봉 반환); 직후 봉이 없으면 `None`. |
| `metrics` (적중률) | bullish+상승 → hit; bullish+하락 → miss; **bearish+하락 → hit**; bearish+상승 → miss. |
| `metrics` (neutral) | neutral 관측이 hit-rate 분모서 제외되고 `neutral_n`에 집계됨. |
| `metrics` (mean edge) | pure-bullish 버킷의 `mean_fwd_return`이 원시 평균과 일치; 혼합 버킷은 부호화 평균. |
| `metrics` (재사용) | 동일 series·anchor에 대해 `forward_returns`와 수치 일치(경계 `i+h≥len` 탈락 포함). |
| 게이팅 | `n < MIN_EVAL_N` horizon 제외; 전 버킷 탈락 시 `sufficient=False`. |
| `engine` (통합) | 합성 insights JSONL + prices JSONL 시드 → 3차원 버킷 저장; 멱등 재실행(overwrite) 시 레코드 수 불변. |
| per-signal | 다중 시그널 인사이트가 각 시그널 버킷에 *그 시그널의 방향*으로 기여. |
| `schema` | `to_record` 라운드트립(`symbol=None`, idempotency_key 형식). |
| 룩어헤드 회귀 | 미래 봉을 series에 넣어도 `until=as_of`+anchor로 평가에 안 새는지. |

합성 픽스처: 결정론적 가격 series(상승/하락/혼합 구간)와 알려진 방향의 인사이트를 손으로 구성해 적중/평균을 산술로 검산.

## 12. S5(자동매매)로의 연결 — *짓지 않고* 토대만

본 스펙은 S5를 **구현하지 않는다.** 대신 [매매 시임(trading-seam)](2026-05-31-trading-seam.md)이 정의한 분석/실행 경계 위에서, S5가 **검증된 track record를 가진 시그널만** 채택하도록 *게이트*를 제공한다:

- `evaluation` 데이터셋이 시간에 따라 누적되면, 각 시그널/방향/별점 버킷의 적중률 추세가 생긴다 → S5는 "예: 5d 적중률 ≥ X, n ≥ Y인 시그널만 실행 후보"라는 **읽기 전용 게이트**를 걸 수 있다.
- 핵심 불변식 유지: 평가는 read-only 신호일 뿐 order/broker를 호출하지 않는다. S5가 등장하더라도 *실행 결정*은 별도 레이어이고, 본 하네스는 그 레이어가 신뢰할 *증거*만 생산한다.
- v1에서 비용/슬리피지/유의성을 의도적으로 보류했으므로, S5 설계 시 이들을 명시적으로 추가해야 한다(본 스펙의 적중률을 그대로 PnL로 해석 금지 — 면책에 반영).
