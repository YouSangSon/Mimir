# AN3 Analysis Plugin Built-in Guard Tech Spec

## 한눈에 보기

이번 변경은 `analysis.plugins`가 built-in signal id를 겨냥할 때 더 정확히 경고한다.
외부 plugin이 없는 것처럼 보이는 generic warning 대신 "built-in signal은 이 namespace를 읽지 않는다"를 알려준다.
`llm_sentiment`처럼 별도 opt-in key가 있는 built-in signal은 올바른 설정 key를 안내한다.
Signal discovery, 기본 signal 순서, LLM off-by-default 정책은 바꾸지 않는다.

## 요약

`analysis.plugins.<signal_id>`는 외부 analysis signal plugin 전용 namespace다. 사용자가 실수로 `analysis.plugins.news_volume`이나 `analysis.plugins.llm_sentiment`를 쓰면 현재 builder는 "matching signal spec이 없다"는 generic warning을 낼 수 있다.

| 결정 | 이유 | 결과 |
| ---- | ---- | ---- |
| built-in signal id를 별도 분류한다 | built-in 설정 오용과 plugin typo는 다른 문제다 | warning이 원인을 직접 말한다 |
| `llm_sentiment`도 built-in config id로 취급한다 | `llm_sentiment`는 `BUILTIN_SIGNAL_SPECS`에는 없지만 Mimir 내장 signal이다 | `analysis.plugins.llm_sentiment` 오용을 잡는다 |
| 설정 hint가 있는 built-in은 올바른 namespace를 알려준다 | 사용자가 바로 수정할 수 있어야 한다 | `use llm_sentiment_enabled instead` 같은 메시지 |
| 외부 plugin typo warning은 유지한다 | 실제 missing plugin config도 여전히 운영자가 알아야 한다 | 기존 unmatched plugin test는 유지 |
| Entry point loading 정책은 유지한다 | 이번 slice는 warning precision만 다룬다 | 기본 path import/network invariant 유지 |

## 현재 상태 분석

`mimir/analysis/builder.py`의 `_warn_for_unmatched_analysis_plugin_settings()`는 현재 `specs`에 없는 `analysis_plugin_settings` key를 모두 같은 warning으로 처리한다.

```python
logger.warning(
    "analysis plugin config '%s' has no matching signal spec",
    signal_id,
)
```

`build_signals()`는 `analysis.plugins`가 비어 있으면 plugin entry point를 읽지 않는다. 설정이 있으면 plugin specs만 로드한 뒤 `_build_signals_from_specs(settings, cfg, plugin_specs)`를 호출한다. 이때 `specs`는 외부 plugin specs만 담고, built-in specs는 들어 있지 않다.

그래서 `analysis.plugins.news_volume`은 "plugin이 없다"처럼 보인다. 실제로는 built-in `news_volume`이 존재하지만, 그 signal은 `analysis.plugins`를 읽지 않는다.

source builder는 이미 더 구체적인 정책을 갖고 있다. `sources.plugins.rss`처럼 built-in source id를 겨냥하면 "built-in source를 target했다"는 warning을 낸다. analysis builder도 같은 사용자 경험을 가져야 한다.

## 목표

- `analysis.plugins.<id>`가 built-in analysis signal id를 겨냥하면 built-in 전용 warning을 낸다.
- `news_volume`, `macro_regime`, `llm_sentiment`처럼 대체 설정 namespace가 있는 signal은 hint를 포함한다.
- `filing_event`, `price_momentum`처럼 plugin namespace로 설정할 수 없는 built-in signal은 "built-in signals do not read analysis.plugins"를 말한다.
- 외부 plugin typo는 기존 "has no matching signal spec" warning을 유지한다.
- `build_signals()` 기본 경로는 entry point를 읽지 않고 `anthropic`을 import하지 않는다.
- Duplicate id, factory id mismatch, broken plugin import 정책은 바꾸지 않는다.

## 목표가 아닌 것

| 항목 | 제외 이유 |
| ---- | --------- |
| built-in signal 설정 surface 추가 | 이번 변경은 warning precision이다. 새 config key를 만들지 않는다. |
| `llm_sentiment`를 `SignalSpec`으로 이동 | 기존 AN1 spec에서 별도 refactor로 미룬 결정이다. |
| plugin config schema 검증 확대 | plugin 내부 schema는 plugin factory가 소유한다. |
| entry point discovery 정책 변경 | installed package만으로 import되지 않는 invariant를 유지한다. |

## 설계

`mimir/analysis/builder.py`에 built-in id와 hint를 둔다.

```python
BUILTIN_SIGNAL_CONFIG_HINTS = {
    "news_volume": "analysis.news instead",
    "macro_regime": "analysis.macro_regime instead",
    "llm_sentiment": "llm_sentiment_enabled instead",
}
BUILTIN_ANALYSIS_SIGNAL_IDS = {
    *(spec.id for spec in BUILTIN_SIGNAL_SPECS),
    "llm_sentiment",
}
```

`_warn_for_unmatched_analysis_plugin_settings()`는 순서를 이렇게 둔다.

1. `signal_id`가 built-in이면 built-in warning.
2. `signal_id`가 현재 plugin specs에 없으면 기존 unmatched warning.
3. matching plugin spec이 있으면 warning 없음.

Warning 문구는 source builder와 같은 형태를 따른다.

```python
"analysis plugin config '%s' targets built-in signal '%s'; use %s"
"analysis plugin config '%s' targets built-in signal '%s'; built-in signals do not read analysis.plugins"
```

## 테스트

| 테스트 | 고정하는 계약 |
| ---- | ---- |
| `test_builder_warns_when_analysis_plugin_namespace_targets_configurable_builtin_signal` | `analysis.plugins.news_volume`은 built-in warning과 `analysis.news` hint를 낸다 |
| `test_builder_warns_when_analysis_plugin_namespace_targets_llm_sentiment` | `analysis.plugins.llm_sentiment`은 built-in warning과 `llm_sentiment_enabled` hint를 낸다 |
| 기존 unmatched plugin test | missing external plugin warning은 유지된다 |
| 기존 default path tests | plugin 설정이 없으면 entry point를 읽지 않고 `anthropic`을 import하지 않는다 |

## 롤아웃

마이그레이션은 없다. 잘못된 `analysis.plugins` 설정을 쓰던 환경은 더 구체적인 warning을 보게 된다. 정상 plugin 설정과 built-in signal 동작은 그대로다.

## 보안·비용 영향

- 새 네트워크 호출이 없다.
- secret 경로가 바뀌지 않는다.
- plugin sandbox 정책이 바뀌지 않는다.
- LLM 유료 경로는 계속 `llm_sentiment_enabled`, `ANTHROPIC_API_KEY`, optional package 조건을 모두 만족할 때만 켜진다.

---

**버전**: v1.0
**작성일**: 2026-06-25
**상태**: Draft
**관련 문서**: [AN1 signal plugin entry points](AN1_signal_plugin_entrypoints_tech_spec_2026_06_23.md), [config reference](../../../reference/config/sources.md)
