# R1b. News Captured Window — 설계

> **스펙 ID**: R1b
> **작성일**: 2026-06-16
> **상태**: ✅ 구현 완료 (`DataReader.read_captured_window` + in-memory captured-date index + 뉴스 시그널 captured window). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **선행**: [S2 Analysis](2026-05-31-analysis-design.md) · [News Mention Alias Matching](2026-06-16-news-mention-alias-design.md) · [확장성 카탈로그](../../architecture/improvement-catalog.md)

---

## 1. 한눈에 보기

뉴스 레코드는 두 개의 시간이 있다. `ts`는 기사가 발행된 시간이고, `captured_at`은 Mimir가 그 기사를 수집한 시간이다.

현재 뉴스 시그널은 `ts` 날짜로 `as_of` 윈도우를 자른다. 그래서 5월 30일에 발행됐지만 5월 31일 실행에서 처음 수집된 뉴스는 5월 31일 분석에서 빠진다. 반대로 5월 31일에 발행됐지만 6월 1일에 처음 수집된 뉴스는 과거 5월 31일 재실행에 끼어들 수 있다.

R1b는 뉴스 시그널의 읽기 기준을 `captured_at` 날짜로 바꾼다. 저장 파티션과 원천 이벤트 시간은 그대로 둔다. 바뀌는 것은 `news_volume`과 off-by-default `llm_sentiment`가 "오늘 수집된 뉴스"를 고르는 기준뿐이다.

---

## 2. 문제

### 2.1 발행일 기준 윈도우는 운영 실행과 어긋난다

`RssSource`는 feed의 publish timestamp를 `RawRecord.ts`로 저장한다. publish timestamp가 없으면 레코드를 건너뛰어 dedup과 뉴스량 부풀림을 피한다.

분석 실행은 보통 하루에 한 번 돈다. 이때 사용자가 기대하는 "오늘 뉴스"는 오늘 실행에서 관측한 뉴스다. 그러나 현재 `NewsVolumeSignal`은 아래처럼 발행일 기준으로 읽는다.

```python
reader.read(Dataset.NEWS, since=as_of, until=as_of)
```

이 호출은 `rec.ts.date()`가 `as_of`인 레코드만 남긴다. 뉴스가 늦게 수집되면 오늘 실행의 입력에서 빠진다.

### 2.2 baseline도 같은 왜곡을 가진다

`news_volume`은 오늘 뉴스 수와 직전 7일 baseline을 비교한다. baseline도 `rec.ts.date()` 기준이므로, 수집 시점이 밀린 뉴스는 실제로 관측된 날의 baseline에 들어가지 않는다.

이 문제는 alias matcher와 별개다. alias matcher는 어떤 headline이 종목을 언급했는지 판단한다. captured window는 어떤 날짜 실행에서 그 headline을 볼 수 있는지 판단한다.

### 2.3 LLM 감성 시그널도 같은 입력 선택을 쓴다

`LlmSentimentSignal`은 LLM 호출 전에 뉴스 mention을 고른다. 이 선택도 `reader.read(Dataset.NEWS, since=as_of, until=as_of)`를 사용한다.

따라서 captured window를 `news_volume`에만 적용하면 무료 시그널은 개선되지만, 사용자가 LLM 감성을 켰을 때는 같은 날짜 왜곡이 남는다.

---

## 3. 목표와 비목표

### 목표

- `DataReader`에 `captured_at.date()` 기준 윈도우 읽기 API를 추가한다.
- `NewsVolumeSignal`의 today와 baseline 읽기를 captured window로 바꾼다.
- `LlmSentimentSignal`의 headline 선택을 captured window로 바꾼다.
- `ts`는 계속 원천 발행일로 유지한다.
- 저장 파티션은 계속 `rec.ts.date()` 기준으로 유지한다.
- 기존 가격, 공시, 거시, 파생 데이터셋의 읽기 의미는 바꾸지 않는다.

### 비목표

- JSONL 파티션 구조를 바꾸지 않는다.
- `captured_at` 인덱스나 별도 파티션을 추가하지 않는다.
- 이미 저장된 뉴스 레코드를 마이그레이션하지 않는다.
- 발행일 없는 RSS 항목을 다시 허용하지 않는다.
- 종목별 feed나 기본 alias 사전을 추가하지 않는다.

---

## 4. 설계

### 4.1 `DataReader.read_captured_window`

`DataReader`에 아래 메서드를 추가한다.

```python
def read_captured_window(
    self,
    dataset: Dataset,
    *,
    symbol: str | None = None,
    since: date | None = None,
    until: date | None = None,
) -> list[Record]:
    ...
```

이 메서드는 `rec.captured_at.date()`로 `since`와 `until`을 비교한다. `symbol` 필터는 기존 `read()`와 같은 의미를 가진다.

### 4.2 현재 구현은 in-memory captured-date index를 쓴다

저장 파티션은 여전히 `rec.ts.date()` 기준이다. `captured_at` 기준으로 날짜를 자르면서 `read_window(since, until)`을 쓰면, 발행일이 윈도우 밖인 레코드를 읽기 전에 놓친다.

현재 구현은 `DataReader.read_captured_window()`가 `_captured_date_index()`를 통해 dataset별 in-memory index를 만든다. 첫 호출은 `JsonlStore.read_all(dataset)`으로 전체 dataset을 읽고 `captured_at.date()`별 bucket을 만든다. 같은 `DataReader`의 다음 captured window 호출은 이 index를 재사용한다.

Cache key는 `JsonlStore.revision`이다. 같은 store 객체에 record가 append되거나 `replace_partition()`이 실행되면 revision이 바뀌고, 다음 `read_captured_window()` 호출이 index를 다시 만든다. Index rebuild 때는 `mimir.storage.reader` DEBUG log에 `captured-date index rebuilt`와 함께 record 수, day 수, elapsed time을 남긴다.

이 index는 on-disk index가 아니다. 저장 구조, JSONL partition, `idempotency_key`, migration 경로는 바꾸지 않는다. 큰 NEWS 데이터에서 scan 비용이 의미 있게 보이면 별도 persistent index 설계로 넘어간다.

### 4.3 뉴스 시그널만 새 API를 사용한다

`NewsVolumeSignal`은 today와 baseline 둘 다 captured window로 읽는다.

```python
reader.read_captured_window(Dataset.NEWS, since=as_of, until=as_of)
reader.read_captured_window(
    Dataset.NEWS,
    since=as_of - timedelta(days=BASELINE_DAYS),
    until=as_of - timedelta(days=1),
)
```

`LlmSentimentSignal`도 같은 API를 사용한다.

```python
reader.read_captured_window(Dataset.NEWS, since=as_of, until=as_of)
```

현재 코드에서 `NewsVolumeSignal`은 today와 baseline 모두 `DataReader.read_captured_window()`를 호출한다. `LlmSentimentSignal`도 classifier 호출 전에 같은 captured window로 mention 후보를 고른다.

다른 시그널은 기존 `read()`를 유지한다. 가격, 공시, 거시 신호는 이벤트 날짜 기준 분석이 자연스럽기 때문이다.

---

## 5. 실패와 예외 처리

| 상황 | 처리 |
|---|---|
| 뉴스가 어제 발행됐고 오늘 수집됨 | 오늘 `as_of` 뉴스 시그널 입력에 포함 |
| 뉴스가 오늘 발행됐고 내일 수집됨 | 오늘 `as_of` 재실행에는 포함하지 않음 |
| baseline 기간에 수집된 뉴스가 더 오래된 발행일을 가짐 | baseline에 포함 |
| `symbol` 필터가 지정됨 | 기존 reader와 같이 `rec.symbol`로 필터 |
| `captured_at` 기준 scan이 느려짐 | 후속으로 인덱스/보조 파티션 설계. 이번 증분에서는 정확성 우선 |

---

## 6. 테스트 전략

### 6.1 Reader 테스트

`tests/analysis/test_reader.py`에 두 reader 테스트를 추가한다.

첫 테스트는 같은 발행일(`ts`)을 가진 뉴스 중 `captured_at` 날짜가 요청 윈도우에 들어오는 레코드만 반환되는지 확인한다. 두 번째 테스트는 `since`/`until` 경계가 inclusive이고 `symbol` 필터가 기존 `read()`와 같은 의미로 적용되는지 확인한다.

### 6.2 News volume 테스트

`tests/analysis/signals/test_signals.py`에 두 회귀 테스트를 추가한다.

- `test_news_volume_counts_news_captured_today_even_when_published_yesterday`
- `test_news_volume_baseline_uses_captured_at_window`

첫 테스트는 어제 발행되고 오늘 수집된 뉴스가 오늘 signal을 만드는지 확인한다. 두 번째 테스트는 baseline도 발행일이 아니라 수집일 기준으로 계산되는지 확인한다.

### 6.3 LLM sentiment 테스트

`tests/analysis/signals/test_llm_sentiment.py`에 `test_llm_sentiment_classifies_news_captured_today_even_when_published_yesterday`를 추가한다.

fake classifier를 사용해 네트워크와 실제 LLM 호출 없이 headline 선택 기준만 검증한다.

---

## 7. 수용 기준

- [x] `DataReader.read_captured_window()`가 `captured_at.date()`로 `since`/`until`을 필터링한다.
- [x] `NewsVolumeSignal`은 today와 baseline 모두 captured window를 사용한다.
- [x] `LlmSentimentSignal`은 captured window로 오늘 수집된 headline을 고른다.
- [x] 기존 `DataReader.read()`의 `ts` 기준 의미는 유지된다.
- [x] captured window는 저장 파티션 구조를 바꾸지 않는다.
- [x] 개선 백로그와 확장성 문서가 R1b 구현과 남은 한계를 설명한다.
- [x] ruff, mypy, pytest, coverage 80% gate를 통과한다.

---

## 8. 남는 한계

`read_captured_window()`는 captured-date on-disk index를 만들지 않는다. 현재는 첫 captured window 호출에서 in-memory index를 만들고 `JsonlStore.revision`이 바뀔 때까지 재사용한다.

그 시점에는 보조 인덱스나 captured-date 파티션을 별도로 설계해야 한다. 이번 증분은 저장 구조를 유지하면서 replay 정확성을 먼저 고정한다.
