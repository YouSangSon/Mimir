# Macro Revision Storage Policy — 설계

> **스펙 ID**: MACRO-LWW
> **작성일**: 2026-06-16
> **상태**: ✅ 구현 완료 (`macro` source last-write-wins + source dataset별 저장 정책). 최신 검증은 README 테스트 배지와 docs health guard가 추적한다.
> **선행**: [Backfill Manifest Recording](2026-06-16-backfill-manifest-design.md) · [R1b News Captured Window](2026-06-16-news-captured-window-design.md) · [개선 백로그](../../IMPROVEMENTS.md)

---

## 1. 한눈에 보기

FRED와 ECOS 같은 공식 거시 데이터는 같은 관측일의 값이 나중에 개정될 수 있다. 현재 저장소는 같은 `idempotency_key`를 다시 받으면 첫 값을 유지한다.

그래서 2024년 1월 2일 금리 값이 처음에는 `4.00`으로 저장되고, 다음 실행에서 `4.25`로 개정되어도 Mimir는 계속 `4.00`을 읽는다. `MacroRegimeSignal`은 저장된 값을 그대로 쓰므로, 공식 기관의 최신 개정값을 반영하지 못한다.

이 변경은 source dataset별 저장 정책을 분리한다. `macro`는 같은 key를 다시 받으면 마지막 값을 남긴다. `prices`, `filings`, `news`는 기존처럼 첫 값을 유지한다.

---

## 2. 문제

### 2.1 macro observation은 불변 raw event가 아니다

가격, 공시, 뉴스는 보통 원천 이벤트 자체가 하나의 관측 기록이다. 같은 key를 다시 받았을 때 첫 값을 유지하면 중복 수집을 막을 수 있다.

FRED와 ECOS의 거시 지표는 다르다. 같은 시리즈와 같은 기간의 관측값이 공식 기관에 의해 개정될 수 있다. 이때 `idempotency_key`는 의도적으로 바뀌지 않는다.

FRED key는 `fred:{series_id}:{day}`다. ECOS key는 `ecos:{stat_code}:{item_code}:{time}`이다. 이 key는 "이 관측점은 같은 관측점"이라는 뜻이지 "payload가 영원히 같아야 한다"는 뜻이 아니다.

### 2.2 현재 collector와 backfill은 모두 first-write-wins다

`JsonlStore.append()`는 기본값으로 `overwrite=False`를 쓴다. 이 기본 동작은 기존 key가 있으면 새 레코드를 건너뛴다.

`Orchestrator._run_one()`과 `run_backfill()`은 이 기본값을 그대로 호출한다. 그래서 macro source가 개정값을 가져와도 저장 파일은 바뀌지 않는다.

### 2.3 전역 overwrite는 위험하다

모든 source에 `overwrite=True`를 적용하면 뉴스, 공시, 가격 데이터의 replay 의미가 바뀐다. 특히 뉴스는 captured window 정책과 결합되어 "처음 수집된 사실"이 중요하다.

따라서 저장 정책은 source dataset 단위로 명시해야 한다.

---

## 3. 목표와 비목표

### 목표

- `Dataset.MACRO` collection과 backfill은 같은 key의 최신 레코드를 남긴다.
- `Dataset.PRICES`, `Dataset.FILINGS`, `Dataset.NEWS`는 기존 first-write-wins 의미를 유지한다.
- 저장 정책 판단을 한 helper에 모아 orchestrator와 backfill이 같은 규칙을 쓴다.
- `append(overwrite=True)`는 새 key뿐 아니라 교체된 key도 저장 건수로 센다.
- 개선 백로그와 확장성 문서가 source dataset별 저장 정책을 설명한다.

### 비목표

- JSONL 파티션 구조를 바꾸지 않는다.
- vendor deletion을 처리하지 않는다. 즉, 이번 변경은 "같은 key의 값 개정"만 다룬다.
- macro observation의 revision history를 별도 보존하지 않는다.
- prices, filings, news의 dedup 정책을 바꾸지 않는다.
- manifest schema를 확장하지 않는다.

---

## 4. 설계

### 4.1 source dataset별 append overwrite 정책

`mimir/storage/policy.py`에 dataset 저장 정책을 둔다.

```python
OVERWRITE_ON_APPEND_DATASETS = frozenset({Dataset.MACRO})

def append_overwrite_enabled(dataset: Dataset) -> bool:
    return dataset in OVERWRITE_ON_APPEND_DATASETS
```

이 helper는 "source 수집 결과를 append할 때 같은 key가 다시 오면 교체할지"만 판단한다. 재생성 데이터셋인 `insights`, `historical`, `evaluation`은 계속 `replace_partition()`을 쓴다.

### 4.2 orchestrator와 backfill은 같은 정책을 쓴다

정기 수집 경로는 source metadata의 dataset을 보고 overwrite 여부를 정한다.

```python
stored = self._store.append(
    records,
    overwrite=append_overwrite_enabled(source.meta.dataset),
)
```

backfill도 같은 helper를 호출한다.

```python
stored = store.append(
    records,
    overwrite=append_overwrite_enabled(source.meta.dataset),
)
```

이렇게 해야 정기 수집과 수동 과거 적재가 같은 저장 의미를 갖는다.

### 4.3 overwrite 저장 건수는 변경된 레코드를 센다

기존 `_append_overwrite()`는 새 key 수만 반환했다. 이 의미에서는 macro 값이 `4.00`에서 `4.25`로 바뀌어 파일이 갱신되어도 `stored=0`이 된다.

이번 변경은 `overwrite=True` 경로에서 새 key와 교체된 key를 모두 센다. `stored`는 "이번 실행으로 파일에 반영된 레코드 수"가 된다.

기본 append-only 경로는 그대로다. 같은 key를 다시 받으면 저장하지 않고 `stored=0`을 유지한다.

현재 구현에서 정책은 `mimir/storage/policy.py`의 `OVERWRITE_ON_APPEND_DATASETS`와 `append_overwrite_enabled(dataset)`에 있다. 현재 overwrite append 대상은 `Dataset.MACRO`뿐이며, source 수집과 backfill은 모두 `append_overwrite_enabled(source.meta.dataset)`로 같은 규칙을 쓴다. 실제 병합은 `JsonlStore.append(overwrite=True)`의 `_append_overwrite()` 경로에서 수행되고, `_same_stored_record()`가 `captured_at`만 다른 replay를 no-op으로 판정해 최초 capture time을 보존한다.

---

## 5. 실패와 예외 처리

| 상황 | 처리 |
|---|---|
| FRED가 같은 key에 새 값을 반환 | 기존 macro 레코드를 새 payload로 교체 |
| ECOS가 같은 key에 새 값을 반환 | 기존 macro 레코드를 새 payload로 교체 |
| Stooq 가격이 같은 key에 다른 close를 반환 | 기존 가격 레코드를 유지 |
| RSS 뉴스가 같은 key에 다른 title을 반환 | 기존 뉴스 레코드를 유지 |
| macro source가 현재 window에서 일부 관측값을 반환하지 않음 | 누락된 기존 관측값은 삭제하지 않음 |
| overwrite 경로에서 동일한 레코드가 다시 들어옴 | 같은 값이면 저장 건수는 증가하지 않음 |
| overwrite 경로에서 `captured_at`만 달라짐 | 새 실행 시간을 반영하지 않고 기존 레코드를 보존 |

---

## 6. 테스트 전략

| 테스트 | 고정하는 계약 |
|---|---|
| `test_macro_sources_overwrite_existing_observations` | orchestrator가 macro source의 같은 key 개정값을 마지막 값으로 저장한다. |
| `test_non_macro_sources_keep_first_write_wins` | orchestrator가 prices 같은 비거시 source에는 기존 dedup 의미를 유지한다. |
| `test_backfill_fred_revisions_overwrite_existing_observation` | backfill FRED 재실행이 같은 관측일의 개정 payload를 저장한다. |
| `test_backfill_stooq_keeps_first_write_wins_for_prices` | backfill Stooq 재실행은 기존 가격 payload를 교체하지 않는다. |
| `test_append_overwrite_counts_replaced_records` | overwrite 경로는 교체된 key를 저장 건수로 센다. |
| `test_append_overwrite_counts_repeated_batch_key_once` | 한 배치에 같은 key가 반복돼도 최종 변경 key는 한 번만 센다. |
| `test_append_overwrite_noop_does_not_rewrite_partition` | 변경이 없는 replay는 파티션 파일을 다시 쓰지 않는다. |
| `test_append_overwrite_enabled_only_for_macro_sources` | 정책 helper가 macro만 overwrite 대상으로 분류한다. |

---

## 7. 수용 기준

- [x] `Dataset.MACRO` source는 orchestrator에서 last-write-wins로 저장된다.
- [x] `Dataset.MACRO` source는 backfill에서 last-write-wins로 저장된다.
- [x] `prices`, `filings`, `news`는 source 수집과 backfill에서 first-write-wins를 유지한다.
- [x] 저장 정책은 orchestrator와 backfill에 중복된 조건문으로 흩어지지 않는다.
- [x] overwrite 저장 건수는 새 key와 교체된 key를 반영한다.
- [x] README 3종과 확장성 문서가 macro revision 정책을 설명한다.
- [x] ruff, mypy, pytest, coverage 80% gate를 통과한다.

---

## 8. 남는 한계

last-write-wins는 최신 값만 남긴다. 공식 기관이 과거 값을 언제, 어떤 이유로 고쳤는지 추적하려면 revision history 데이터셋이 별도로 필요하다.

또한 이번 변경은 삭제를 처리하지 않는다. vendor가 관측값을 삭제하거나 시리즈 정의를 바꾸면, 기존 저장 파일에 남은 레코드는 그대로 유지된다. 이 문제는 `replace_partition()`이 아니라 source별 deletion policy가 필요한 별도 설계다.
