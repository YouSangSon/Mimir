# C2a: captured news window 반복 스캔 완화

## 요약

1. 뉴스 분석은 발행일이 아니라 수집일 기준으로 today와 baseline을 봅니다.
2. 변경 전에는 같은 분석 실행에서도 NEWS 전체를 여러 번 다시 읽었습니다.
3. 이번 변경은 `DataReader`가 수집일별 메모리 cache를 만들어 같은 실행의 반복 scan을 줄입니다.
4. 저장 파일 형식과 뉴스 날짜 의미는 바뀌지 않습니다.

---

## 배경

뉴스 record에는 날짜가 두 개 있습니다.

| 용어 | 뜻 |
| ---- | --- |
| `ts` | 기사가 실제로 발행된 시각 |
| `captured_at` | Mimir가 그 기사를 저장한 시각 |

뉴스 시그널은 `captured_at`을 사용합니다. 그래야 어제 발행됐지만 오늘 처음 수집된 뉴스가 오늘 분석에 들어갑니다.

## 문제

`captured_at` 기준 분석은 정확하지만 비용이 있었습니다. NEWS 파일은 `ts.date()` 기준으로 저장됩니다. 그래서 `captured_at` 기준으로 일반 날짜 파티션을 자르면 늦게 수집된 오래된 기사를 놓칠 수 있습니다.

기존 `DataReader.read_captured_window()`는 안전하게 NEWS 전체를 읽고 나서 `captured_at`으로 필터링했습니다. 그러나 `news_volume`은 symbol마다 today와 baseline을 따로 읽습니다. Watchlist가 커지면 같은 NEWS dataset을 계속 다시 읽게 됩니다.

## 해결

`DataReader`가 captured-date 인메모리 cache를 만듭니다.

| Before | After |
| ------ | ----- |
| captured window 호출마다 `JsonlStore.read_all(Dataset.NEWS)` 실행 | 첫 호출만 NEWS 전체를 읽고, 다음 호출은 cache 재사용 |
| store에 새 record가 들어와도 reader가 알 방법 없음 | `JsonlStore.revision`으로 store 변경을 감지 |
| 저장 구조 변경은 없음 | 저장 구조 변경 없음 |

`JsonlStore.revision`은 실제 저장 내용이 바뀔 때만 증가합니다. `DataReader`는 cache가 만든 revision과 현재 store revision을 비교합니다. 값이 다르면 cache를 다시 만듭니다.

## User Scenarios

### Scenario 1: 여러 종목을 분석한다

- Given NEWS 데이터가 이미 저장되어 있다
- When `mimir analyze`가 여러 watchlist symbol을 평가한다
- Then 첫 captured-window 조회 후 같은 실행의 다른 뉴스 window는 메모리 cache를 재사용한다

### Scenario 2: 늦게 수집된 뉴스가 있다

- Given 5월 30일 발행 뉴스가 5월 31일에 처음 수집되었다
- When 5월 31일 뉴스 시그널을 계산한다
- Then 그 뉴스는 여전히 5월 31일 분석 입력에 포함된다

### Scenario 3: 같은 store에 새 뉴스가 추가된다

- Given `DataReader`가 빈 NEWS cache를 이미 만들었다
- When 같은 `JsonlStore`에 새 NEWS record가 append된다
- Then 다음 captured-window 조회는 cache를 다시 만들고 새 record를 반환한다

## Acceptance Test

### captured-window cache

- [x] 같은 `DataReader`에서 today, baseline, symbol-specific NEWS 조회를 해도 `read_all()`은 한 번만 실행된다.
- [x] `JsonlStore.append()` 후 같은 reader가 새 NEWS record를 다시 읽는다.
- [x] `JsonlStore.replace_partition()` 후 같은 reader가 교체된 NEWS partition을 다시 읽는다.
- [x] `captured_at` 기준 inclusive bounds가 유지된다.
- [x] `symbol` 필터가 유지된다.

### 저장소 호환성

- [x] NEWS 파티션 경로는 `data/news/YYYY/MM/DD.jsonl` 그대로 유지된다.
- [x] record JSON 직렬화와 `idempotency_key`는 바뀌지 않는다.
- [x] persistent index 파일이나 migration은 없다.

## 변경 파일 요약

| 영역 | 파일 수 | 주요 파일 |
| ---- | ------- | --------- |
| 저장소 revision | 1 | `mimir/storage/jsonl_store.py` |
| captured-window cache | 1 | `mimir/storage/reader.py` |
| 회귀 테스트 | 1 | `tests/analysis/test_reader.py`의 captured-window cache, append invalidation, replace-partition invalidation |
| 문서/메타데이터 | 10 | README 3종, tech spec, ticket, commit artifact, plan, catalog, backlog, extensibility guide |

## 배포

- **호환성:** 저장 파일, CLI, 설정, API가 바뀌지 않습니다.
- **배포 방식:** 코드 배포만 필요합니다.
- **롤백:** C2a 구현 커밋을 revert하면 이전 full-scan 방식으로 돌아갑니다.

### 배포 후 확인 포인트

| 확인 항목 | 정상 | 이상 시 조치 |
| --------- | ---- | ------------ |
| 분석 결과 개수 | C2a 전후 같은 입력에서 동일 | `DataReader.read_captured_window()` bounds와 symbol filter 확인 |
| 테스트 수 | README badge/table이 pytest collect count와 일치 | `uv run pytest --collect-only -q` 후 README 3종 갱신 |
| 뉴스 분석 시간 | Watchlist가 클수록 반복 scan 감소 | NEWS cache build 시간이 병목인지 별도 계측 |
