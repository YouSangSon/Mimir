# AN6 Analysis Signal Result Boundary Tech Spec

## 한눈에 보기

이번 변경은 `Signal.evaluate()`가 `None`도 `SignalResult`도 아닌 값을 돌려줄 때 scoring 단계로 넘기지 않게 한다.
잘못된 반환값은 해당 signal/symbol에서 error log 후 skip하고, 같은 symbol의 다른 signal과 다음 symbol 평가는 계속한다.
`SignalResult` schema, scorer formula, plugin discovery, 저장 schema, retry, network, LLM 비용 gate는 바꾸지 않는다.

## 요약

AN4는 signal 평가 중 발생한 `Exception`을 signal/symbol 단위로 격리했다. 하지만 Python의 `Protocol`은 런타임 반환 타입을 강제하지 않는다. 외부 plugin이나 잘못 작성된 built-in 후보가 `dict`, `str`, 임의 객체처럼 non-`None`이지만 `SignalResult`가 아닌 값을 반환하면 engine은 현재 그 값을 `results`에 append하고, 이후 `score()`가 `.weight`, `.direction`, `.strength`, `.confidence` 접근에서 실패한다.

이 실패는 `Signal.evaluate()` 호출 밖에서 발생하므로 AN4의 isolation boundary를 빠져나간다. AN6는 engine과 scorer 사이에 명시적인 result boundary를 추가해 malformed result를 signal failure처럼 취급한다.

| 결정 | 이유 | 결과 |
| ---- | ---- | ---- |
| `AnalysisEngine`가 `SignalResult` instance인지 확인한다 | `Signal` protocol annotation은 runtime plugin 반환값을 강제하지 않는다 | malformed return이 scorer를 crash시키지 않는다 |
| non-`None`/non-`SignalResult` 값은 skip한다 | coercion은 plugin 버그를 숨기고 분석 오염을 만들 수 있다 | 해당 signal/symbol 결과만 빠지고 run은 계속된다 |
| error log에 signal id, market/symbol, 반환 타입을 남긴다 | 운영자가 어떤 plugin이 잘못된 계약을 깼는지 알아야 한다 | traceback 없는 contract error로 진단 가능하다 |
| `SignalResult` validation은 기존 pydantic boundary에 맡긴다 | schema 위반은 signal 생성 시점에 이미 loud failure다 | engine은 type boundary만 담당한다 |
| scoring/storage contract는 유지한다 | 이번 slice는 engine input guard만 다룬다 | JSONL layout, `Insight`, scorer formula 변화 없음 |

## 현재 상태 분석

`mimir/analysis/engine.py`는 AN4 이후 다음 구조다.

```python
for sig in self._signals:
    try:
        result = sig.evaluate(symbol, market, as_of, self._reader)
    except Exception:
        logger.exception(
            "analysis signal '%s' failed for %s/%s; skipping",
            _signal_id(sig),
            key,
            symbol,
        )
        continue
    if result is not None:
        results.append(result)
```

`mimir/analysis/signals/base.py`의 `Signal.evaluate()`는 `SignalResult | None`을 약속하지만, runtime enforcement는 없다.

```python
class Signal(Protocol):
    id: str

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None: ...
```

`SignalResult` 자체는 pydantic 모델이고 `extra="forbid"`, `strength/confidence` bounds, non-negative `weight`를 검증한다. 이 모델을 만들지 않고 raw object를 반환하는 경우만 engine boundary에서 걸러야 한다.

## 목표

- `Signal.evaluate()` 반환값이 `None`이면 기존처럼 signal 없음으로 처리한다.
- 반환값이 `SignalResult`면 기존처럼 scoring input에 append한다.
- 반환값이 `None`도 `SignalResult`도 아니면 error log 후 해당 signal result만 skip한다.
- malformed result 뒤에 오는 같은 symbol의 정상 signal은 계속 score에 들어간다.
- malformed result만 있는 symbol은 insight를 생성하지 않는다.
- malformed result만 있는 rerun도 `replace_partition()`을 호출해 stale insight를 제거한다.
- log에는 signal id, watchlist market key/symbol, 실제 반환 타입이 남는다.

## 목표가 아닌 것

| 항목 | 제외 이유 |
| ---- | --------- |
| dict/object를 `SignalResult`로 coercion | plugin 버그를 숨기고 잘못된 분석값을 만들 수 있다 |
| plugin sandbox/process isolation | AN1 trust boundary는 in-process trusted plugin이다 |
| source/builder plugin 정책 변경 | 이번 경계는 engine runtime result만 다룬다 |
| scoring formula 변경 | 정상 `SignalResult`를 합치는 방식은 유지한다 |
| 새 manifest/dataset | 작은 runtime hardening이며 저장 schema를 바꾸지 않는다 |
| retry/backoff | malformed return은 재시도 대상이 아니라 signal 구현 계약 위반이다 |

## 설계

`mimir/analysis/engine.py`가 `SignalResult`를 import한다.

```python
from mimir.analysis.signals.base import Signal, SignalResult
```

Signal loop는 exception handling 뒤에 result type guard를 둔다.

```python
if result is None:
    continue
if not isinstance(result, SignalResult):
    logger.error(
        "analysis signal '%s' returned invalid result type %s for %s/%s; skipping",
        _signal_id(sig),
        type(result).__name__,
        key,
        symbol,
    )
    continue
results.append(result)
```

`logger.error`를 쓰는 이유는 exception이 발생한 것은 아니지만 signal contract가 깨졌기 때문이다. `logger.exception`처럼 traceback을 만들 필요는 없다. 반환값 repr은 secret이나 큰 payload를 log에 흘릴 수 있으므로 남기지 않고 타입명만 남긴다.

## 테스트

| 테스트 | 고정하는 계약 |
| ---- | ---- |
| `test_engine_skips_malformed_signal_result_and_scores_remaining_signal` | malformed return이 같은 symbol의 다음 정상 signal scoring/storage를 막지 않는다 |
| `test_engine_clears_stale_insights_when_only_malformed_results` | malformed-only rerun도 `replace_partition()`까지 도달해 stale insight를 제거한다 |
| 기존 AN4 exception tests | exception isolation과 next-symbol continuation이 그대로 유지된다 |

RED는 현재 engine이 raw dict/object를 `results`에 넣고 `score()`에서 `AttributeError`로 abort하는 것이다.
GREEN은 malformed result를 error log 후 skip하고 정상 result 또는 stale clearing 경로가 계속되는 것이다.

## 롤아웃

마이그레이션은 없다. 올바른 built-in signal과 plugin signal은 같은 결과를 낸다.
잘못된 plugin은 전체 analysis run failure 대신 해당 signal/symbol 누락과 error log를 보게 된다.

## 보안·비용 영향

- 새 네트워크 호출이 없다.
- 새 dependency가 없다.
- LLM 유료 경로는 계속 `llm_sentiment_enabled`, `ANTHROPIC_API_KEY`, optional package 조건을 모두 만족할 때만 켜진다.
- Invalid result log는 반환값 repr을 남기지 않고 타입명만 남겨 secret leakage 위험을 줄인다.
- Plugin sandbox 정책은 바뀌지 않는다. Plugin은 여전히 trusted in-process code다.

---

**버전**: v1.0
**작성일**: 2026-06-25
**상태**: Implemented
**관련 문서**: [AN4 analysis engine signal isolation](AN4_analysis_engine_signal_isolation_tech_spec_2026_06_25.md), [AN5 analysis signal specs injection](AN5_analysis_signal_specs_injection_tech_spec_2026_06_25.md), [analysis scoring reference](../../../reference/analysis/scoring.md)
