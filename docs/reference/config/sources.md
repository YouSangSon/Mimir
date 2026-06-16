# `config/sources.yaml` 설정 레퍼런스

> **상태**: 현재 구현 기준
> **최종 업데이트**: 2026-06-16
> **대상 독자**: 로컬 실행자, GitHub Actions 운영자, 새 데이터 커버리지를 추가하는 개발자

---

## 1. 한눈에 보기

`sources.yaml`은 어떤 소스를 켤지, 어떤 언어로 리포트를 만들지, 어떤 외부 시리즈와 RSS 피드를 수집할지 정한다. 잘못된 `sources:` 블록은 조용히 무시하지 않는다. 파서가 실패시키고 CLI가 `invalid sources.yaml` 메시지를 낸다.

```yaml
gray_enabled: true
disabled_ids: []
lang: en
llm_sentiment_enabled: false
llm_sentiment_max_headlines: 50

sources:
  fred:
    series: ["DGS10", "FEDFUNDS", "CPIAUCSL"]
  ecos:
    series:
      - { stat_code: "722Y001", cycle: "M", item_code: "0101000" }
  rss:
    feeds:
      - { url: "https://www.sec.gov/news/pressreleases.rss", publisher: "SEC", market: "US" }
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

`lang`에 허용되지 않은 값이 들어오면 렌더러는 `en`으로 정규화한다. 이는 잘못된 설정이 `<html lang="...">` 속성에 직접 들어가는 일을 막기 위한 방어다.

---

## 3. `sources:` 블록

`sources:` 블록은 FRED, ECOS, RSS의 커버리지를 파이썬 코드 수정 없이 늘리는 설정이다. 블록을 생략하면 코드 기본값을 쓴다.

### 3.1 FRED

```yaml
sources:
  fred:
    series: ["DGS10", "FEDFUNDS", "CPIAUCSL", "T10Y2Y", "UNRATE"]
```

`series`는 FRED series id 목록이다. FRED API key가 없으면 `fred` 소스 자체가 실행되지 않는다. key가 있고 `series`가 없으면 코드 기본값인 `DGS10`, `FEDFUNDS`, `CPIAUCSL`을 수집한다.

### 3.2 ECOS

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

### 3.3 RSS

```yaml
sources:
  rss:
    feeds:
      - url: "https://www.sec.gov/news/pressreleases.rss"
        publisher: "SEC"
        market: "US"
```

RSS는 공식 feed의 제목과 요약 metadata만 저장한다. 기사 본문 전문을 가져오지 않는다. LLM 뉴스 감성 시그널도 저장된 제목과 요약만 사용한다.

---

## 4. 끄는 방법

소스를 끌 때는 빈 `series: []` 대신 `disabled_ids`를 쓴다.

```yaml
disabled_ids: ["rss", "dart"]
```

이 규칙은 설정의 뜻을 하나로 유지하기 위한 것이다. `sources.fred.series`는 "어떤 시리즈를 수집할지"를 말하고, `disabled_ids`는 "소스 자체를 실행하지 말지"를 말한다.

---

## 5. LLM 감성 시그널

LLM 감성 시그널은 세 조건이 모두 맞을 때만 켜진다.

1. `llm_sentiment_enabled: true`
2. `ANTHROPIC_API_KEY` 환경변수 존재
3. `[llm]` extra 설치로 `anthropic` package 사용 가능

기본값은 `false`다. 이 기본값은 프로젝트의 무료 실행 원칙을 지키기 위한 것이다. 설정만 켜고 key나 package가 없으면 경고를 남기고 시그널을 등록하지 않는다.

---

## 6. 잘못된 설정 예시

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

실패를 빠르게 내는 이유는 명확하다. 설정 오타가 조용히 기본값으로 돌아가면 사용자는 새 시리즈가 수집된다고 믿지만 실제 데이터는 늘어나지 않는다.
