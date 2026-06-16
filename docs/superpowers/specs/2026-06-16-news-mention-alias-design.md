# R1. News Mention Alias Matching — 설계

> **스펙 ID**: R1
> **작성일**: 2026-06-16
> **상태**: ✅ 구현 완료 (`analysis.news.aliases` + shared `NewsMentionMatcher`). 364 테스트 · ruff · mypy · coverage gate 클린.
> **선행**: [S2 Analysis](2026-05-31-analysis-design.md) · [LLM 뉴스 감성 seam](2026-06-13-llm-sentiment-seam-design.md) · [확장성 카탈로그](../../architecture/improvement-catalog.md)

---

## 1. 한눈에 보기

`news_volume`은 저장된 뉴스 제목과 요약에서 종목 심볼을 찾는다. 하지만 SEC 보도자료 같은 공식 RSS feed는 제목에 `AAPL` 같은 티커를 거의 쓰지 않는다. 그래서 실제 데이터에서는 뉴스가 있어도 시그널이 `None`으로 끝나는 경우가 많다.

R1은 무료 경로를 유지하면서 이 한계를 줄인다. `config/sources.yaml`의 `analysis.news.aliases`에 회사명 alias를 선언하고, `NewsVolumeSignal`과 off-by-default `LlmSentimentSignal`이 같은 alias matcher를 사용한다.

이 변경은 새 뉴스 본문을 크롤링하지 않는다. 저장된 제목과 요약만 읽는다. LLM 호출도 기본값에서는 계속 0건이다.

---

## 2. 문제

### 2.1 공식 feed는 티커를 잘 싣지 않는다

`NewsVolumeSignal`은 오늘 뉴스와 7일 기준선을 비교한다. 매칭 대상은 `news` 데이터셋의 `title`과 `summary`다.

현재 매칭어는 watchlist symbol 하나뿐이다.

```python
_mentions(record, "AAPL")
```

이 방식은 제목에 `AAPL`이 들어간 뉴스에는 동작한다. 그러나 공식 보도자료는 보통 `Apple`, `Apple Inc.`, `Samsung Electronics`처럼 회사명을 쓴다. 이 경우 사용자가 RSS feed를 추가해도 `news_volume`은 해당 종목과 연결하지 못한다.

### 2.2 짧은 티커 오매칭은 이미 줄였지만, 실데이터 recall은 아직 낮다

기존 hardening은 단어 경계 매칭을 추가했다. 그래서 `A`가 `Apple` 안에서 매칭되는 문제는 줄었다.

남은 문제는 반대 방향이다. `AAPL`이 없고 `Apple`만 있으면 매칭하지 못한다. 이 문제는 단어 경계로 해결되지 않는다.

### 2.3 LLM seam도 같은 매칭 병목을 가진다

`LlmSentimentSignal`은 유료 시그널이라 기본으로 꺼져 있다. 이 시그널도 LLM에 보낼 headline을 고르기 전에 `_mentions(record, symbol)`을 사용한다.

따라서 alias가 `news_volume`에만 들어가면 무료 시그널은 개선되지만, 사용자가 LLM을 켰을 때는 같은 recall 문제가 남는다. alias matcher는 두 뉴스 시그널이 같이 써야 한다.

---

## 3. 목표와 비목표

### 목표

- `analysis.news.aliases` 설정을 검증한다.
- `NewsVolumeSignal`은 symbol과 alias를 모두 매칭어로 사용한다.
- `LlmSentimentSignal`도 같은 alias matcher를 사용한다.
- 설정이 없으면 기존 동작과 시그널 수를 유지한다.
- 매칭은 저장된 `title`과 `summary`만 사용한다.
- 잘못된 `analysis.news` 키는 조용히 무시하지 않고 실패한다.

### 비목표

- 기사 본문 크롤링을 추가하지 않는다.
- 기본 alias 사전을 코드에 넣지 않는다. v1은 사용자 설정만 지원한다.
- alias를 watchlist 파일로 옮기지 않는다. 이 증분은 분석 해석 설정이므로 `sources.yaml`의 `analysis:` 블록에 둔다.
- LLM 시그널을 기본으로 켜지 않는다.
- 이미 저장된 뉴스 레코드를 마이그레이션하지 않는다.

---

## 4. 설정 설계

Alias는 수집 대상이 아니라 분석 해석 규칙이다. 그래서 `sources:`가 아니라 `analysis:` 아래에 둔다.

```yaml
analysis:
  news:
    aliases:
      AAPL: ["Apple", "Apple Inc."]
      MSFT: ["Microsoft", "Microsoft Corp."]
      NVDA: ["NVIDIA", "Nvidia Corporation"]
      "005930": ["Samsung Electronics", "삼성전자"]
```

`aliases`는 `dict[str, list[str]]`이다.

| 필드 | 의미 |
|---|---|
| key | watchlist symbol. 예: `AAPL`, `"005930"` |
| value | 제목과 요약에서 추가로 찾을 회사명 또는 표기 |

설정을 생략하면 빈 alias map을 쓴다. 빈 alias map은 오늘의 symbol-only 동작과 같다.

---

## 5. 매칭 설계

### 5.1 공통 matcher

새 모듈 `mimir/analysis/signals/news_matching.py`가 뉴스 mention 판정을 담당한다.

```python
class NewsMentionMatcher:
    def __init__(self, aliases: Mapping[str, Sequence[str]] | None = None) -> None: ...

    def mentions(self, record: Record, symbol: str) -> bool: ...

    def terms_for(self, symbol: str) -> tuple[str, ...]: ...
```

`terms_for("AAPL")`은 항상 symbol 자체를 포함한다. 설정 alias가 있으면 symbol 뒤에 alias를 붙인다. alias 중복은 제거하되 순서는 보존한다.

### 5.2 경계 규칙

모든 term은 대소문자를 무시하고 매칭한다.

경계는 Python 정규식의 Unicode word 문자(`\w`) 기준으로 처리한다.

```text
(?<![\w])<term>(?![\w])
```

이 규칙은 `A`가 `Apple` 안에서 매칭되는 일을 막는다. `Apple Inc.`처럼 공백과 마침표가 있는 alias도 전체 phrase 기준으로 매칭한다.

한국어 alias도 같은 정규식으로 처리한다. `삼성전자`는 단독 표기일 때 매칭되지만, `삼성전자우`처럼 다른 종목명이나 긴 단어 안에 붙어 있으면 매칭하지 않는다.

### 5.3 빈 문자열 alias

빈 문자열이나 공백뿐인 alias는 무시한다. 설정 파일에 우연히 `""`가 있어도 모든 뉴스가 매칭되는 위험을 만들면 안 된다.

---

## 6. 빌더 배선

`SourcesConfig`에 `news_aliases` 필드를 추가한다.

```python
class SourcesConfig(BaseModel):
    news_aliases: dict[str, list[str]] | None = None
```

`parse_sources_config()`는 아래 설정을 읽는다.

```yaml
analysis:
  news:
    aliases:
      AAPL: ["Apple", "Apple Inc."]
```

`build_signals()`는 같은 alias map을 두 뉴스 시그널에 전달한다.

```python
signals: list[Signal] = [
    FilingEventSignal(),
    NewsVolumeSignal(aliases=cfg.news_aliases),
    PriceMomentumSignal(),
    MacroRegimeSignal(rate_series=cfg.macro_regime_rate_series),
]

if _llm_sentiment_enabled(...):
    signals.append(
        LlmSentimentSignal(
            classifier=...,
            max_headlines=cfg.llm_sentiment_max_headlines,
            aliases=cfg.news_aliases,
        )
    )
```

LLM 시그널은 기존처럼 세 조건이 모두 맞을 때만 생성된다. alias 설정만으로는 LLM 호출이 생기지 않는다.

---

## 7. 실패와 예외 처리

| 상황 | 처리 |
|---|---|
| `analysis.news.aliases`가 list나 string임 | pydantic `ValidationError` |
| alias 값이 string 하나임 | pydantic `ValidationError` |
| `analysis.news.aliasez` 같은 오타 | pydantic `ValidationError` |
| alias list에 빈 문자열이 있음 | matcher가 무시 |
| 설정이 없음 | 기존 symbol-only 매칭 유지 |
| `삼성전자` alias가 `삼성전자우` 안에 들어 있음 | 매칭하지 않음 |
| alias가 너무 넓어서 false positive가 생김 | 사용자 설정 문제로 문서화. R1c의 기본 alias는 `use_default_aliases: false`로 끌 수 있음 |

---

## 8. 테스트 전략

### 8.1 Signal matcher 테스트

`tests/analysis/signals/test_signals.py`는 alias가 제목과 요약 양쪽에서 동작하는지 확인한다.

- `AAPL` 뉴스에 `Apple announced earnings`만 있어도 `news_volume`이 결과를 낸다.
- `A`는 `Apple` 안에서 매칭되지 않는다.
- 빈 alias는 매칭어로 쓰이지 않는다.
- baseline window도 같은 alias matcher를 사용한다.

### 8.2 Builder 테스트

`tests/analysis/test_builder.py`는 `build_signals(SourcesConfig(news_aliases=...))`가 `NewsVolumeSignal`에 alias를 전달하는지 확인한다.

LLM 쪽은 fake classifier를 주입해 `LlmSentimentSignal`이 alias로 headline을 찾는지 확인한다. 이 테스트는 네트워크와 실제 `anthropic` package를 요구하지 않는다.

### 8.3 Config 테스트

`tests/sources/test_config.py`는 `analysis.news.aliases` 파싱과 오타 실패를 고정한다.

### 8.4 회귀 테스트

`build_signals()` 기본 호출은 계속 네 개 시그널만 반환해야 한다. 기본 경로는 `anthropic`을 import하지 않는다.

---

## 9. 수용 기준

- [ ] `analysis.news.aliases`가 검증되고 `SourcesConfig.news_aliases`로 전달된다.
- [ ] `NewsVolumeSignal`이 symbol과 alias를 모두 사용한다.
- [ ] `LlmSentimentSignal`이 같은 alias matcher를 사용한다.
- [ ] 설정이 없으면 기존 symbol-only 동작과 시그널 수가 유지된다.
- [ ] 잘못된 alias 설정은 `ValidationError`로 실패한다.
- [ ] `config/sources.yaml`, `docs/reference/config/sources.md`, 개선 백로그, 확장성 문서가 새 설정을 설명한다.
- [ ] ruff, mypy, pytest, coverage 80% gate를 통과한다.

---

## 10. 남는 한계

Alias는 recall을 높이지만, 뉴스 방향성은 만들지 않는다. `news_volume`은 계속 NEUTRAL 시그널이다. 방향성은 off-by-default `llm_sentiment`가 맡는다.

또한 R1 v1의 alias는 사용자가 관리한다. 기본 alias 사전을 넣으면 유지보수와 오매칭 책임이 프로젝트 코드로 들어오기 때문에 이 증분에서는 제외했다. 이후 R1c에서 기본 watchlist용 보수적 alias 데이터셋과 `analysis.news.use_default_aliases` opt-out을 별도 설계로 추가했다.
