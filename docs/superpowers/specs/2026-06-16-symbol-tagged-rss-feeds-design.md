# Symbol-Tagged RSS Feeds — 설계

> **스펙 ID**: R1d
> **작성일**: 2026-06-16
> **상태**: ✅ 구현 완료 (`RssFeed.symbol` + record-symbol 뉴스 매칭). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **선행**: [R1a News Mention Alias](2026-06-16-news-mention-alias-design.md) · [R1b News Captured Window](2026-06-16-news-captured-window-design.md) · [R1c Default News Aliases](2026-06-16-default-news-aliases-design.md) · [개선 백로그](../../IMPROVEMENTS.md)

---

## 1. 한눈에 보기

공식 RSS feed는 제목에 티커를 자주 넣지 않는다. Alias matcher는 `Apple` 같은 회사명을 `AAPL`로 해석해 이 문제를 줄였지만, 사용자가 이미 종목별 feed URL을 알고 있어도 그 feed가 어느 symbol을 위한 것인지 저장할 방법이 없다.

이 변경은 RSS feed 설정에 선택 필드 `symbol`을 추가한다. `symbol`이 있는 feed에서 온 뉴스는 top-level record symbol에 그 값을 저장한다.

분석 단계에서는 record symbol이 평가 중인 symbol과 같으면 뉴스 mention으로 인정한다. 제목과 요약에 티커나 회사명이 없어도, 사용자가 종목별 feed로 명시한 뉴스는 해당 symbol의 뉴스로 계산된다.

---

## 2. 문제

### 2.1 Alias만으로는 모든 종목별 feed를 살릴 수 없다

R1a와 R1c는 제목·요약 텍스트를 보고 symbol mention을 찾는다. 이 방식은 무료이고 보수적이다.

하지만 feed 자체가 이미 종목별로 분리되어 있으면 텍스트 매칭은 불필요한 제약이 된다. 예를 들어 사용자가 `AAPL` 전용 feed를 설정했는데 제목이 `Supplier update`라면, 현재 `news_volume`은 이 뉴스를 놓친다.

### 2.2 지금 RSS 설정은 feed와 symbol의 관계를 표현하지 못한다

현재 `sources.rss.feeds` 항목은 `url`, `publisher`, `market`만 받는다. 이 정보는 출처와 feed market을 설명하지만, watchlist symbol과의 연결을 설명하지 않는다.

### 2.3 같은 URL이 여러 종목 feed에 나타날 수 있다

한 기사가 여러 종목 feed에 동시에 들어갈 수 있다. 이때 idempotency key가 URL만 사용하면 먼저 저장된 symbol만 남고 나머지 symbol은 dedup으로 사라진다.

---

## 3. 목표와 비목표

### 목표

- `sources.rss.feeds[].symbol`을 선택 필드로 받는다.
- `symbol`은 공백 제거 후 저장한다. 빈 문자열은 설정 오류로 실패한다.
- RSS feed 항목에 알 수 없는 필드가 있으면 `ValidationError`로 실패한다.
- `RssSource`는 symbol-tagged feed에서 `RawRecord.symbol`을 채운다.
- symbol-tagged feed는 `rss:{symbol}:{link}` idempotency key를 사용한다.
- 기존 symbol 없는 RSS feed는 `rss:{link}` key와 `symbol=None`을 유지한다.
- `NewsMentionMatcher`는 record symbol exact match를 텍스트 match보다 먼저 인정한다.
- `NewsVolumeSignal`과 opt-in `LlmSentimentSignal`은 같은 matcher를 쓰므로 둘 다 symbol-tagged news를 활용한다.

### 비목표

- 종목별 feed URL을 자동으로 발견하지 않는다.
- news payload schema에 `symbol` 필드를 추가하지 않는다. Symbol은 record envelope에 이미 있다.
- RSS 기사 본문 전문을 가져오지 않는다.
- 기존 alias matcher를 제거하거나 LLM sentiment를 기본 활성화하지 않는다.
- 여러 symbol이 같은 기사 URL을 공유할 때 중복 기사 수를 자동으로 합치지 않는다.

---

## 4. 설계

### 4.1 RSS feed 모델

`RssFeed`는 선택 필드 `symbol`을 가진다.

```python
class RssFeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    publisher: str
    market: str
    symbol: str | None = None
```

`symbol`은 validator에서 `strip()`한다. 값이 빈 문자열이면 실패한다.

이 변경은 기존 설정과 호환된다. 기존 feed 항목은 `symbol`을 생략하므로 지금처럼 일반 뉴스 feed로 동작한다.

현재 구현에서 `RssFeed.symbol`은 `mimir/sources/rss.py`의 pydantic model 필드다. Validator는 공백을 제거하고 빈 문자열이면 `ValueError("RSS feed symbol must not be blank")`로 실패한다. `extra="forbid"` 때문에 `symbl` 같은 오타 field도 조용히 무시되지 않는다.

### 4.2 RawRecord symbol과 idempotency key

`RssSource.fetch()`는 feed symbol을 `RawRecord.symbol`에 넣는다.

```python
symbol = feed.symbol
key = f"rss:{symbol}:{link}" if symbol else f"rss:{link}"
```

symbol 없는 feed는 기존 key를 유지한다. symbol 있는 feed만 symbol을 key에 포함한다.

이 정책은 같은 URL이 `AAPL` feed와 `MSFT` feed에 동시에 나타나는 상황을 보존한다. 두 record는 다른 symbol을 가진 별도 mention이다.

현재 `RssSource.fetch()`는 symbol-tagged feed에서 `RawRecord.symbol`을 feed symbol로 채운다. Symbol 없는 feed는 기존 `rss:{link}` key를 유지하고, symbol 있는 feed는 `rss:{symbol}:{link}` key를 쓴다. Payload schema에는 symbol을 추가하지 않고 record envelope symbol만 사용한다.

### 4.3 NewsMentionMatcher 우선순위

`NewsMentionMatcher.mentions(record, symbol)`는 먼저 envelope symbol을 본다.

```python
if record.symbol == symbol:
    return True
```

그 다음 기존처럼 제목과 요약에서 symbol·alias를 찾는다.

이 순서는 symbol-tagged feed를 명시적인 사용자 의도로 취급한다. 텍스트 matcher는 일반 RSS feed와 alias 기반 보완을 계속 담당한다.

현재 `NewsMentionMatcher`는 코드상 `record.symbol == symbol`을 먼저 확인한 뒤 제목·요약의 symbol/alias term을 검사한다. `NewsVolumeSignal`과 `LlmSentimentSignal`은 같은 matcher를 사용하므로 symbol-tagged RSS feed는 무료 뉴스량 시그널과 opt-in LLM 감성 시그널 모두에 적용된다.

---

## 5. 실패와 예외 처리

| 상황 | 처리 |
|---|---|
| `sources.rss.feeds[].symbol`이 생략됨 | 기존 일반 RSS feed로 처리 |
| `symbol: " AAPL "` | `"AAPL"`로 정규화 |
| `symbol: ""` 또는 공백 문자열 | `ValidationError` |
| feed 항목에 `symbl` 같은 오타가 있음 | `ValidationError` |
| symbol-tagged feed의 제목에 symbol/alias가 없음 | record symbol match로 mention 인정 |
| 같은 URL이 두 symbol-tagged feed에 있음 | symbol별 idempotency key로 둘 다 저장 |
| 같은 URL이 일반 feed와 symbol-tagged feed에 있음 | 일반 record와 symbol-tagged record가 별도로 저장될 수 있음 |

---

## 6. 테스트 전략

| 테스트 | 고정하는 계약 |
|---|---|
| `test_rss_feed_symbol_parses_from_config` | config parser가 `sources.rss.feeds[].symbol`을 typed 모델로 읽는다. |
| `test_rss_feed_blank_symbol_raises_validation_error` | 공백 symbol은 설정 오류다. |
| `test_rss_feed_typo_field_raises_validation_error` | feed 항목의 오타 필드는 조용히 무시되지 않는다. |
| `test_rss_parses_entries_with_feed_symbol` | RSS source가 `RawRecord.symbol`과 symbol 포함 key를 만든다. |
| `test_rss_symbol_feed_key_keeps_same_url_for_multiple_symbols` | 같은 기사 URL이 여러 symbol feed에 있어도 symbol별 key로 둘 다 보존된다. |
| `test_news_mention_matcher_matches_record_symbol_before_text` | 제목·요약에 mention이 없어도 record symbol exact match가 true다. |
| `test_news_volume_counts_symbol_tagged_feed_without_text_mention` | `news_volume`이 symbol-tagged news를 오늘 뉴스로 계산한다. |
| `test_llm_sentiment_matches_symbol_tagged_feed_without_text_mention` | opt-in LLM sentiment도 같은 matcher 계약을 따른다. |

---

## 7. 수용 기준

- [x] `sources.rss.feeds[].symbol`이 문서화되고 검증된다.
- [x] 기존 symbol 없는 RSS feed의 key와 payload는 바뀌지 않는다.
- [x] symbol-tagged RSS feed는 top-level record symbol을 남긴다.
- [x] symbol-tagged RSS feed는 symbol별 idempotency key를 사용한다.
- [x] `news_volume`과 opt-in `llm_sentiment`가 symbol-tagged news를 활용한다.
- [x] 개선 백로그와 확장성 문서에서 "종목별 feed" 한계를 업데이트한다.
- [x] ruff, mypy, pytest, coverage 80% gate를 통과한다.

---

## 8. 남는 한계

이번 변경은 사용자가 종목별 feed URL을 알고 있다는 전제에서 동작한다. Mimir가 외부 vendor의 symbol별 RSS endpoint를 자동으로 찾거나 추천하지는 않는다.

또한 같은 URL이 일반 feed와 symbol-tagged feed에 동시에 들어오면 두 record가 생길 수 있다. 이 동작은 symbol 관계 보존을 우선한 결과다. 중복 기사 수를 전역에서 합치려면 URL canonicalization과 multi-symbol relation 모델이 필요하다.
