# Captured-date persistent index — 설계문서 (보류 항목, 미구현)

> **상태**: 설계만 — 구현하지 않음 (catalog §6 C2 보류 항목의 엄밀한 설계 + unblock 기준)
> **작성**: 2026-06-19
> **선행**: R1b(captured window), C2a-CAPTURED-NEWS-CACHE(in-memory index) · [개선 카탈로그 §6](../../architecture/improvement-catalog.md)
> **대상 독자**: NEWS 데이터가 커져 이 보류 항목을 풀기로 결정할 때 구현하는 개발자

---

## 0. 이 문서의 위치

이 문서는 **코드를 지르지 않는다.** catalog §0 규율상 "측정이 필요한 신규"는 측정 전 구현이 YAGNI다. captured-date persistent index는 "데이터가 수년 누적되고 cache rebuild 자체가 병목이라는 *측정*이 나온 뒤" 설계하도록 보류됐다(C2). 이 문서는 그 한 줄 보류 사유를 "구현 준비된 설계 + 측정 기반 unblock 기준"으로 승격한다.

---

## 1. 한눈에 보기

뉴스 분석 시그널(`news_volume`, opt-in `llm_sentiment`)은 발행일(`ts`)이 아니라 수집일(`captured_at`) 기준 윈도우로 today/baseline을 읽는다(R1b). JSONL 파티션은 `ts.date()` 기준이라 `captured_at` 윈도우에 파티션 프루닝을 쓸 수 없다 — late-captured 기사를 놓치기 때문. 그래서 C2a는 `DataReader`가 첫 호출 때 NEWS 전체를 한 번 스캔해 `captured_at.date()` 별 **in-memory index**를 만들고, `JsonlStore.revision`이 바뀌면 무효화한다.

이 설계가 다루는 보류 조각: NEWS가 수년치로 커져 **in-memory rebuild(전체 스캔) 자체가 병목**이 될 때의 on-disk persistent index.

---

## 2. 현재 동작과 한계

| 항목 | 현재(C2a) | 한계(보류 사유) |
| ---- | --------- | --------------- |
| 인덱스 위치 | 메모리, `DataReader` 수명 | 프로세스 재시작마다 재빌드 |
| 빌드 비용 | NEWS 전체 1회 스캔 / reader | NEWS가 수년치면 단일 스캔도 비싸짐 |
| 무효화 | `JsonlStore.revision` 변경 시 | 정확하지만, 매 변경마다 전체 재빌드 |

**왜 보류였나.** 현재 핫패스(일반 날짜 윈도우)는 `read_window` 파티션 프루닝이 처리하고, captured-window 반복 스캔은 C2a in-memory cache로 이미 완화됐다. persistent index는 추가 복잡도(on-disk schema, rebuild command, stale fallback, migration)를 들이는데, **그 복잡도를 정당화할 측정이 아직 없다.** 측정 없이 구현하면 YAGNI다.

---

## 3. 설계

### 3.1 인덱스 모델 — 파생 데이터, append-친화

index는 source record가 아니라 **NEWS 파티션에서 파생된 캐시**다. `captured_at.date()` → 그 날짜에 수집된 NEWS record를 담은 `ts` 파티션 파일 목록(또는 record 키 목록)을 매핑한다.

```
data/_index/news_captured/INDEX.jsonl   # 또는 날짜 샤딩
# 각 줄: {"captured_date": "2026-06-18", "partitions": ["news/2026/06/17", "news/2026/06/18"], "revision": "<store revision token>"}
```

- **append-친화 갱신**: 새 NEWS append 시, 그 record의 `captured_at.date()` 엔트리에 파티션을 추가(중복 제거). 전체 재빌드 대신 증분 갱신.
- **revision 스탬프**: 각 엔트리에 빌드 시점의 `JsonlStore.revision`을 박아, store가 인덱스보다 앞서면 stale로 판단.

### 3.2 stale-index fallback — 항상 정확

| 상황 | 동작 |
| ---- | ---- |
| index 없음 | 현재 C2a 경로(전체 스캔)로 fallback. 결과 동일 |
| index revision < store revision (stale) | 해당 captured_date만 부분 재계산하거나, 안전하게 전체 스캔 fallback |
| index 정상 | 인덱스가 가리키는 파티션만 읽어 captured window 구성 |

**불변식**: 인덱스는 *최적화*일 뿐이다. 없거나 stale이면 **항상 전체 스캔으로 떨어져 동일한 정답**을 낸다. 인덱스 버그가 잘못된 분석 결과를 만들면 안 된다.

### 3.3 rebuild command

```bash
mimir index rebuild --dataset news_captured   # 전체 재빌드 (운영/복구용)
```

증분 갱신이 어긋났다고 의심되면 운영자가 전체 재빌드로 복구한다. doctor에 "index staleness" 점검을 선택적으로 추가할 수 있다(별도 결정).

### 3.4 저장 위치 — git-as-DB와의 조화

`data/_index/`는 파생 캐시다. 두 후보: (a) repo 커밋(재현성·감사 가능, 단 git churn) vs (b) gitignore + CI `actions/cache`(repo 깨끗). **권고: gitignore + CI cache** — 인덱스는 언제든 record에서 재생성 가능하므로 git에 둘 이유가 약하다. NEWS 파티션 레이아웃·idempotency_key는 **무변경**.

---

## 4. 테스트 전략 (구현 시)

- **정확성 동치**: 같은 데이터셋에서 index 경로와 전체 스캔 경로의 captured window 결과가 **byte 동일**.
- **증분 갱신**: NEWS append 후 index가 새 captured_date를 반영.
- **stale fallback**: revision이 어긋나면 전체 스캔으로 떨어져 정답 유지.
- **rebuild**: 손상된 index를 rebuild가 복구.
- 모든 테스트는 임시 store로, 네트워크 없이.

---

## 5. 보류 해제 기준 (unblock criteria, 측정 기반)

아래 **측정**이 나오면 구현한다(추정이 아니라 데이터로).

1. NEWS record 수가 수십만~수백만 규모로 누적된다.
2. 한 분석 실행에서 C2a in-memory rebuild(NEWS 전체 스캔)가 측정 가능한 병목이다(예: 실행 시간의 유의미한 비중, 또는 절대 초 단위 임계 초과).
3. 이 병목이 GitHub Actions 무료 cron 시간 예산을 위협한다.

하나라도 미충족이면 C2a in-memory cache가 정답으로 남는다. **먼저 측정하라** — 그 측정 자체가 별도의 작은 작업(예: cache build 시간·record 수를 doctor/dashboard에 노출)이며, 이 설계의 선행 조건이다.

---

## 6. 범위 밖

- `ts` 기준 일반 윈도우(이미 파티션 프루닝으로 빠름).
- NEWS 외 데이터셋(captured window는 NEWS 전용).
- 저장 레이아웃/idempotency_key/partition 변경.

---

## 7. 영향

- **성능**: 큰 NEWS에서 captured window 재빌드를 증분화. 작은 데이터에선 이득 없음(그래서 보류).
- **정확성**: 인덱스는 최적화일 뿐, fallback이 항상 정답 보장(§3.2).
- **저장 계약**: 파생 인덱스만 추가, source record 계약 무변경.
