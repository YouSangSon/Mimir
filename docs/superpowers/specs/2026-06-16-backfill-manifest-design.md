# Backfill Manifest Recording — 설계

> **스펙 ID**: BF-MANIFEST
> **작성일**: 2026-06-16
> **상태**: ✅ 구현 완료 (`backfill` success/failure manifest recording). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **선행**: [Collector 설계](2026-05-31-collector-design.md) · [개선 백로그](../../IMPROVEMENTS.md) · [발전 카탈로그](../../architecture/improvement-catalog.md)

---

## 1. 한눈에 보기

`collect`는 각 실행 결과를 `data/_manifest/YYYY/MM/DD.jsonl`에 남긴다. 그래서 어떤 소스가 실패했는지, 몇 건을 가져오고 저장했는지 나중에 추적할 수 있다.

`backfill`은 같은 저장소와 같은 소스를 쓰지만 manifest를 남기지 않는다. 과거 가격이나 거시 데이터를 한 번에 적재하다 실패하면, 저장소에는 일부 데이터만 남고 실행 로그에는 아무 흔적이 없다.

이 변경은 `backfill`도 manifest에 한 줄을 남기게 한다. 성공 시에는 `fetched`, `stored`, `invalid`를 기록한다. 실패 시에는 실패 manifest를 먼저 기록한 뒤 기존처럼 예외를 다시 던져 호출자가 비정상 종료를 볼 수 있게 한다.

---

## 2. 문제

### 2.1 백필은 운영상 더 위험하지만 실행 로그가 없다

백필(backfill)은 과거 기간을 한 번에 다시 가져오는 작업이다. 보통 정기 수집보다 더 많은 레코드를 만들고, 실행 시간도 길다.

현재 `mimir.backfill.run_backfill()`은 다음 동작만 한다.

1. 소스를 하나 고른다.
2. `FetchContext.backfill_since`를 채워 데이터를 가져온다.
3. 레코드별 `NormalizationError`는 건너뛴다.
4. 저장된 건수만 반환한다.

이 흐름은 성공과 실패를 manifest에 쓰지 않는다. README는 `data/_manifest`를 실행 로그로 설명하고, 백로그도 "매니페스트는 후속"이라고 남겨두었다. 현재 동작은 이 약속과 맞지 않는다.

### 2.2 실패를 삼키면 안 된다

`collect`는 소스별 격리를 제공한다. 여러 소스 중 하나가 실패해도 다른 소스를 계속 처리하고, 요약 결과로 실패를 신호한다.

`backfill`은 단일 소스 작업이다. 실패를 `ok=False`로 기록하고 정상 반환하면 호출자는 성공으로 오해할 수 있다. 따라서 실패 manifest를 남기되 예외는 다시 던진다.

---

## 3. 목표와 비목표

### 목표

- `backfill` 성공 실행을 manifest에 기록한다.
- 성공 manifest에는 `source`, `ok`, `fetched`, `stored`, `invalid`가 들어간다.
- 레코드별 정규화 실패는 기존처럼 건너뛰고 `invalid`에 반영한다.
- upstream fetch, normalize, store 단계의 예외는 실패 manifest를 남긴 뒤 다시 던진다.
- `run_backfill()`의 반환값은 기존처럼 저장된 건수(`stored`)로 유지한다.
- manifest cadence는 대상 소스의 `source.meta.cadence`를 사용한다.

### 비목표

- backfill CLI의 출력 형식을 바꾸지 않는다.
- backfill 실패를 정상 반환으로 바꾸지 않는다.
- 여러 source를 한 번에 backfill하는 기능을 추가하지 않는다.
- manifest schema를 확장하지 않는다. 기존 `SourceResult`와 `RunRecord`를 그대로 쓴다.
- 백필 실행 시간이나 duration 필드를 새로 기록하지 않는다.

---

## 4. 설계

### 4.1 성공 경로

`run_backfill()`은 `JsonlStore`와 함께 `Manifest(root=data_root)`를 만든다.

```python
store = JsonlStore(root=data_root)
manifest = Manifest(root=data_root)
```

fetch loop는 raw 레코드 수를 센다. 정규화에 성공한 레코드는 저장 목록에 넣고, `NormalizationError`는 `invalid`만 증가시킨다.

```python
fetched = 0
invalid = 0
records: list[Record] = []

for raw in source.fetch(ctx):
    fetched += 1
    try:
        records.append(normalize(raw, source.meta, captured_at=now))
    except NormalizationError:
        invalid += 1
```

저장이 끝나면 기존 manifest schema로 한 줄을 기록한다.

```python
stored = store.append(records)
manifest.write(
    now=now,
    cadence=source.meta.cadence,
    results=[
        SourceResult(
            source=source.meta.id,
            ok=True,
            fetched=fetched,
            stored=stored,
            invalid=invalid,
        )
    ],
)
return stored
```

`stored`는 유효 레코드 수가 아니라 이번 실행으로 저장 파일에 반영된 건수다. append-only 데이터셋은 이미 같은 key가 있으면 dedup 때문에 `fetched > 0`, `stored = 0`이 될 수 있다. `macro`처럼 공식 개정값을 last-write-wins로 받는 데이터셋은 같은 key라도 payload가 바뀌면 `stored = 1`로 기록된다.

현재 `run_backfill()`은 저장 시 `append_overwrite_enabled(source.meta.dataset)`를 사용한다. 따라서 BF-MANIFEST의 `stored`는 source dataset별 저장 정책과 같은 의미를 갖는다. `macro` source는 `JsonlStore.append(overwrite=True)` 경로를 통해 개정 payload를 반영하고, `prices`/`filings`/`news`는 first-write-wins로 dedup된다.

### 4.2 실패 경로

fetch, normalize, store 중 하나가 실패하면 `SourceResult.ok=False`를 기록한다.

```python
except Exception as exc:
    manifest.write(
        now=now,
        cadence=source.meta.cadence,
        results=[
            SourceResult(
                source=source.meta.id,
                ok=False,
                fetched=fetched,
                invalid=invalid,
                error=str(exc),
            )
        ],
    )
    raise
```

예외는 다시 던진다. 그래야 기존 backfill 호출자는 실패를 계속 비정상 종료로 본다.

실패 manifest 기록 자체가 실패하면, `backfill`은 경고 로그만 남기고 원래 fetch, normalize, store 예외를 다시 던진다. 실행 로그 쓰기 실패가 원래 원인을 가리면 운영자가 잘못된 문제를 보게 되기 때문이다.

현재 구현은 runtime failure와 BF-PREFLIGHT preflight failure 모두 작은 helper인 `_write_failure_manifest()`로 같은 `SourceResult` shape를 쓴다. Manifest schema는 여전히 `SourceResult`와 `RunRecord`를 그대로 사용하며, `mode`, `phase`, `duration` 같은 필드는 추가하지 않았다.

### 4.3 unknown source와 registered-unavailable source의 현재 경계

BF-MANIFEST 당시에는 `source_id`가 build 결과에 없으면 `SystemExit("unknown or unavailable source: ...")`만 올리고 manifest를 쓰지 않았다. 후속 BF-PREFLIGHT 구현 후 현재 경계는 더 좁다.

현재 구현에서 registered-unavailable source는 BF-PREFLIGHT가 `ok=false` manifest로 기록한다. 예를 들어 `stooq`이 등록되어 있지만 `STOOQ_API_KEY`가 없거나, `pykrx`가 등록되어 있지만 optional package가 없으면 zero-count failure manifest를 남긴 뒤 기존 `SystemExit("unknown or unavailable source: <id>")`를 유지한다.

반대로 진짜 unknown source id는 여전히 manifest 없이 argument error로 끝난다. 이 경우에는 registered `SourceSpec.meta`가 없어 `RunRecord.cadence`에 넣을 신뢰 가능한 cadence가 없기 때문이다.

---

## 5. 테스트 전략

| 테스트 | 고정하는 계약 |
|---|---|
| `test_backfill_stooq_loads_history` 확장 | 성공 backfill이 `_manifest`를 만들고 `fetched=2`, `stored=2`, `invalid=0`을 기록한다. |
| `test_backfill_records_invalid_count_in_manifest` | 레코드 하나가 정규화 실패해도 나머지는 저장되고 manifest에 `invalid=1`이 남는다. |
| `test_backfill_records_failure_manifest_before_reraising` | source fetch 실패가 manifest `ok=false`로 남고 예외는 다시 올라간다. |
| `test_backfill_preserves_original_error_when_failure_manifest_write_fails` | 실패 manifest 기록까지 실패해도 원래 normalize 예외가 호출자에게 올라간다. |

---

## 6. 수용 기준

- [x] 성공한 backfill 실행이 `data/_manifest/YYYY/MM/DD.jsonl`에 기록된다.
- [x] manifest cadence는 source metadata에서 온다.
- [x] `fetched`, `stored`, `invalid`가 성공 manifest에 정확히 기록된다.
- [x] backfill fetch 실패는 `ok=false` manifest를 기록한 뒤 예외를 다시 던진다.
- [x] 실패 manifest 기록이 실패해도 원래 backfill 예외를 보존한다.
- [x] `run_backfill()` 반환값은 기존처럼 저장된 건수다.
- [x] 개선 백로그, 발전 카탈로그, README 3종이 backfill manifest 동작을 설명한다.
- [x] 최신 전체 검증 상태는 README 테스트 배지와 docs health guard가 추적한다.

---

## 7. 남는 한계

`backfill`은 여전히 단일 소스 작업이다. 여러 소스를 한 번에 백필하는 orchestration은 별도 설계가 필요하다.

또한 `RunRecord`에는 `mode` 필드가 없다. 따라서 manifest만 보면 collect와 backfill을 cadence로만 구분한다. 이번 증분은 schema 확장을 피하고, 기존 dashboard/status 소비자와의 호환성을 우선한다.
