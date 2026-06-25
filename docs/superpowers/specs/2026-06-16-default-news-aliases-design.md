# R1c. Default News Aliases — 설계

> **스펙 ID**: R1c
> **작성일**: 2026-06-16
> **상태**: ✅ 구현 완료 (`DEFAULT_NEWS_ALIASES` + `analysis.news.use_default_aliases`). 최신 검증은 README 테스트 배지와 docs health guard가 추적하며, ruff · mypy · coverage gate 클린 상태를 유지한다.
> **선행**: [R1 News Mention Alias Matching](2026-06-16-news-mention-alias-design.md) · [R1b News Captured Window](2026-06-16-news-captured-window-design.md) · [확장성 카탈로그](../../architecture/improvement-catalog.md)

---

## 1. 한눈에 보기

R1a는 사용자가 `analysis.news.aliases`에 회사명 alias를 직접 적으면 `news_volume`과 opt-in `llm_sentiment`가 그 alias를 사용하게 했다.

하지만 기본 watchlist에는 이미 `AAPL`, `MSFT`, `NVDA`, `"005930"`이 들어 있고, 각 symbol의 대표 회사명도 뚜렷하다. 사용자가 alias 설정을 따로 쓰지 않으면 공식 RSS 제목의 `Apple`, `Microsoft`, `NVIDIA`, `삼성전자`는 여전히 watchlist symbol과 연결되지 않는다.

R1c는 작은 기본 alias 데이터셋을 코드에 둔다. 실제 파이프라인을 만드는 `build_signals()`는 기본 alias와 사용자 alias를 병합한다. 직접 `NewsVolumeSignal()`을 만드는 단위 테스트나 실험 코드는 기존처럼 symbol-only 기본값을 유지한다.

---

## 2. 문제

### 2.1 사용자가 설정을 알아야만 recall이 좋아진다

`analysis.news.aliases`는 강력하지만 opt-in 설정이다. 새 사용자는 README와 config reference를 읽기 전까지 alias가 필요한지 알기 어렵다.

이 때문에 기본 watchlist로 실행해도 `Apple announces...` 같은 뉴스가 `AAPL` 분석에 연결되지 않는다. 프로젝트가 이미 기본 watchlist와 기본 RSS feed를 제공하는 만큼, 가장 흔한 symbol 몇 개의 대표 회사명은 기본으로 해석하는 편이 더 실용적이다.

### 2.2 너무 큰 기본 사전은 오탐을 만든다

Alias는 분석 해석 규칙이다. `Apple`, `Meta`, `ON` 같은 단어는 일반 명사나 짧은 단어와 겹칠 수 있다.

따라서 R1c는 작은 기본값만 제공한다. 기본 watchlist에 들어 있는 핵심 종목과 명확한 회사명만 포함한다. 사용자가 더 넓은 alias를 원하면 `analysis.news.aliases`로 직접 추가한다.

---

## 3. 목표와 비목표

### 목표

- 기본 watchlist 핵심 symbol에 대한 보수적 alias 데이터셋을 제공한다.
- `build_signals()`가 기본 alias와 사용자 alias를 병합해 두 뉴스 시그널에 전달한다.
- 사용자가 `analysis.news.use_default_aliases: false`로 기본 alias를 끌 수 있다.
- 사용자 alias는 기본 alias 뒤에 추가되고, 중복은 제거된다.
- alias 설정만으로 LLM 호출이 켜지지 않는 기존 게이트를 유지한다.
- 직접 생성한 `NewsVolumeSignal()`과 `LlmSentimentSignal()`은 기존처럼 전달받은 alias만 쓴다.

### 비목표

- 대규모 상장사 alias 데이터베이스를 만들지 않는다.
- fuzzy matching, ticker metadata API, 회사명 자동 수집을 추가하지 않는다.
- 종목별 RSS feed를 추가하지 않는다.
- 기본 alias를 저장 데이터에 쓰거나 뉴스 레코드를 마이그레이션하지 않는다.
- LLM 시그널을 기본으로 켜지 않는다.

---

## 4. 설계

### 4.1 기본 alias registry

새 모듈 `mimir/analysis/news_aliases.py`가 기본 alias와 병합 함수를 제공한다.

```python
DEFAULT_NEWS_ALIASES = {
    "AAPL": ("Apple", "Apple Inc."),
    "MSFT": ("Microsoft", "Microsoft Corp."),
    "NVDA": ("NVIDIA", "Nvidia Corporation"),
    "005930": ("Samsung Electronics", "삼성전자"),
}
```

이 사전은 기본 watchlist와 맞춘다. `Meta`처럼 일반 단어와 충돌 가능성이 높은 alias는 넣지 않는다.

### 4.2 병합 규칙

`merge_news_aliases(configured, include_defaults=True)`는 기본 alias와 사용자 alias를 합친다.

1. `include_defaults=True`이면 기본 alias를 먼저 넣는다.
2. 사용자 alias가 있으면 뒤에 추가한다.
3. 같은 symbol 안에서는 대소문자 무시 기준으로 중복을 제거한다.
4. 빈 문자열과 공백 alias는 제거한다.
5. 결과는 signal matcher가 받을 수 있는 `dict[str, tuple[str, ...]]`이다.

기본 alias가 먼저 오기 때문에 `terms_for("AAPL")`은 `("AAPL", "Apple", "Apple Inc.", 사용자 alias...)`처럼 안정적이다.

### 4.3 설정 opt-out

`analysis.news.use_default_aliases`를 추가한다.

```yaml
analysis:
  news:
    use_default_aliases: false
    aliases:
      AAPL: ["Cupertino company"]
```

기본값은 `true`다. 설정을 생략하면 오늘의 기본 watchlist에 맞춘 alias를 쓴다. false로 두면 사용자 alias만 쓴다.

### 4.4 빌더 배선

`build_signals()`는 아래처럼 한 번만 alias map을 만든다.

```python
aliases = merge_news_aliases(
    cfg.news_aliases,
    include_defaults=cfg.use_default_news_aliases,
)
```

그리고 `NewsVolumeSignal`과 `LlmSentimentSignal`에 같은 alias map을 전달한다.

Signal 클래스 자체는 기본 alias를 모른다. 그래서 기존 unit test와 직접 생성 코드는 계속 명시적으로 받은 alias만 사용한다.

---

## 5. 실패와 예외 처리

| 상황 | 처리 |
|---|---|
| 설정이 없음 | 기본 alias를 사용한다 |
| `use_default_aliases: false` | 기본 alias를 쓰지 않는다 |
| 사용자 alias와 기본 alias가 중복됨 | 한 번만 남긴다 |
| 사용자 alias가 빈 문자열임 | 병합 함수와 matcher가 무시한다 |
| `use_default_aliases` 오타 | pydantic `ValidationError` |
| `use_default_aliases`가 문자열 `"false"` | pydantic boolean 파싱으로 `False` |
| LLM 설정이 꺼져 있음 | 기본 alias가 있어도 LLM 시그널은 등록되지 않는다 |

---

## 6. 테스트 전략

| 테스트 | 고정하는 계약 |
|---|---|
| `test_merge_news_aliases_includes_defaults` | 기본 alias가 제공되고 사용자 alias와 병합된다 |
| `test_merge_news_aliases_can_disable_defaults` | opt-out이면 사용자 alias만 남는다 |
| `test_merge_news_aliases_rejects_scalar_string_alias_values` | 직접 helper 호출에서도 scalar string alias가 글자 단위로 펼쳐지지 않는다 |
| `test_build_signals_uses_default_news_aliases_for_news_volume` | 설정 없이도 `Apple` 제목이 `AAPL` 뉴스로 잡힌다 |
| `test_build_signals_can_disable_default_news_aliases` | opt-out이면 `Apple` 제목이 `AAPL`로 잡히지 않는다 |
| `test_build_signals_uses_default_news_aliases_for_llm_sentiment` | LLM을 명시적으로 켰을 때도 같은 기본 alias matcher를 쓴다 |
| `test_analysis_news_use_default_aliases_parse_from_config` | YAML parse layer가 opt-out 값을 읽는다 |
| `test_analysis_news_use_default_aliases_typo_raises` | 오타는 조용히 무시하지 않는다 |

---

## 7. 수용 기준

- [x] 기본 alias 데이터셋이 코드에 있고 테스트로 고정된다.
- [x] `build_signals()` 기본 경로가 `NewsVolumeSignal`에 기본 alias를 전달한다.
- [x] opt-in LLM 시그널도 같은 기본 alias를 사용한다.
- [x] `analysis.news.use_default_aliases: false`가 기본 alias를 끈다.
- [x] 사용자 alias는 기본 alias와 병합되고 중복은 제거된다.
- [x] 직접 생성한 signal의 symbol-only 기본 의미는 유지된다.
- [x] config/reference/README/개선 문서가 기본 alias와 opt-out을 설명한다.
- [x] ruff, mypy, pytest, coverage 80% gate가 통과한다.

---

## 8. 남는 한계

기본 alias는 작고 보수적이다. watchlist가 커지면 symbol metadata를 기반으로 alias 후보를 생성하는 별도 데이터셋이나, 종목별 공식 feed가 필요하다.

또한 `Apple` 같은 일반 단어는 feed 맥락에 따라 오탐 가능성이 있다. 그래서 opt-out을 제공한다. 사용자가 false positive를 확인하면 `use_default_aliases: false`로 끄고 필요한 alias만 직접 지정할 수 있다.
