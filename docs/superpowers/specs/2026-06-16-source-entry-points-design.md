# A3b. Source Plugin Entry Points — 설계

> **스펙 ID**: A3b
> **작성일**: 2026-06-16
> **상태**: ✅ 구현 완료 (`mimir.sources` entry point + plugin `SourceSpec` loader). 396 테스트 · ruff · mypy · coverage gate 클린.
> **선행**: [A3 선언적 소스 등록](2026-06-16-declarative-source-registration-design.md) · [확장성 카탈로그](../../architecture/improvement-catalog.md)

---

## 1. 한눈에 보기

A3는 내장 source 생성을 `SourceSpec` 테이블로 정리했다. 이 구조 덕분에 새 source의 생성 조건, secret gate, optional package gate가 한 곳에 모인다.

하지만 아직 외부 Python package가 Mimir에 source를 주입할 방법은 없다. 사용자가 사내 feed나 실험용 adapter를 배포하려면 여전히 Mimir repo를 fork해서 `BUILTIN_SOURCE_SPECS`를 고쳐야 한다.

A3b는 Python package entry point를 source 확장 seam으로 추가한다. Mimir는 시작 시 `mimir.sources` group을 읽고, 각 entry point가 제공하는 `SourceSpec`을 built-in spec 뒤에 붙인다. built-in 동작과 순서는 그대로 유지한다.

---

## 2. 문제

### 2.1 built-in 등록만으로는 외부 확장이 막힌다

현재 새 source를 추가하려면 `mimir/sources/<source>.py`를 만들고 `mimir/core/builder.py`를 수정해야 한다. 이 방식은 프로젝트 안에서 작업할 때는 단순하지만, 외부 패키지에는 맞지 않는다.

예를 들어 사용자가 내부 전용 RSS, 회사 데이터 lake, 또는 유료 vendor adapter를 별도 package로 관리하려면 Mimir 본문 코드를 수정하지 않고도 source를 주입할 수 있어야 한다.

### 2.2 plugin 실패가 core source를 깨면 안 된다

외부 plugin은 Mimir가 통제하지 않는 코드다. plugin import가 실패하거나 잘못된 객체를 반환해도 SEC EDGAR, RSS 같은 built-in source가 같이 죽으면 안 된다.

반대로 source id 충돌은 조용히 넘어가면 안 된다. built-in `rss`와 plugin `rss`가 같은 id를 쓰면 registry와 manifest가 같은 source로 오해한다.

---

## 3. 목표와 비목표

### 목표

- `mimir.sources` entry-point group에서 외부 `SourceSpec`을 읽는다.
- entry point는 `SourceSpec` 하나 또는 `Sequence[SourceSpec]`를 직접 로드할 수 있다.
- 단일 `SourceSpec` entry point는 entry point 이름과 `SourceSpec.id`를 일치시킨다.
- built-in source 순서와 기본 동작을 유지한다.
- plugin load 오류와 잘못된 반환값은 warning으로 남기고 해당 plugin만 skip한다.
- built-in과 plugin source id 중복은 기존 duplicate-id 검증으로 `ValueError`를 낸다.
- 문서에 plugin package 예시와 failure 정책을 남긴다.

### 비목표

- plugin별 YAML 설정 스키마를 추가하지 않는다.
- plugin source를 sandbox하거나 권한 격리하지 않는다.
- doctor 기대 데이터셋을 plugin에서 자동 파생하지 않는다.
- 외부 package를 실제로 새로 배포하지 않는다.
- source registry의 cadence/GRAY 정책은 바꾸지 않는다.

---

## 4. 설계

### 4.1 entry-point group

외부 package는 `pyproject.toml`에 아래 group을 선언한다.

```toml
[project.entry-points."mimir.sources"]
acme_feed = "acme_mimir.sources:ACME_FEED_SPEC"
```

entry point는 `SourceSpec` 객체 하나를 직접 로드한다. 이때 entry point 이름과 `SourceSpec.id`는 같아야 한다.

```python
from mimir.core.builder import SourceSpec


ACME_FEED_SPEC = SourceSpec("acme_feed", lambda settings, cfg: AcmeSource())
```

한 package가 여러 source를 묶어 제공할 수도 있다. 이때 entry point 이름은 provider 이름이고, 값은 `tuple[SourceSpec, ...]`이다.

```toml
[project.entry-points."mimir.sources"]
acme = "acme_mimir.sources:SOURCE_SPECS"
```

```python
SOURCE_SPECS = (
    SourceSpec("acme_news", lambda settings, cfg: AcmeNewsSource()),
    SourceSpec("acme_macro", lambda settings, cfg: AcmeMacroSource()),
)
```

### 4.2 builder 흐름

`build_sources(settings, config)`는 아래 순서로 동작한다.

1. 기존 SEC User-Agent warning을 유지한다.
2. `SourcesConfig()` 기본값을 만든다.
3. `BUILTIN_SOURCE_SPECS`를 먼저 둔다.
4. `_load_entry_point_source_specs()`가 `mimir.sources` plugin spec을 읽는다.
5. built-in spec과 plugin spec을 합쳐 `_build_sources_from_specs()`에 넘긴다.
6. `_validate_unique_source_ids()`가 전체 spec id 중복을 잡는다.

이 순서 때문에 built-in source의 반환 순서는 그대로 유지되고, plugin source는 뒤에 붙는다.

### 4.3 실패 정책

| 상황 | 처리 |
|---|---|
| entry point load가 예외를 던짐 | warning 후 해당 plugin skip |
| 단일 `SourceSpec.id`가 entry point 이름과 다름 | `ValueError` |
| 반환값이 `SourceSpec`도 sequence도 아님 | `ValueError` |
| sequence 안에 `SourceSpec`이 아닌 값이 있음 | `ValueError` |
| plugin source id가 built-in 또는 다른 plugin과 중복됨 | `ValueError` |
| plugin factory가 source를 만들었지만 `source.meta.id`가 spec id와 다름 | 기존 `ValueError` |

---

## 5. 테스트 전략

| 테스트 | 고정하는 계약 |
|---|---|
| `test_load_entry_point_source_specs_accepts_single_spec` | entry point가 `SourceSpec` 하나를 로드할 수 있다 |
| `test_load_entry_point_source_specs_accepts_sequence` | entry point가 여러 `SourceSpec`을 로드할 수 있다 |
| `test_entry_point_source_spec_id_must_match_entry_point_name` | 단일 spec entry point 이름과 source id가 어긋나면 실패한다 |
| `test_build_sources_includes_entry_point_sources_after_builtins` | `build_sources()`가 plugin source를 built-in 뒤에 붙인다 |
| `test_broken_entry_point_source_spec_is_skipped_and_logged` | broken plugin이 built-in source를 깨지 않는다 |
| `test_entry_point_wrong_object_type_raises_value_error` | 잘못 선언된 plugin은 조용히 무시하지 않는다 |
| `test_entry_point_source_id_conflict_raises_value_error` | source id 충돌은 조용히 무시하지 않는다 |

---

## 6. 수용 기준

- [x] `mimir.sources` entry-point group을 읽는 loader가 있다.
- [x] built-in source 순서와 기본 source set이 유지된다.
- [x] plugin source가 `build_sources()` 결과에 추가된다.
- [x] broken plugin은 warning 후 skip된다.
- [x] source id 중복은 `ValueError`로 실패한다.
- [x] docs가 외부 source plugin 작성법과 실패 정책을 설명한다.
- [x] ruff, mypy, pytest, coverage 80% gate가 통과한다.

---

## 7. 남는 한계

entry point는 신뢰된 Python package를 로드한다. Mimir는 plugin 코드를 sandbox하지 않는다. 사용자는 plugin package를 설치하기 전에 배포 주체와 secret 사용 방식을 검토해야 한다.

Plugin별 설정 스키마도 아직 없다. 첫 버전은 `Settings`와 `SourcesConfig`를 그대로 받는 `SourceSpec.factory`를 재사용한다. plugin이 복잡한 설정을 필요로 하면 별도 설정 namespace를 설계해야 한다.
