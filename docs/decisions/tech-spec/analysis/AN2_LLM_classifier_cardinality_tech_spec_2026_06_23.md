# AN2 LLM Classifier Cardinality Tech Spec

## 한눈에 보기

이번 변경은 opt-in LLM 감성 시그널이 classifier 응답 개수를 검증하게 한다.
LLM이 headline보다 적거나 많은 verdict를 반환하면 해당 symbol의 시그널을 건너뛴다.
잘못된 응답은 warning으로 남기고, 집계·스코어링에는 넣지 않는다.
기본 off-by-default 정책과 유료 호출 gate는 바꾸지 않는다.

## 요약

`LlmSentimentSignal.evaluate()`는 headline 목록을 classifier에 넘긴 뒤, 반환된 `HeadlineVerdict` 목록을 바로 `_aggregate()`에 전달한다. 이 경로는 classifier가 "입력 headline 하나당 verdict 하나"라는 계약을 지키는 것을 전제로 한다.

| 결정 | 이유 | 결과 |
| ---- | ---- | ---- |
| verdict 개수가 headline 개수와 다르면 `None` 반환 | 누락/초과 응답을 조용히 평균내면 다른 headline의 방향성이 섞인다 | 해당 symbol의 LLM 시그널만 skip |
| warning에 expected/actual 개수와 symbol을 남긴다 | 운영자가 LLM 구조화 출력 drift를 볼 수 있어야 한다 | pipeline은 계속 실행, 원인은 로그에 남음 |
| `_aggregate()` 앞에서 검증한다 | 잘못된 verdict batch가 scoring 표면으로 넘어가기 전에 막는다 | 기존 aggregate 수식은 정상 batch에만 적용 |
| classifier exception 정책은 유지한다 | 네트워크/API 실패와 구조화 출력 drift는 같은 격리 원칙을 따른다 | 한 symbol 실패가 전체 분석을 깨지 않음 |
| 저장·cache·schema 변경은 하지 않는다 | 이 slice는 runtime guard다 | 새 데이터셋, 새 네트워크 호출 없음 |

## 현재 상태 분석

### Classifier 계약

`mimir/analysis/signals/llm_sentiment.py`의 `HeadlineClassifier` protocol은 아래 계약을 갖는다.

```python
class HeadlineClassifier(Protocol):
    def classify(self, headlines: list[str]) -> list[HeadlineVerdict]: ...
```

`AnthropicHeadlineClassifier.classify()`는 prompt에서 "Return one verdict per headline, in the same order"라고 요구한다. `_VerdictBatch`도 `verdicts: list[HeadlineVerdict]`만 검증하므로 pydantic은 "list인지"까지만 확인한다. list 길이가 입력 길이와 같은지는 현재 코드가 따로 확인해야 한다.

### 현재 실패 모드

`evaluate()`는 아래 순서로 동작한다.

1. 오늘 수집된 NEWS 중 symbol mention을 찾는다.
2. `max_headlines` 상한만큼 자른다.
3. headline text를 classifier에 보낸다.
4. classifier가 반환한 verdict 목록을 `_aggregate()`에 넘긴다.

4번 앞에 개수 검증이 없다. 그래서 3개 headline에 2개 verdict가 오면 두 verdict만 평균낸다. 반대로 3개 headline에 4개 verdict가 오면 존재하지 않는 headline까지 점수에 들어간다.

### 기존 보호 장치

`test_runtime_classifier_error_returns_none`은 classifier가 예외를 던질 때 `None`을 반환한다고 고정한다. 하지만 "예외는 없고 길이만 틀린 구조화 출력"은 테스트가 없다. 이 경우는 API 장애가 아니라 모델 출력 drift에 가깝고, 같은 source-isolation 원칙으로 처리해야 한다.

## 목표

- classifier 반환 verdict 수가 입력 headline 수와 정확히 같을 때만 `_aggregate()`를 호출한다.
- verdict 수가 부족하면 warning 후 `None`을 반환한다.
- verdict 수가 초과하면 warning 후 `None`을 반환한다.
- warning에는 signal id, symbol, expected count, actual count가 포함된다.
- 기존 cap warning, classifier exception handling, 정상 aggregate 결과는 유지한다.
- 기본 pipeline의 LLM off-by-default invariant를 유지한다.

## 목표가 아닌 것

| 항목 | 제외 이유 |
| ---- | --------- |
| LLM retry 또는 re-prompt | 비용과 latency가 늘고, 실패 정책이 복잡해진다. |
| partial aggregate | 누락된 headline의 방향성을 알 수 없어서 조용한 편향을 만든다. |
| verdict-headline pair 저장 | 현재 LLM sentiment는 저장 데이터셋을 만들지 않는다. |
| cache 구현 | 기존 LLM seam 문서의 cache 아이디어는 별도 설계가 필요하다. |
| Anthropic SDK 호출 변경 | prompt와 parse 경로는 그대로 두고 runtime guard만 추가한다. |

## 설계

`LlmSentimentSignal.evaluate()`에서 classifier 호출 직후 길이를 검증한다.

```python
verdicts = self._classifier.classify(texts)
if len(verdicts) != len(texts):
    logger.warning(
        "signal 'llm_sentiment' classifier returned %d verdicts for %d headlines for %s; skipping",
        len(verdicts),
        len(texts),
        symbol,
    )
    return None
```

검증 위치는 `_aggregate()`보다 앞이다. `_aggregate()`는 정상 batch의 수식만 유지한다. `texts`는 이미 `capped`에서 만든 실제 classifier 입력이므로 expected count는 `len(texts)`가 맞다. `unclassified`는 cap 때문에 의도적으로 분류하지 않은 개수이고, classifier cardinality mismatch와는 별도 개념이다.

## 테스트

| 테스트 | 고정하는 계약 |
| ---- | ---- |
| `test_classifier_too_few_verdicts_returns_none` | verdict 부족 batch는 aggregate하지 않고 `None` |
| `test_classifier_too_many_verdicts_returns_none` | verdict 초과 batch도 aggregate하지 않고 `None` |
| 기존 aggregate tests | 정상 cardinality는 기존 방향·strength·confidence 계산 유지 |
| 기존 runtime error test | classifier exception 격리 정책 유지 |

## 롤아웃

마이그레이션은 없다. 유효한 classifier 구현은 기존과 동일하게 동작한다. 잘못된 구조화 출력만 해당 symbol의 `llm_sentiment`를 생략한다. 다른 signal과 다른 symbol 분석은 계속 실행된다.

## 보안·비용 영향

- 새 네트워크 호출이 없다.
- secret 처리 경로가 바뀌지 않는다.
- 잘못된 LLM batch가 score에 섞이는 silent corruption 위험을 줄인다.
- retry를 하지 않으므로 비용 상한과 `llm_sentiment_max_headlines` 정책을 유지한다.

---

**버전**: v1.0
**작성일**: 2026-06-23
**상태**: Implemented
**관련 문서**: [LLM seam 설계](../../../superpowers/specs/2026-06-13-llm-sentiment-seam-design.md), [analysis scoring](../../../reference/analysis/scoring.md)
