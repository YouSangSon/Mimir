# AN5 Analysis Signal Specs Injection Tech Spec

## 한눈에 보기

이번 변경은 `build_signals()`에 public `specs=` injection seam을 추가한다.
외부 analysis signal plugin을 entry point 설치 없이도 테스트·임베디드 호출자가 직접 주입할 수 있게 하되, 기존 opt-in 설정 계약은 그대로 유지한다.
Built-in signal은 계속 기본 table에서 먼저 생성되고, 주입된 `SignalSpec`은 외부 plugin spec으로만 해석된다.

## 요약

AN1은 외부 analysis signal plugin을 `mimir.analysis_signals` entry point와 `analysis.plugins.<signal_id>` 설정으로 연결했다. 이 경로는 설치된 package를 배포 단위로 쓰는 운영 환경에는 맞지만, 테스트·임베디드 실행·내부 extension host에는 불필요하게 packaging metadata를 요구한다.

Source builder는 이미 `build_sources(..., specs=...)`로 public injection seam을 제공한다. Analysis builder에도 같은 수준의 직접 주입 seam이 필요하다. 다만 analysis 쪽은 built-in signal과 LLM gate가 별도 정책을 갖기 때문에, `specs`를 전체 signal list replacement로 해석하지 않는다.

| 결정 | 이유 | 결과 |
| ---- | ---- | ---- |
| `build_signals(..., specs=...)`를 추가한다 | entry point 없이 plugin specs를 직접 주입하는 public API가 필요하다 | tests/embedded callers가 private `_build_signals_from_specs()`에 의존하지 않는다 |
| `specs`는 외부/plugin signal specs만 의미한다 | built-in signal 순서와 기본 pipeline 계약을 보존해야 한다 | built-in 4개가 먼저 생성되고 configured injected plugin만 뒤에 붙는다 |
| `specs is None`일 때만 entry point를 읽는다 | 기존 installed-plugin 운영 경로는 그대로 유지한다 | 현재 default와 AN1 entry point behavior가 깨지지 않는다 |
| `specs`가 제공되면 entry point를 읽지 않는다 | 직접 주입 호출자는 packaging metadata와 installed package side effect를 피해야 한다 | 테스트·임베디드 호출이 결정론적이다 |
| plugin config opt-in은 계속 필수다 | 설치 또는 주입만으로 signal이 실행되면 AN1 off-by-default 계약이 깨진다 | `analysis.plugins.<signal_id>`가 있는 injected spec만 build된다 |
| duplicate id는 built-in과 injected specs 전체에서 검증한다 | score 해석과 운영 log에서 signal id는 식별자다 | built-in id를 덮어쓰는 injected spec은 loud failure |

## 현재 상태 분석

`mimir/analysis/builder.py`에는 이미 다음 구성요소가 있다.

- `SignalSpec`
- `BUILTIN_SIGNAL_SPECS`
- `_load_entry_point_signal_specs()`
- `_build_signals_from_specs(settings, config, specs, ...)`
- `build_signals(config, settings, *, classifier=None)`

하지만 public `build_signals()`는 plugin specs를 직접 받을 수 없다.

현재 테스트가 plugin spec을 직접 다루려면 private helper를 호출해야 한다.

```python
signals = _build_signals_from_specs(
    Settings.from_env({}),
    cfg,
    (SignalSpec("plugin_quality", build_plugin),),
)
```

이 방식은 helper의 private status와 public extension story가 어긋난다. External plugin authors와 embedded callers가 사용할 공개 seam은 `build_signals()`여야 한다.

## 목표

- `build_signals()`가 keyword-only `specs: Sequence[SignalSpec] | None = None`를 받는다.
- `specs=None`이면 현재처럼 `analysis.plugins`가 있을 때만 `mimir.analysis_signals` entry point를 읽는다.
- `specs`가 제공되면 entry point를 읽지 않는다.
- Injected specs는 built-in replacement가 아니라 external/plugin specs로 취급한다.
- Built-in signal은 계속 `BUILTIN_SIGNAL_SPECS`에서 먼저 생성된다.
- Injected plugin signal은 `analysis.plugins.<signal_id>` 설정이 있을 때만 생성된다.
- Explicit `specs=()`와 non-empty `analysis.plugins`는 unmatched config warning을 유지한다.
- Built-in id와 injected plugin id가 중복되면 `ValueError`로 실패한다.
- LLM sentiment gate와 classifier injection semantics는 바꾸지 않는다.

## 목표가 아닌 것

| 항목 | 제외 이유 |
| ---- | --------- |
| `llm_sentiment`를 `SignalSpec` table로 이동 | 별도 paid SDK/off-by-default gate가 있어 이번 public seam과 무관하다 |
| entry point schema discovery | Core는 plugin schema를 모른다는 AN1 계약을 유지한다 |
| plugin sandbox | Plugin은 여전히 trusted in-process code다 |
| source builder `specs` semantics 변경 | Source seam은 이미 운영 중인 public API다 |
| built-in signal disable/reorder API | 이번 변경은 external spec injection만 다룬다 |

## 설계

`build_signals()` signature를 keyword-only `specs`로 확장한다.

```python
def build_signals(
    config: SourcesConfig | None = None,
    settings: Settings | None = None,
    *,
    classifier: HeadlineClassifier | None = None,
    specs: Sequence[SignalSpec] | None = None,
) -> list[Signal]:
```

Plugin spec 선택은 다음 분기로 고정한다.

```python
if specs is None:
    plugin_specs = _load_entry_point_signal_specs() if cfg.analysis_plugin_settings else ()
else:
    plugin_specs = tuple(specs)

if cfg.analysis_plugin_settings or plugin_specs:
    _validate_unique_signal_ids((*BUILTIN_SIGNAL_SPECS, *plugin_specs))
    signals.extend(_build_signals_from_specs(settings, cfg, plugin_specs))
```

`if cfg.analysis_plugin_settings or plugin_specs`가 중요하다. `specs=()`를 명시한 호출에서도 `analysis.plugins`가 비어 있지 않으면 `_build_signals_from_specs()`가 unmatched config warning을 낼 수 있어야 한다.

## 테스트

| 테스트 | 고정하는 계약 |
| ---- | ---- |
| `test_build_signals_accepts_injected_plugin_specs_after_builtins` | injected plugin spec은 configured일 때 built-in 뒤에 append된다 |
| `test_build_signals_with_injected_specs_does_not_read_entry_points` | `specs` 제공 시 entry point metadata를 읽지 않는다 |
| `test_build_signals_injected_specs_still_require_analysis_plugin_config` | injected spec도 `analysis.plugins.<signal_id>` opt-in 없이는 build되지 않는다 |
| `test_build_signals_injected_duplicate_builtin_signal_id_raises` | injected spec이 built-in signal id와 충돌하면 loud failure |
| `test_build_signals_empty_injected_specs_warns_for_unmatched_plugin_config` | explicit `specs=()`가 unmatched plugin config warning을 숨기지 않는다 |

RED는 현재 `build_signals(..., specs=...)`가 `TypeError`를 내거나, explicit empty specs warning 계약을 만족하지 못하는 것이다.
GREEN은 public builder API가 private helper 없이 동일한 plugin opt-in semantics를 제공하는 것이다.

## 롤아웃

마이그레이션은 없다. 기존 호출자는 새 keyword-only 인자를 쓰지 않으면 동일하게 동작한다.

새 API를 쓰는 테스트·임베디드 호출자는 entry point packaging 없이 `SignalSpec` tuple을 넘길 수 있다.
설정은 계속 `analysis.plugins.<signal_id>` 아래에 있어야 하므로 installed package와 injected spec 모두 같은 opt-in 규칙을 따른다.

## 보안·비용 영향

- 새 네트워크 호출이 없다.
- 새 dependency가 없다.
- LLM 유료 경로는 계속 `llm_sentiment_enabled`, `ANTHROPIC_API_KEY`, optional package 조건을 모두 만족할 때만 켜진다.
- Directly injected signal factory도 trusted in-process code다. Sandbox 정책은 바뀌지 않는다.

---

**버전**: v1.0
**작성일**: 2026-06-25
**상태**: Draft
**관련 문서**: [AN1 signal plugin entry points](AN1_signal_plugin_entrypoints_tech_spec_2026_06_23.md), [AN3 analysis plugin built-in guard](AN3_analysis_plugin_builtin_guard_tech_spec_2026_06_25.md), [extensibility guide](../../../architecture/extensibility/README.md)
