# `config/sources.yaml` 설정 레퍼런스

> **상태**: 현재 구현 기준
> **최종 업데이트**: 2026-06-16
> **대상 독자**: 로컬 실행자, GitHub Actions 운영자, 새 데이터 커버리지를 추가하는 개발자

---

## 1. 한눈에 보기

`sources.yaml`은 어떤 소스를 켤지, 어떤 언어로 리포트를 만들지, 어떤 외부 시리즈와 RSS 피드를 수집할지, 수집된 데이터를 분석 시그널이 어떻게 해석할지 정한다. 잘못된 최상위 키, `sources:` 블록, `analysis:` 블록은 조용히 무시하지 않는다. 파서가 실패시키고 CLI가 `invalid sources.yaml` 메시지를 낸다.

```yaml
gray_enabled: true
disabled_ids: []
lang: en
llm_sentiment_enabled: false
llm_sentiment_max_headlines: 50

# Optional. Omit to inherit the macro-series registry default.
analysis:
  news:
    use_default_aliases: true
    aliases:
      AAPL: ["Apple", "Apple Inc."]
      MSFT: ["Microsoft", "Microsoft Corp."]
  macro_regime:
    rate_series: ["DGS10", "FEDFUNDS", "722Y001.0101000"]

# Optional. Omit each source block to keep that source's code default.
sources:
  fred:
    series: ["DGS10", "FEDFUNDS", "CPIAUCSL"]
  ecos:
    series:
      - { stat_code: "722Y001", cycle: "M", item_code: "0101000" }
  rss:
    feeds:
      - { url: "https://www.sec.gov/news/pressreleases.rss", publisher: "SEC", market: "US" }
      - { url: "https://example.com/aapl.rss", publisher: "Example", market: "US", symbol: "AAPL" }
```

---

## 2. 최상위 키

| 키 | 타입 | 기본값 | 의미 |
|---|---|---|---|
| `gray_enabled` | boolean | `true` | GRAY 소스(예: pykrx)를 실행할지 정한다 |
| `disabled_ids` | string list | `[]` | 특정 소스 id를 끈다. 예: `["dart", "rss"]` |
| `lang` | string | `en` | 리포트 언어. 허용 값은 `en`, `ko`, `zh` |
| `llm_sentiment_enabled` | boolean | `false` | 유료 LLM 뉴스 감성 시그널을 분석 단계에 추가할지 정한다 |
| `llm_sentiment_max_headlines` | integer | `50` | 한 실행에서 LLM으로 분류할 최대 headline 수 |

위 표의 최상위 키와 `sources`, `analysis` 외의 키는 설정 오류로 처리한다. `analysis`를 `analysys`처럼 잘못 쓰면 기본값으로 조용히 돌아가지 않고 실패한다.

`lang`에 허용되지 않은 값이 들어오면 렌더러는 `en`으로 정규화한다. 이는 잘못된 설정이 `<html lang="...">` 속성에 직접 들어가는 일을 막기 위한 방어다.

---

## 3. `analysis:` 블록

`analysis:` 블록은 이미 수집한 데이터를 분석 시그널이 어떻게 해석할지 정한다. 수집 대상 자체를 늘리지는 않는다.

### 3.1 News aliases

```yaml
analysis:
  news:
    aliases:
      AAPL: ["Apple", "Apple Inc."]
      MSFT: ["Microsoft", "Microsoft Corp."]
      NVDA: ["NVIDIA", "Nvidia Corporation"]
      "005930": ["Samsung Electronics", "삼성전자"]
```

Mimir는 기본 watchlist의 핵심 symbol에 대해 보수적인 내장 alias를 기본으로 사용한다. 현재 기본값은 `AAPL`, `MSFT`, `NVDA`, `"005930"`의 대표 회사명이다. `aliases`는 여기에 사용자 회사명 표기를 추가하는 목록이다. RSS는 계속 공식 feed의 제목과 요약 metadata만 저장한다. 이 설정은 저장된 텍스트를 분석 단계에서 어떻게 해석할지만 바꾼다.

종목별 RSS feed를 이미 알고 있다면 `sources.rss.feeds[].symbol`을 쓰는 편이 더 직접적이다. 이 값은 수집된 record의 top-level symbol이 되며, 뉴스 matcher는 제목·요약 텍스트보다 이 symbol을 먼저 확인한다.

| 필드 | 의미 |
|---|---|
| `use_default_aliases` | 내장 alias를 쓸지 정한다. 기본값은 `true` |
| `AAPL`, `"005930"` 같은 key | watchlist symbol |
| list 안의 문자열 | 제목과 요약에서 추가로 찾을 회사명 또는 표기 |

`news_volume`은 record symbol, symbol 텍스트, alias를 모두 찾는다. 예를 들어 제목에 `AAPL`이 없어도 symbol-tagged feed에서 온 record이거나 기본 alias인 `Apple`이 있으면 `AAPL` 관련 뉴스로 셀 수 있다. 사용자 alias는 기본 alias 뒤에 추가되고, 같은 symbol 안의 중복은 대소문자 무시 기준으로 제거된다.

기본 alias를 끄고 직접 지정한 alias만 쓰려면 아래처럼 설정한다.

```yaml
analysis:
  news:
    use_default_aliases: false
    aliases:
      AAPL: ["Cupertino company"]
```

LLM 감성 시그널도 같은 alias matcher를 사용한다. 단, alias 설정만으로 LLM 호출이 켜지지는 않는다. LLM 감성 시그널은 여전히 `llm_sentiment_enabled`, `ANTHROPIC_API_KEY`, `[llm]` extra 세 조건이 모두 맞을 때만 등록된다.

Alias는 너무 넓게 잡으면 오탐을 만들 수 있다. `Apple`, `Meta`, `ON`처럼 일반 단어와 겹치는 이름은 feed 맥락을 보고 보수적으로 넣어야 한다. matcher는 단어 안쪽 매칭을 막지만, 사람이 보기에도 애매한 alias의 의미까지 판단하지는 않는다.

### 3.2 Macro regime rate series

```yaml
analysis:
  macro_regime:
    rate_series: ["DGS10", "FEDFUNDS", "722Y001.0101000"]
```

`rate_series`는 macro regime 시그널이 정책금리나 벤치마크 금리로 해석할 시리즈 id 목록이다. 이 목록에 있는 시리즈만 시장 전체의 risk-on/risk-off 방향 판단에 영향을 준다. `analysis:` 블록을 생략하면 `mimir/core/macro_series.py`의 registry 기본값을 사용한다.

이 설정은 `sources.fred.series`와 다르다. `sources.fred.series`는 무엇을 수집할지 정한다. `analysis.macro_regime.rate_series`는 수집된 macro 데이터 중 무엇을 금리 regime 신호로 사용할지 정한다.

예를 들어 `CPIAUCSL`은 수집할 수 있지만 기본 rate-series에는 없다. CPI는 물가지표이고, `MacroRegimeSignal`이 보는 정책금리 변화와 같은 의미로 해석하면 안 되기 때문이다.

---

## 4. `sources:` 블록

`sources:` 블록은 FRED, ECOS, RSS의 커버리지를 파이썬 코드 수정 없이 늘리는 설정이다. 블록을 생략하면 코드 기본값을 쓴다.

### 4.1 FRED

```yaml
sources:
  fred:
    series: ["DGS10", "FEDFUNDS", "CPIAUCSL", "T10Y2Y", "UNRATE"]
```

`series`는 FRED series id 목록이다. FRED API key가 없으면 `fred` 소스 자체가 실행되지 않는다. key가 있고 `series`가 없으면 코드 기본값인 `DGS10`, `FEDFUNDS`, `CPIAUCSL`을 수집한다.

### 4.2 ECOS

```yaml
sources:
  ecos:
    series:
      - stat_code: "722Y001"
        cycle: "M"
        item_code: "0101000"
```

| 필드 | 의미 |
|---|---|
| `stat_code` | 한국은행 ECOS 통계 코드 |
| `cycle` | 주기. `D`, `M`, `Q`, `A` 형식을 사용한다 |
| `item_code` | 통계 항목 코드 |

ECOS API key가 없으면 `ecos` 소스 자체가 실행되지 않는다.

### 4.3 RSS

```yaml
sources:
  rss:
    feeds:
      - url: "https://www.sec.gov/news/pressreleases.rss"
        publisher: "SEC"
        market: "US"
      - url: "https://example.com/aapl.rss"
        publisher: "Example"
        market: "US"
        symbol: "AAPL"
```

RSS는 공식 feed의 제목과 요약 metadata만 저장한다. 기사 본문 전문을 가져오지 않는다. LLM 뉴스 감성 시그널도 저장된 제목과 요약만 사용한다.

| 필드 | 필수 | 의미 |
|---|---|---|
| `url` | 예 | RSS feed URL |
| `publisher` | 예 | payload에 저장할 발행자 이름 |
| `market` | 예 | payload에 저장할 feed market. record envelope market은 source 특성상 `GLOBAL`이다 |
| `symbol` | 아니오 | 이 feed가 특정 watchlist symbol 전용일 때 쓰는 값. 공백은 제거하고 빈 값은 오류로 처리한다 |

`symbol`이 없으면 기존처럼 일반 뉴스 feed로 저장한다. idempotency key도 기존 형식인 `rss:{link}`를 유지한다.

`symbol`이 있으면 `RawRecord.symbol`에 그 값을 넣고, idempotency key는 `rss:{symbol}:{link}`가 된다. 같은 URL이 `AAPL` feed와 `MSFT` feed에 동시에 있어도 두 symbol 관계가 dedup으로 사라지지 않는다.

---

## 5. 끄는 방법

소스를 끌 때는 빈 `series: []` 대신 `disabled_ids`를 쓴다.

```yaml
disabled_ids: ["rss", "dart"]
```

이 규칙은 설정의 뜻을 하나로 유지하기 위한 것이다. `sources.fred.series`는 "어떤 시리즈를 수집할지"를 말하고, `disabled_ids`는 "소스 자체를 실행하지 말지"를 말한다.

---

## 6. LLM 감성 시그널

LLM 감성 시그널은 세 조건이 모두 맞을 때만 켜진다.

1. `llm_sentiment_enabled: true`
2. `ANTHROPIC_API_KEY` 환경변수 존재
3. `[llm]` extra 설치로 `anthropic` package 사용 가능

기본값은 `false`다. 이 기본값은 프로젝트의 무료 실행 원칙을 지키기 위한 것이다. 설정만 켜고 key나 package가 없으면 경고를 남기고 시그널을 등록하지 않는다.

---

## 7. 잘못된 설정 예시

아래 설정은 실패해야 한다.

```yaml
sources:
  fred:
    serie: ["DGS10"]     # 오타. series가 맞다.
```

```yaml
sources:
  ecos:
    series:
      - { cycle: "M", item_code: "0101000" }  # stat_code 누락
```

```yaml
sources: "fred"          # sources는 mapping이어야 한다.
```

```yaml
analysis:
  news:
    use_defaults_aliases: false  # 오타. use_default_aliases가 맞다.
```

```yaml
analysis:
  news:
    aliasez: { AAPL: ["Apple"] }  # 오타. aliases가 맞다.
```

```yaml
analysis:
  news:
    aliases:
      AAPL: "Apple"  # aliases 값은 문자열 하나가 아니라 문자열 list여야 한다.
```

```yaml
sources:
  rss:
    feeds:
      - { url: "https://x/feed.rss", publisher: "Example", market: "US", symbl: "AAPL" }
      # 오타. symbol이 맞다. RSS feed 항목의 알 수 없는 필드는 오류다.
```

```yaml
sources:
  rss:
    feeds:
      - { url: "https://x/feed.rss", publisher: "Example", market: "US", symbol: "   " }
      # symbol은 공백만 있으면 안 된다.
```

```yaml
analysis:
  macro_regime:
    rate_seriez: ["DGS10"]  # 오타. rate_series가 맞다.
```

```yaml
analysys:
  macro_regime:
    rate_series: ["DGS10"]  # 오타. analysis가 맞다.
```

실패를 빠르게 내는 이유는 명확하다. 설정 오타가 조용히 기본값으로 돌아가면 사용자는 새 시리즈가 수집되거나 분석에 반영된다고 믿지만 실제 동작은 바뀌지 않는다.
