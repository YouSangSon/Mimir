# AN4 Analysis Engine Signal Isolation Tech Spec

## 한눈에 보기

이번 변경은 한 analysis signal의 `evaluate()` 예외가 전체 analysis run을 중단하지 않게 한다.
실패한 signal 결과만 해당 symbol에서 생략하고, 같은 symbol의 다른 signal과 다음 symbol은 계속 평가한다.
Insight scoring formula, signal interface, 저장 schema, plugin discovery, LLM 비용 gate는 바꾸지 않는다.

## 요약

AN1 이후 외부 analysis signal plugin은 `mimir.analysis_signals` entry point와 `analysis.plugins.<signal_id>` 설정으로 score pipeline에 합류할 수 있다. Plugin 코드는 Mimir 프로세스 안에서 실행되는 trusted code지만, 평가 중 런타임 예외 하나가 모든 symbol의 insight 생성을 멈추는 것은 blast radius가 너무 크다.

| 결정 | 이유 | 결과 |
| ---- | ---- | ---- |
| `AnalysisEngine`가 signal 평가 예외를 catch한다 | built-in과 plugin signal 모두 같은 `Signal` protocol을 쓰며 평가 단계에서 구분되지 않는다 | 한 signal 실패가 전체 run을 멈추지 않는다 |
| 실패한 signal은 해당 symbol에서 skip한다 | malformed `SignalResult`를 만들거나 score에 섞으면 분석 오염이다 | `None`과 같은 생략 경계로 처리 |
| `logger.exception`으로 signal id, symbol, market을 남긴다 | 운영자가 어떤 signal/symbol이 빠졌는지 알아야 한다 | traceback은 보존되고 run은 계속된다 |
| `Exception`만 catch한다 | `KeyboardInterrupt`, `SystemExit` 같은 process-control 예외는 삼키면 안 된다 | 운영 중단 신호는 계속 loud failure |
| scoring/storage contract는 유지한다 | 이번 slice는 isolation boundary만 다룬다 | JSONL layout, `Insight`, `SignalResult`, scorer formula 변화 없음 |

## 현재 상태 분석

`mimir/analysis/engine.py`는 market, symbol, signal을 순회하면서 곧바로 `sig.evaluate(...)`를 호출한다.

```python
for sig in self._signals:
    result = sig.evaluate(symbol, market, as_of, self._reader)
    if result is not None:
        results.append(result)
```

이 구조에서 signal 하나가 예외를 던지면 다음 일이 모두 일어나지 않는다.

- 같은 symbol의 나머지 signal 평가
- 다음 symbol/market 평가
- `replace_partition(Dataset.INSIGHTS, as_of, records)` 호출

반면 `LlmSentimentSignal` 내부는 classifier runtime failure를 이미 격리한다. 예외를 warning/exception log로 남기고 해당 symbol의 `llm_sentiment` 결과만 `None`으로 생략한다. Engine 레벨에도 같은 fail-closed 경계가 필요하다.

## 목표

- signal `evaluate()`가 `Exception`을 던지면 engine은 그 signal 결과만 생략한다.
- 같은 symbol의 다른 signal은 계속 평가되어 score에 들어간다.
- 한 symbol에서 signal이 실패해도 다음 symbol 평가는 계속된다.
- 모든 signal이 실패하거나 `None`이면 기존처럼 그 symbol의 insight는 생성하지 않는다.
- log에는 signal id, symbol, market, traceback이 남는다.
- `replace_partition()` stale insight clearing 계약은 유지된다.

## 목표가 아닌 것

| 항목 | 제외 이유 |
| ---- | --------- |
| signal retry/backoff | 실패 원인이 IO인지 logic bug인지 engine은 모른다. retry는 signal 소유자가 결정한다. |
| plugin sandbox/process isolation | AN1 trust boundary는 in-process trusted plugin이다. sandbox는 별도 아키텍처다. |
| built-in과 plugin failure policy 분리 | runtime `Signal` protocol만으로 출처를 구분하지 않는다. |
| partial failure manifest dataset | 현재 insight schema를 바꾸지 않는 작은 hardening이다. |
| scoring formula 변경 | 실패한 signal은 score 입력에서 빠질 뿐이다. |

## 설계

`mimir/analysis/engine.py`에 module logger와 작은 helper를 둔다.

```python
import logging

logger = logging.getLogger(__name__)


def _signal_id(signal: Signal) -> str:
    return getattr(signal, "id", signal.__class__.__name__)
```

Signal loop는 `Exception`만 catch한다.

```python
for sig in self._signals:
    try:
        result = sig.evaluate(symbol, market, as_of, self._reader)
    except Exception:
        logger.exception(
            "analysis signal '%s' failed for %s/%s; skipping",
            _signal_id(sig),
            market.value,
            symbol,
        )
        continue
    if result is not None:
        results.append(result)
```

`logger.exception`은 traceback을 자동으로 남긴다. `market.value`는 log text를 `us/AAPL`, `kr/005930`처럼 사람이 읽기 쉽게 만든다.

## 테스트

| 테스트 | 고정하는 계약 |
| ---- | ---- |
| `test_engine_skips_failed_signal_and_scores_remaining_signal` | 한 signal이 예외를 던져도 같은 symbol의 다음 signal 결과로 insight를 만들고 저장한다 |
| `test_engine_continues_to_next_symbol_after_signal_failure` | 특정 symbol에서 signal이 실패해도 다음 symbol은 평가되고 저장된다 |
| 기존 stale insight clearing test | 새 exception boundary가 `replace_partition()` 호출을 건너뛰지 않는다 |

RED는 현재 engine이 첫 예외에서 abort하므로 두 신규 테스트가 실패하는 것이다. GREEN은 engine이 exception log를 남기고 계속 평가하는 것이다.

## 롤아웃

마이그레이션은 없다. 실패하던 signal이 있던 환경은 이제 전체 analysis run 실패 대신 해당 signal/symbol 누락과 exception log를 보게 된다. 정상 signal 결과와 persisted `insights` payload shape는 그대로다.

## 보안·비용 영향

- 새 네트워크 호출이 없다.
- LLM 유료 경로는 계속 `llm_sentiment_enabled`, `ANTHROPIC_API_KEY`, optional package 조건을 모두 만족할 때만 켜진다.
- Plugin sandbox 정책은 바뀌지 않는다. Plugin은 여전히 trusted in-process code다.
- 예외 traceback은 log에 남는다. Secret을 예외 메시지에 넣지 않는 책임은 기존처럼 signal/plugin 구현자가 가진다.

---

**버전**: v1.0
**작성일**: 2026-06-25
**상태**: Draft
**관련 문서**: [AN1 signal plugin entry points](AN1_signal_plugin_entrypoints_tech_spec_2026_06_23.md), [AN2 LLM classifier cardinality](AN2_LLM_classifier_cardinality_tech_spec_2026_06_23.md), [analysis scoring reference](../../../reference/analysis/scoring.md)
