# Backfill Preflight Failure Manifest — 설계

> **스펙 ID**: BF-PREFLIGHT
> **작성일**: 2026-06-18
> **상태**: ✅ 구현 완료 (`backfill` registered-unavailable preflight failure manifest). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **선행**: [Backfill Manifest Recording](2026-06-16-backfill-manifest-design.md) · [개선 백로그](../../IMPROVEMENTS.md) · [발전 카탈로그](../../architecture/improvement-catalog.md)

---

## 1. 한눈에 보기

`backfill`은 fetch, normalize, store 단계에서 실패하면 `ok=false` manifest를 남긴다.

하지만 source를 고르기 전에 실패하면 아직 manifest를 쓰지 못한다. 대표 사례는 사용자가 등록된 source id를 지정했지만 API key나 선택 패키지가 없어 `build_sources()`가 그 source를 건너뛰는 경우다.

이 변경은 registered source가 preflight 단계에서 unavailable인 경우에도 `ok=false` manifest를 남긴다. 진짜 unknown source id는 source cadence를 알 수 없으므로 argument error로 유지하고 manifest를 쓰지 않는다.

---

## 2. 문제

### 2.1 README의 운영 계약보다 실제 기록 범위가 좁다

README는 `backfill` 실패가 `ok=false` manifest를 먼저 남긴 뒤 비정상 종료한다고 설명한다. 현재 구현은 fetch loop가 시작된 뒤에는 이 계약을 지킨다.

그러나 `run_backfill()`은 source lookup을 먼저 수행한다.

```python
sources = {s.meta.id: s for s in build_sources(settings, config)}
if source_id not in sources:
    raise SystemExit(f"unknown or unavailable source: {source_id}")
manifest = Manifest(root=data_root)
```

`stooq`, `fred`, `dart`, `ecos`처럼 secret이 필요한 source는 key가 없으면 `build_sources()`에서 제외된다. 이때 사용자가 해당 source를 명시적으로 backfill하면 `SystemExit`만 나고 manifest는 남지 않는다.

### 2.2 unknown source와 unavailable source는 다르다

두 실패는 사용자에게 비슷하게 보이지만 manifest 관점에서는 다르다.

| 실패 | 예시 | source metadata | manifest 가능 여부 |
| ---- | ---- | --------------- | ------------------ |
| registered but unavailable | `stooq`인데 `STOOQ_API_KEY` 없음 | built-in `SourceSpec`에서 알 수 있음 | 가능 |
| unknown id | `not_a_source` | id, cadence, dataset을 알 수 없음 | 불가능 |

기존 manifest schema의 `RunRecord.cadence`는 필수 `Cadence`다. 진짜 unknown id에 임의 cadence를 넣으면 실행 로그가 거짓 정보를 갖게 된다.

---

## 3. 목표와 비목표

### 목표

- registered source가 secret/package gate 때문에 build 전에 제외되어도 backfill manifest에 `ok=false`를 기록한다.
- preflight 실패 manifest는 기존 `RunRecord`와 `SourceResult` schema를 그대로 사용한다.
- built-in source는 source class의 static `SourceMeta`를 `SourceSpec`에 노출해 cadence를 알 수 있게 한다.
- plugin source도 원하면 `SourceSpec(meta=...)`로 preflight manifest를 지원할 수 있게 한다.
- 진짜 unknown source id는 기존처럼 `SystemExit("unknown or unavailable source: ...")`로 끝나고 manifest를 쓰지 않는다.

### 비목표

- manifest schema에 `mode`, `phase`, `duration` 필드를 추가하지 않는다.
- unknown source id에 임의 cadence를 넣지 않는다.
- 여러 source를 한 번에 backfill하지 않는다.
- `collect`의 secret-gated skipped source manifest 정책은 이번 증분에서 바꾸지 않는다.
- API key 값을 manifest, log, 문서에 노출하지 않는다.

---

## 4. 설계

### 4.1 SourceSpec에 static metadata를 선택적으로 둔다

`SourceSpec`에 `meta: SourceMeta | None = None` 필드를 추가한다. 새 필드는 dataclass 끝에 두어 기존 plugin이 `SourceSpec(id, factory)` 형태로 만들던 코드를 깨지 않는다.

Built-in source specs는 각 source class의 static metadata를 연결한다.

| SourceSpec id | meta |
| ------------- | ---- |
| `sec_edgar` | `SecEdgarSource.meta` |
| `rss` | `RssSource.meta` |
| `stooq` | `StooqSource.meta` |
| `dart` | `DartSource.meta` |
| `fred` | `FredSource.meta` |
| `ecos` | `EcosSource.meta` |
| `pykrx` | `PykrxSource.meta` |

### 4.2 source spec 목록을 한 번만 로드한다

`build_sources()`는 지금 built-in spec과 entry point spec을 내부에서 합친다. `backfill`은 source build 결과와 preflight metadata를 둘 다 봐야 하므로 spec 목록이 필요하다.

새 helper를 둔다.

```python
def load_source_specs(
    group: str = SOURCE_ENTRY_POINT_GROUP,
) -> tuple[SourceSpec, ...]:
    return (*BUILTIN_SOURCE_SPECS, *_load_entry_point_source_specs(group))
```

`build_sources()`는 선택 인자 `specs`를 받는다.

```python
def build_sources(
    settings: Settings,
    config: SourcesConfig | None = None,
    *,
    specs: Sequence[SourceSpec] | None = None,
) -> list[Source]:
    selected_specs = tuple(specs) if specs is not None else load_source_specs()
    return _build_sources_from_specs(settings, cfg, selected_specs)
```

기존 caller는 인자를 추가하지 않아도 같은 동작을 한다.

### 4.3 backfill preflight failure를 manifest에 쓴다

`run_backfill()`은 `Manifest`를 source lookup 전에 만든다. source build에는 같은 spec 목록을 넘긴다.

```python
manifest = Manifest(root=data_root)
specs = load_source_specs()
built_sources = build_sources(settings, runtime.source_config, specs=specs)
sources = {s.meta.id: s for s in built_sources}
```

현재 호출 형태는 `load_source_specs()`로 spec 목록을 가져온 뒤 `build_sources(settings, runtime.source_config, specs=specs)`에 같은 목록을 넘기는 구조다.

source id가 build 결과에 없으면 `spec.meta`를 찾는다.

- meta가 있으면 `SourceResult(source=source_id, ok=False, error=<비밀값 없는 unavailable reason>)`를 기록한다.
- cadence는 `spec.meta.cadence`를 쓴다.
- `fetched`, `stored`, `invalid`는 0을 유지한다.
- manifest write가 실패하면 warning만 남기고 원래 `SystemExit`를 다시 올린다.
- meta가 없으면 기존처럼 manifest 없이 `SystemExit`만 올린다.

현재 구현은 `_source_spec_for_id()`로 requested id의 `SourceSpec`를 찾고, `_preflight_unavailable_error()`로 비밀값 없는 원인을 만든 뒤 `_write_failure_manifest()`를 호출한다. 이 경로는 `SourceSpec(meta=...)`가 있는 registered source에서만 manifest를 쓴다. `SourceSpec.meta`가 없는 plugin이나 진짜 unknown source id는 신뢰 가능한 cadence가 없으므로 manifest 없이 argument error로 남는다.

### 4.4 실패 기록 helper를 공유한다

runtime failure와 preflight failure가 같은 schema를 쓰도록 작은 helper를 둔다.

```python
def _write_failure_manifest(
    manifest: Manifest,
    *,
    now: datetime,
    cadence: Cadence,
    source_id: str,
    fetched: int,
    invalid: int,
    error: str,
) -> None:
    manifest.write(
        now=now,
        cadence=cadence,
        results=[
            SourceResult(
                source=source_id,
                ok=False,
                fetched=fetched,
                invalid=invalid,
                error=error,
            )
        ],
    )
```

호출부는 이 helper를 `try/except Exception`으로 감싼다. manifest write 실패가 원래 실패 원인을 가리지 않아야 하기 때문이다.

### 4.5 preflight error는 원인을 담되 secret 값은 담지 않는다

사용자-facing `SystemExit` 문구는 기존 호환성을 위해 `unknown or unavailable source: <id>`로 유지한다. Manifest의 `error` 필드는 운영자가 원인을 찾을 수 있도록 secret/package gate 이유를 담는다.

| gate | manifest error |
| ---- | -------------- |
| missing secret | `STOOQ_API_KEY is not set` |
| missing optional module | `package not installed (pip install -e '.[kr]')` |
| registered source but no specific reason | `unknown or unavailable source: <id>` |

---

## 5. 테스트 전략

| 테스트 | 고정하는 계약 |
| ------ | ------------- |
| `test_backfill_records_unavailable_registered_source_manifest_before_system_exit` | secret이 없는 registered source backfill이 `ok=false` manifest를 쓰고 `SystemExit`를 유지한다. |
| `test_backfill_records_missing_optional_package_manifest_before_system_exit` | 선택 패키지가 없어 제외된 registered source도 `ok=false` manifest를 쓴다. |
| `test_backfill_unknown_source_remains_argument_error_without_manifest` | unknown source id는 cadence를 알 수 없어 manifest를 쓰지 않는다. |
| `test_builtin_source_specs_expose_static_metadata_for_preflight_manifest` | built-in `SourceSpec`가 preflight manifest에 필요한 `SourceMeta`를 가진다. |

RED 단계에서는 첫 테스트가 실패해야 한다. 현재 구현은 source lookup 전에 manifest를 만들지 않으므로 `_manifest`가 없다.

---

## 6. 수용 기준

- [x] `run_backfill(source_id="stooq", env={})`는 `SystemExit("unknown or unavailable source: stooq")`를 유지한다.
- [x] 같은 실행은 `data/_manifest/YYYY/MM/DD.jsonl`에 `source="stooq"`, `ok=false`, `fetched=0`, `stored=0`, `invalid=0`, `error="STOOQ_API_KEY is not set"`을 기록한다.
- [x] 선택 패키지가 없어 제외된 `pykrx` backfill은 `ok=false` manifest에 package hint를 기록한다.
- [x] preflight failure manifest cadence는 built-in source metadata에서 온다.
- [x] unknown source id는 manifest를 쓰지 않는다.
- [x] runtime fetch/normalize/store failure manifest 동작은 바뀌지 않는다.
- [x] 기존 plugin `SourceSpec(id, factory)` 생성 방식은 계속 동작한다.
- [x] README 3종과 개선 문서가 unknown/unavailable boundary를 설명한다.
- [x] ruff, mypy, pytest, coverage gate, diff-check가 통과한다.

---

## 7. 남는 한계

plugin source가 `SourceSpec(meta=...)`를 제공하지 않으면 preflight failure manifest를 쓸 수 없다. 이 경우에는 기존처럼 `SystemExit`만 남는다. 임의 cadence를 넣는 것보다 이 제한을 명시하는 편이 manifest 신뢰성을 지킨다.

이 제한은 현재 구현에서도 유지된다. 즉, unknown source id와 `SourceSpec(meta=...)`가 없는 plugin unavailable은 manifest 없이 argument error로 남는다.
