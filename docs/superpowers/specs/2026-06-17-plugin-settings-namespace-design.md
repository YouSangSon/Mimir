# Source Plugin Settings Namespace — 설계

> **스펙 ID**: A3c
> **작성일**: 2026-06-17
> **상태**: ✅ 구현 완료 (`sources.plugins.<source_id>` namespace + plugin-owned pydantic validation helper). 424 테스트 · ruff · mypy · coverage gate 클린.
> **선행**: [A3 선언적 소스 등록](2026-06-16-declarative-source-registration-design.md) · [A3b Source Plugin Entry Points](2026-06-16-source-entry-points-design.md) · [확장성 카탈로그](../../architecture/improvement-catalog.md)

---

## 1. 한눈에 보기

외부 package는 `mimir.sources` entry point로 source를 추가할 수 있다. 하지만 plugin별 설정을 `sources.yaml`에 안전하게 넣을 곳이 아직 없다.

이번 변경은 `sources.plugins.<source_id>` namespace를 추가한다. Mimir core는 이 namespace를 mapping으로 검증하고 `SourcesConfig.plugin_settings`에 보존한다.

Plugin factory는 `SourcesConfig.plugin_config()`로 raw 설정을 읽거나, `SourcesConfig.parse_plugin_config()`로 자신이 정의한 pydantic 모델을 검증한다. Core는 외부 plugin의 schema를 알 필요가 없다.

---

## 2. 문제

### 2.1 entry point는 source만 넣고 설정 통로는 없다

A3b 이후 외부 package는 `SourceSpec`을 entry point로 등록할 수 있다. 그러나 plugin이 `base_url`, `symbols`, `timeout`, vendor-specific option을 필요로 하면 현재는 선택지가 나쁘다.

1. 환경변수만 추가한다.
2. Mimir 본문 설정 모델을 fork한다.
3. `SourcesConfig`의 기존 typed field를 임의로 재사용한다.

셋 다 확장성이 낮다.

### 2.2 기존 fail-fast config 정책은 유지해야 한다

`sources.yaml`은 typo를 조용히 무시하지 않는다. `sources.fed`나 `analysis.news.aliasez`는 `ValidationError`로 실패한다.

Plugin 설정을 열어 준다고 해서 `sources:` 전체를 `extra="allow"`로 바꾸면 이 정책이 깨진다. 따라서 허용해야 하는 자유도는 `sources.plugins.<source_id>` 아래로만 제한해야 한다.

### 2.3 core가 plugin schema를 알 수는 없다

외부 plugin의 설정 schema는 plugin package가 소유한다. Mimir core가 모든 plugin schema를 import하거나 registry에 강제하면 entry point seam이 무거워진다.

Core는 namespace, raw mapping 보존, pydantic 검증 helper만 제공한다. Plugin factory는 자신이 필요한 모델로 검증한다.

---

## 3. 목표와 비목표

### 목표

- `sources.plugins.<source_id>` 블록을 허용한다.
- 각 plugin config 값은 mapping이어야 한다. scalar/list/string은 설정 오류로 실패한다.
- 기존 built-in source block typo는 계속 `ValidationError`로 실패한다.
- parsed config는 `SourcesConfig.plugin_settings`에 보존된다.
- `SourcesConfig.plugin_config(source_id)`는 해당 plugin 설정의 shallow copy를 반환한다.
- `SourcesConfig.plugin_config(source_id)`는 없는 plugin id에 `{}`를 반환한다.
- `SourcesConfig.parse_plugin_config(source_id, Model)`은 plugin이 제공한 pydantic 모델로 설정을 검증한다.
- `build_sources()`는 `sources.plugins.<source_id>`가 있지만 해당 `SourceSpec.id`가 없으면 warning을 남긴다.
- `sources.plugins.<built_in_id>`는 warning을 남긴다. Built-in source 설정은 기존 `sources.rss`, `sources.fred` 같은 typed block을 써야 한다.
- 문서가 plugin 설정 namespace와 신뢰 경계를 설명한다.

### 비목표

- 외부 plugin의 schema를 core registry에 등록하지 않는다.
- Plugin 설정을 자동으로 typed model로 바꿔 factory에 주입하지 않는다.
- Plugin source를 sandbox하지 않는다.
- Built-in source 설정을 `sources.plugins`로 옮기지 않는다.
- Secrets 저장 방식을 바꾸지 않는다. 민감한 값은 계속 환경변수나 secret store를 써야 한다.

---

## 4. 설계

### 4.1 YAML 형태

```yaml
sources:
  plugins:
    acme_news:
      base_url: "https://internal.example.com/rss"
      symbols: ["AAPL", "MSFT"]
      timeout_seconds: 5
```

`acme_news`는 `SourceSpec.id`와 같은 값이다. 한 entry point가 여러 `SourceSpec`을 반환하면 각 source id 아래에 별도 설정을 둔다.

### 4.2 SourcesConfig

`SourcesConfig`는 plugin 설정을 보존한다.

```python
class SourcesConfig(BaseModel):
    plugin_settings: dict[str, dict[str, Any]] = Field(default_factory=dict)

    def plugin_config(self, source_id: str) -> dict[str, Any]:
        return dict(self.plugin_settings.get(source_id, {}))

    def parse_plugin_config(self, source_id: str, model: type[M]) -> M:
        return model.model_validate(self.plugin_config(source_id))
```

`plugin_config()`는 shallow copy를 반환한다. Plugin factory가 반환 dict를 mutate해도 `SourcesConfig` 내부 상태는 바뀌지 않는다.

### 4.3 Parser

`_SourcesBlock`은 `plugins` 필드를 추가한다.

```python
class _SourcesBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fred: _FredBlock | None = None
    ecos: _EcosBlock | None = None
    rss: _RssBlock | None = None
    plugins: dict[str, dict[str, Any]] | None = None
```

이렇게 하면 `sources.plugins`는 허용하지만, `sources.rsss` 같은 typo는 계속 실패한다. 또한 `sources.plugins.acme: "x"`처럼 plugin block이 mapping이 아니면 실패한다.

### 4.4 Builder warning

`build_sources()`는 `BUILTIN_SOURCE_SPECS`와 entry point source specs를 합친 뒤 plugin config key를 검사한다.

| 상황 | 처리 |
|---|---|
| `sources.plugins.acme_news`가 있고 `SourceSpec("acme_news", ...)`도 있음 | warning 없음 |
| `sources.plugins.acme_news`가 있는데 plugin이 설치되지 않았거나 load 실패 | warning |
| `sources.plugins.rss`처럼 built-in source id를 사용 | warning |

Warning은 설정을 fail-fast로 막지 않는다. Plugin이 선택 설치일 수 있기 때문이다. 다만 사용자는 typo나 미설치 plugin을 로그에서 볼 수 있다.

### 4.5 Plugin factory 사용 예

```python
from pydantic import BaseModel, ConfigDict
from mimir.core.builder import SourceSpec


class AcmeNewsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str
    symbols: list[str] = []


def build_acme_news(settings, cfg):
    plugin_cfg = cfg.parse_plugin_config("acme_news", AcmeNewsConfig)
    return AcmeNewsSource(base_url=plugin_cfg.base_url, symbols=plugin_cfg.symbols)


ACME_NEWS_SPEC = SourceSpec("acme_news", build_acme_news)
```

Plugin이 설정을 필요로 하지 않으면 helper를 호출하지 않아도 된다.

---

## 5. 실패와 예외 처리

| 상황 | 처리 |
|---|---|
| `sources.plugins`가 생략됨 | `plugin_settings={}` |
| `sources.plugins.acme_news`가 mapping | raw dict로 보존 |
| `sources.plugins.acme_news: "x"` | `ValidationError` |
| `sources.plugins.acme_news.timeout_seconds: "x"` | parser는 통과. plugin의 pydantic model이 검증할 때 실패 |
| plugin factory가 `parse_plugin_config()`에서 실패 | 기존 factory failure처럼 예외가 올라간다 |
| plugin config key와 source spec id가 맞지 않음 | warning |
| built-in id가 `sources.plugins`에 들어옴 | warning |

---

## 6. 테스트 전략

| 테스트 | 고정하는 계약 |
|---|---|
| `test_sources_plugins_namespace_parses_mapping` | `sources.plugins.<id>` mapping이 `SourcesConfig.plugin_settings`에 보존된다. |
| `test_sources_plugins_namespace_rejects_non_mapping_plugin_config` | plugin config block은 mapping이어야 한다. |
| `test_plugin_config_returns_copy_and_empty_default` | 없는 plugin은 `{}`이고 반환 dict mutation이 내부 상태를 바꾸지 않는다. |
| `test_parse_plugin_config_validates_with_pydantic_model` | plugin factory가 pydantic 모델로 자기 설정을 검증할 수 있다. |
| `test_parse_plugin_config_rejects_plugin_schema_drift` | plugin schema가 `extra="forbid"`이면 오타가 실패한다. |
| `test_build_sources_passes_plugin_namespace_to_factory` | plugin `SourceSpec.factory`가 namespaced config를 읽어 source를 만들 수 있다. |
| `test_builder_warns_for_unmatched_plugin_config` | config key는 있지만 matching source spec이 없으면 warning이 남는다. |
| `test_builder_warns_when_plugin_namespace_targets_builtin_source` | built-in id 아래 plugin namespace를 쓰면 warning이 남는다. |

---

## 7. 수용 기준

- [x] `sources.plugins.<source_id>` namespace가 parse된다.
- [x] Plugin config block은 mapping만 허용한다.
- [x] 기존 built-in source typo 검증은 유지된다.
- [x] Plugin factory가 pydantic 모델로 자기 설정을 검증할 수 있다.
- [x] Matching `SourceSpec.id`가 없는 plugin config는 warning을 남긴다.
- [x] Built-in source id가 `sources.plugins`에 있으면 warning을 남긴다.
- [x] README, config reference, extensibility guide, improvement catalog가 새 namespace를 설명한다.
- [x] ruff, mypy, pytest, coverage 80% gate를 통과한다.

---

## 8. 남는 한계

Core는 plugin schema를 자동 발견하지 않는다. 이 결정은 plugin package의 독립성을 지키기 위한 것이다. 더 강한 schema registry가 필요하면 `SourceSpec`에 optional config model을 추가하는 별도 설계가 필요하다.

또한 plugin code는 여전히 Mimir 프로세스 안에서 실행된다. 설정 namespace는 검증과 가독성을 개선하지만 sandbox를 제공하지 않는다.
