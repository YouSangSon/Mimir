# 분석 시그널 & 스코어링 레퍼런스

> **상태**: 현재 구현 기준
> **최종 업데이트**: 2026-06-19
> **대상 독자**: 리포트의 ⭐별점·방향·confidence가 어떻게 산출되는지 알고 싶은 운영자, 새 시그널을 추가하는 개발자
> **관련**: 확장 방법은 [extensibility 가이드](../../architecture/extensibility/README.md), 설정은 [sources.md](../config/sources.md)

이 문서는 *현재 시그널이 무엇을 측정하고 점수가 어떻게 합쳐지는지*를 설명한다. 새 시그널을 *추가하는 방법*은 extensibility 가이드 §4를 본다.

---

## 1. 한눈에 보기

각 시그널은 `(symbol, market, as_of)`에 대해 `SignalResult | None`을 낸다. `SignalResult`는 `direction`(bullish/bearish/neutral), `strength`(0..1), `confidence`(0..1), `weight`(곱셈자, ≥0), `reason`을 담는다. `scorer.score()`가 한 symbol의 여러 `SignalResult`를 하나의 `InsightScore`(direction, ⭐stars 1..5, confidence, attention)로 합친다.

핵심 원칙: **별점은 *방향 확신*을 뜻한다.** 방향 없는 활동(공시·뉴스량)은 stars를 올리지 못하고 `attention`으로만 드러난다.

---

## 2. 현재 시그널

| 시그널 | 방향성 | weight | 기본 confidence | 측정 대상 |
|---|---|---|---|---|
| `price_momentum` | 방향성 | 1.0 | 0.6 (거래량 급증 시 0.85) | 14일 가격 모멘텀 |
| `filing_event` | 항상 NEUTRAL | 0.8 | 0.6(중요)/0.4(일반) | 최근 3일 공시 활동 |
| `news_volume` | 항상 NEUTRAL | 0.5 | — | 뉴스 언급량(활동) |
| `macro_regime` | 방향성 | 0.3 | 0.4 | 60일 금리 추세 |
| `llm_sentiment` | 방향성 | 0.8 | 볼륨 가중 | 헤드라인 감성(off-by-default) |

`weight`는 [0,1] 점수가 아니라 시그널 간 상대 중요도를 정하는 **곱셈자**다. 현재 값은 코드 상수이며 백테스트(B1)로 보정 대상이다(사용자 YAML로 노출하지 않는다 — 일관성 유지).

### 2.1 `price_momentum` (방향성, weight 1.0)

- 윈도우: `as_of` 직전 14일(`WINDOW_DAYS`). 종가 ≥2개 필요, 아니면 시그널 없음.
- 수익률 `ret = (last - first) / first`. `> +2%`면 BULLISH, `< -2%`면 BEARISH, 그 사이는 NEUTRAL(`UP_THRESHOLD=0.02`).
- `strength = min(|ret| / 0.10, 1.0)` — 10% 이동(`FULL_MOVE`)이 full strength.
- confidence 0.6. 마지막 거래량이 직전 평균의 1.5배(`VOLUME_SURGE_RATIO`)를 넘으면 0.85로 상향. 거래량이 없으면 급증 보정을 건너뛴다.

### 2.2 `filing_event` (항상 NEUTRAL, weight 0.8)

- 윈도우: 최근 3일(`LOOKBACK_DAYS`). 방향을 추정하지 않는다 — 공시는 "무슨 일이 일어남"을 알릴 뿐.
- 중요 공시(US `8-K`/`8-K/A`, KR `주요사항`)가 있으면 `strength = min(n/3, 1.0)`, confidence 0.6.
- 없으면 일반 공시로 `strength = min(n/10, 0.3)`, confidence 0.4.

### 2.3 `news_volume` (항상 NEUTRAL, weight 0.5)

- `captured_at` 기준 오늘 윈도우의 뉴스 언급량을 baseline 대비로 본다. 방향이 아니라 활동량이다.
- `analysis.news.aliases`·기본 alias·symbol-tagged RSS feed를 같은 matcher로 해석한다([sources.md](../config/sources.md) §3.1).

### 2.4 `macro_regime` (방향성, weight 0.3)

- 윈도우: 60일(`WINDOW_DAYS`). `analysis.macro_regime.rate_series`(또는 기본 rate-series)의 금리 추세를 본다.
- **금리 상승 → BEARISH, 하락 → BULLISH**(역방향). `delta = last - first`, 1e-9 epsilon.
- `strength = min(|delta| / 1.0, 1.0)`(`FULL_DELTA=1.0`pp), confidence 0.4.

### 2.5 `llm_sentiment` (방향성, weight 0.8, off-by-default)

- 세 조건(`llm_sentiment_enabled`+`ANTHROPIC_API_KEY`+`[llm]` extra)이 모두 맞을 때만 등록된다([sources.md](../config/sources.md) §6).
- 헤드라인별 verdict의 confidence-가중 평균 부호(`mean_signed`)로 방향(±0.02 epsilon), `strength = min(|mean_signed|, 1.0)`.
- confidence는 볼륨으로 다운웨이트: `volume_factor = min(n / 3, 1.0)`(`FULL_CONFIDENCE_VOLUME=3`) — 1건이면 1/3로 줄인다.

---

## 3. 스코어링 (`scorer.score`)

여러 `SignalResult`를 하나로 합친다.

```
directional_weight = Σ weight  (방향 시그널만; bullish/bearish)
total_weight       = Σ weight  (모든 시그널)
net        = Σ (sign · strength · confidence · weight) / directional_weight   ∈ [-1, 1]
attention  = Σ (strength · confidence · weight) / total_weight
confidence = Σ (confidence · weight) / total_weight
```

`sign`은 bullish +1 / bearish −1 / neutral 0.

- **direction**: `net > +0.02`면 BULLISH, `< −0.02`면 BEARISH, 그 사이는 NEUTRAL(`DIRECTION_EPS=0.02`).
- **stars**: `max(1, min(5, round(1 + 4·|net|)))` — 방향 확신의 크기.
- **attention**: 방향과 무관한 가중 활동량(중립 시그널이 여기 기여).

### 3.1 왜 `net`을 *방향* weight로만 나누나

`news_volume`·`filing_event`는 항상 NEUTRAL이라 numerator에 0을 기여한다. 만약 `net`을 `total_weight`로 나누면, 활동 시그널을 추가하는 것만으로 실제 방향 시그널의 별점이 희석된다(같은 강세 근거가 5★→3★). 그래서 `net`은 **방향 시그널 weight로만 정규화**해, 활동량이 방향 확신을 깎아내리지 않게 한다. 활동량은 `attention`에 별도로 드러난다. `|net| ≤ 1`은 유지된다(중립 항이 numerator에 0이므로).

시그널이 하나도 없으면 NEUTRAL·1★·confidence 0·attention 0을 낸다.

---

## 4. 분석/실행 경계

모든 인사이트·평가에는 "투자 권유가 아님" 면책이 붙는다. 시그널은 *발행*만 하고, 주문 실행은 별도 엔진이 읽기 전용으로 소비한다([로드맵](../../architecture/roadmap.md) §6). 시그널이 검증되는지는 평가 하네스(B1, `mimir evaluate`)가 사후수익 적중률·엣지로 측정한다.
