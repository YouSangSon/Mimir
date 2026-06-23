# AN1 Signal Plugin Entry Points Tech Spec

## 한눈에 보기

이번 변경은 Mimir 밖의 Python package가 새 분석 시그널을 추가할 수 있게 한다.
기본 실행은 그대로 내장 4개 시그널만 만든다.
외부 시그널은 `mimir.analysis_signals` entry point와 명시 설정이 있을 때만 붙는다.
스코어러와 분석 엔진은 바꾸지 않는다.

## 요약

Mimir는 수집 소스에는 plugin seam(외부 package가 끼어드는 확장 지점)이 있다. 하지만 분석 시그널은 아직 `build_signals()` 안에 직접 고정되어 있다.

| 결정 | 이유 | 결과 |
| ---- | ---- | ---- |
| `SignalSpec` 테이블을 만든다 | 내장 시그널 생성 규칙을 한 곳에 모은다 | built-in 순서와 기본 시그널 수를 테스트로 고정 |
| `mimir.analysis_signals` entry point를 읽는다 | 외부 package가 Mimir repo 수정 없이 시그널을 추가한다 | source plugin과 같은 배포 방식 |
| plugin 설정은 `analysis.plugins.<signal_id>`에 둔다 | 수집 source 설정과 분석 signal 설정을 분리한다 | typo는 core 경계에서 fail-loud |
| plugin은 명시 설정이 있을 때만 생성한다 | 설치만으로 외부 코드나 비용 경로가 실행되는 일을 막는다 | 기본 경로는 네트워크 0·유료 호출 0 유지 |
| `AnalysisEngine`과 `score()`는 건드리지 않는다 | 엔진은 이미 `list[Signal]`을 주입받는다 | 변경 범위가 discovery와 construction에 머문다 |

## 현재 상태 분석

### 분석 시그널 생성 경로

`mimir/analysis/builder.py:25`의 `build_signals()`는 내장 시그널 4개를 직접 만든다.

- `FilingEventSignal`
- `NewsVolumeSignal`
- `PriceMomentumSignal`
- `MacroRegimeSignal`

같은 함수는 `llm_sentiment_enabled`, `ANTHROPIC_API_KEY`, optional package 조건이 모두 맞을 때만 `LlmSentimentSignal`을 붙인다. `tests/analysis/test_builder.py`는 no-args 경로가 내장 4개만 반환하고 `anthropic`을 import하지 않는다고 고정한다.

### 이미 열려 있는 엔진 경계

`mimir/analysis/engine.py:15`의 `AnalysisEngine`은 생성자에서 `list[Signal]`을 받는다. 실행 중에는 각 signal의 `evaluate()`만 호출한다. 따라서 엔진은 이미 외부 signal을 받을 수 있다.

`mimir/analysis/signals/base.py:46`의 `Signal` protocol은 좁다.

```python
class Signal(Protocol):
    id: str

    def evaluate(
        self, symbol: str, market: Market, as_of: date, reader: DataReader
    ) -> SignalResult | None: ...
```

`SignalResult`는 `extra="forbid"`, `strength/confidence` 0..1, `weight >= 0`을 검증한다. 외부 signal이 잘못된 score payload를 내면 pydantic 경계에서 실패한다.

### 수집 source plugin 선례

`mimir/core/builder.py:51`의 `SourceSpec`은 source id, factory, secret gate, module gate를 한 곳에 묶는다. `mimir/core/builder.py:176` 이후는 `mimir.sources` entry point를 읽고, source id 중복·잘못된 object type·metadata mismatch를 실패시킨다. Broken plugin import는 warning 후 skip한다.

이 선례는 signal plugin에도 맞다. 단, signal에는 `SourceMeta` 같은 metadata 객체가 없으므로 `id`와 protocol만 검증한다.

## 목표

- `SignalSpec`과 `BUILTIN_SIGNAL_SPECS`를 추가한다.
- `build_signals()`의 기본 결과와 순서를 유지한다.
- `mimir.analysis_signals` entry point group에서 외부 `SignalSpec`을 읽는다.
- Entry point는 `SignalSpec` 하나 또는 `tuple[SignalSpec, ...]`를 로드할 수 있다.
- 단일 `SignalSpec` entry point는 entry point 이름과 `SignalSpec.id`가 같아야 한다.
- 외부 signal plugin은 `analysis.plugins.<signal_id>` 설정이 있을 때만 생성한다.
- Plugin factory는 `Settings`와 `SourcesConfig`를 받는다.
- Plugin factory는 `SourcesConfig.parse_analysis_plugin_config()`로 자기 설정 모델을 검증할 수 있다.
- Broken entry point import는 warning 후 skip한다.
- 잘못된 object type, duplicate signal id, built signal id mismatch는 `ValueError`로 실패한다.
- Missing secret/module gate는 warning 후 skip한다.
- Docs가 trust boundary와 failure policy를 설명한다.

## 목표가 아닌 것

| 항목 | 제외 이유 |
| ---- | --------- |
| signal weight YAML 노출 | 모든 signal weight는 현재 코드 상수이며, 부분 노출은 catalog §6의 보류 결정과 충돌한다. |
| scoring hook 또는 custom scorer | 스코어러는 `SignalResult` list를 합치는 단일 계약이다. 이번 slice는 signal discovery만 연다. |
| `AnalysisEngine` 변경 | 엔진은 이미 `list[Signal]` 주입을 받는다. |
| plugin sandbox | source plugin과 동일하게 신뢰된 package만 설치한다는 운영 경계를 문서화한다. |
| 외부 package 배포 | entry point seam만 제공한다. |
| 설치만으로 plugin 자동 실행 | 외부 signal은 `analysis.plugins.<signal_id>` 설정이 있어야 생성된다. |

## 설계

### 1. SignalSpec

`mimir/analysis/builder.py`에 `SignalSpec`을 둔다.

```python
@dataclass(frozen=True)
class SignalSpec:
    id: str
    factory: Callable[[Settings, SourcesConfig], Signal]
    required_secret_attr: str | None = None
    required_secret_name: str | None = None
    required_module: str | None = None
    missing_module_hint: str | None = None
```

`SignalSpec`에는 "내장 여부" flag를 두지 않는다. 내장 signal은 `BUILTIN_SIGNAL_SPECS`에 들어 있기 때문에 항상 생성 대상이고, plugin signal은 entry point에서 로드한 spec 중 `analysis.plugins.<signal_id>` 설정이 있는 것만 생성 대상이다. 이 구분을 public dataclass flag로 노출하지 않으면 외부 plugin이 실수로 내장 signal처럼 auto-enable되는 경로를 만들지 않는다.

### 2. Built-in signal table

`BUILTIN_SIGNAL_SPECS` 순서는 기존 `build_signals()` 순서를 그대로 따른다.

```python
BUILTIN_SIGNAL_SPECS = (
    SignalSpec("filing_event", lambda settings, cfg: FilingEventSignal()),
    SignalSpec(
        "news_volume",
        lambda settings, cfg: NewsVolumeSignal(
            aliases=merge_news_aliases(
                cfg.news_aliases,
                include_defaults=cfg.use_default_news_aliases,
            )
        ),
    ),
    SignalSpec("price_momentum", lambda settings, cfg: PriceMomentumSignal()),
    SignalSpec(
        "macro_regime",
        lambda settings, cfg: MacroRegimeSignal(rate_series=cfg.macro_regime_rate_series),
    ),
)
```

LLM sentiment는 기존 gate가 복잡하고 paid/off-by-default 성격이 강하다. 첫 implementation에서는 현재 explicit branch를 유지한다. `SignalSpec`으로 옮기는 것은 별도 refactor로 미룬다.

### 3. Entry point group

외부 package는 아래 entry point를 선언한다.

```toml
[project.entry-points."mimir.analysis_signals"]
acme_quality = "acme_mimir.signals:ACME_QUALITY_SIGNAL_SPEC"
```

단일 spec은 entry point 이름과 `SignalSpec.id`가 같아야 한다.

```python
from mimir.analysis.builder import SignalSpec

ACME_QUALITY_SIGNAL_SPEC = SignalSpec(
    "acme_quality",
    lambda settings, cfg: AcmeQualitySignal(
        cfg.parse_analysis_plugin_config("acme_quality", AcmeQualityConfig)
    ),
)
```

한 package가 여러 signal을 제공하면 tuple을 로드할 수 있다. 이때 entry point 이름은 provider bundle 이름이고, tuple 내부의 각 id는 서로 달라야 한다.

### 4. `analysis.plugins` 설정

`sources.yaml`의 top-level `analysis:` 블록 아래에 plugin 설정 namespace를 둔다.

```yaml
analysis:
  plugins:
    acme_quality:
      threshold: 0.7
      symbols: ["AAPL", "MSFT"]
```

Core parser는 `analysis.plugins.<signal_id>` 값이 mapping인지까지만 검증한다. Plugin은 자기 pydantic model로 schema를 검증한다.

`SourcesConfig`에 아래 helper를 추가한다.

```python
analysis_plugin_settings: dict[str, dict[str, Any]] = Field(default_factory=dict)

def analysis_plugin_config(self, signal_id: str) -> dict[str, Any]:
    return dict(self.analysis_plugin_settings.get(signal_id, {}))

def parse_analysis_plugin_config(
    self, signal_id: str, model: type[PluginConfig]
) -> PluginConfig:
    return model.model_validate(self.analysis_plugin_config(signal_id))
```

기존 `sources.plugins`는 source plugin 전용으로 유지한다.

### 5. Plugin 생성 정책

Signal plugin은 설치만으로 실행되지 않는다.

`build_signals()`의 기본 경로는 `analysis.plugins` 설정이 비어 있으면 외부 entry point를 조회하지 않는다. 즉 package 설치만으로 factory 실행뿐 아니라 plugin module import도 일어나지 않는다. 직접 `load_signal_specs()`를 호출한 경우에만 entry point discovery가 수행된다.

| 상황 | 처리 |
| ---- | ---- |
| `analysis.plugins.<id>` 있고 matching `SignalSpec.id` 있음 | factory 실행 |
| `analysis.plugins.<id>` 있으나 matching spec 없음 | warning |
| plugin spec 있으나 `analysis.plugins.<id>` 없음 | 생성하지 않음 |
| plugin spec id가 built-in과 중복 | `ValueError` |
| plugin factory가 만든 signal의 `id`가 spec id와 다름 | `ValueError` |
| plugin import 실패 | warning 후 해당 entry point skip |
| wrong object type | `ValueError` |
| required secret/module 없음 | warning 후 skip |

이 정책은 source plugin보다 더 보수적이다. 분석 signal은 저장 데이터를 읽고 점수에 영향을 주기 때문이다.

### 6. Trust boundary

Signal plugin code는 Mimir process 안에서 실행된다. Plugin은 `Settings`, `SourcesConfig`, `DataReader`를 통해 환경과 저장 데이터를 볼 수 있다. Mimir는 plugin을 sandbox하지 않는다. 운영자는 신뢰한 package만 설치해야 한다.

## 테스트 전략

| 테스트 | 고정하는 계약 |
| ---- | ---- |
| `test_builtin_signal_specs_keep_existing_order` | 내장 signal 순서가 유지된다. |
| `test_default_path_does_not_import_anthropic` | 기존 off-by-default LLM invariant가 유지된다. |
| `test_default_path_does_not_read_signal_entry_points` | plugin 설정이 없으면 entry point discovery도 하지 않는다. |
| `test_load_entry_point_signal_specs_accepts_single_spec` | 단일 `SignalSpec` entry point를 읽는다. |
| `test_load_entry_point_signal_specs_accepts_sequence` | tuple entry point를 읽는다. |
| `test_entry_point_signal_specs_are_loaded_in_name_order` | plugin은 entry point 이름순으로 로드된다. |
| `test_entry_point_signal_spec_id_must_match_entry_point_name` | 단일 spec 이름 mismatch는 실패한다. |
| `test_broken_entry_point_signal_spec_is_skipped_and_logged` | broken plugin은 built-in signal을 깨지 않는다. |
| `test_entry_point_signal_wrong_object_type_raises_value_error` | 잘못된 plugin 선언은 fail-loud다. |
| `test_build_signals_includes_configured_plugin_signals_after_builtins` | configured plugin signal은 built-in 뒤에 붙는다. |
| `test_unconfigured_plugin_signal_is_not_built` | 설치만으로 signal이 실행되지 않는다. |
| `test_entry_point_duplicate_builtin_signal_id_raises_value_error` | built-in id 충돌은 실패한다. |
| `test_plugin_signal_id_mismatch_raises_value_error` | factory result id mismatch는 실패한다. |
| `test_build_signals_passes_analysis_plugin_namespace_to_factory` | plugin factory가 `analysis.plugins` 설정을 검증한다. |
| `test_builder_warns_for_unmatched_analysis_plugin_config` | 설정은 있지만 plugin 없음이면 warning이다. |
| `test_analysis_plugins_namespace_rejects_non_mapping_config` | `analysis.plugins.<id>`는 mapping이어야 한다. |

## 롤아웃

기본 `build_signals()` 결과는 그대로다. 외부 plugin package가 설치되어도 `analysis.plugins.<signal_id>` 설정이 없으면 signal은 생성되지 않는다.

이 변경은 JSONL 저장 레이아웃, insight payload schema, `idempotency_key`, scoring formula를 바꾸지 않는다. 단, 사용자가 plugin signal을 opt-in하면 해당 signal의 `SignalResult`가 insight payload의 `signals[]`에 추가될 수 있다. 이 동작은 명시 설정이 있을 때만 발생한다.

## 위험과 대응

| 위험 | 대응 |
| ---- | ---- |
| 설치만으로 외부 코드가 실행됨 | plugin signal은 `analysis.plugins.<id>`가 있어야 생성한다. |
| 외부 signal이 점수를 왜곡함 | `SignalResult` boundary가 strength/confidence/weight를 검증한다. |
| plugin 설정 typo가 조용히 무시됨 | core는 namespace mapping을 검증하고, plugin은 pydantic 모델로 자기 schema를 검증한다. |
| built-in signal id 충돌 | duplicate id를 `ValueError`로 실패시킨다. |
| plugin trust boundary 오해 | docs에 sandbox 없음과 secret 취급을 명시한다. |

## 수용 기준

- `build_signals()` no-args 결과는 기존 내장 4개 signal 그대로다.
- Default path는 `anthropic`을 import하지 않는다.
- `mimir.analysis_signals` entry point를 읽는 loader가 있다.
- Plugin signal은 `analysis.plugins.<signal_id>` 설정이 있을 때만 추가된다.
- Broken plugin import는 warning 후 skip된다.
- Wrong object type, duplicate id, built signal id mismatch는 `ValueError`로 실패한다.
- `analysis.plugins` 설정 namespace와 pydantic helper가 있다.
- Extensibility guide, config reference, improvement catalog, tech-spec index가 새 seam을 설명한다.
- Full pytest, ruff, mypy, `git diff --check`가 통과한다.

---

**버전**: v1.0
**작성일**: 2026-06-23
**상태**: Draft
**관련 문서**: `docs/architecture/improvement-catalog.md`, `docs/architecture/extensibility/README.md`, `docs/reference/config/sources.md`
