# R1l-SEC-CIK-CLI-ERRORS: SEC ticker CIK map CLI 오류 표면 정리

## 요약

1. SEC ticker CIK mapping file이 깨졌을 때 `collect`, `run`, `backfill` CLI가 raw traceback 대신 `[mimir] invalid sources.yaml:` 메시지를 출력합니다.
2. Source build 단계의 `ValueError`만 `SourcesConfigError`로 감쌉니다.
3. Fetch나 analysis 도중 생기는 downstream 오류는 계속 그대로 전파합니다. 런타임 버그를 설정 오류로 오분류하지 않습니다.

---

## 1. CLI에서 설정 오류로 보이게 만들기

### 배경

R1i/R1j/R1k는 `sources.rss.sec.ticker_cik_map_path`가 가리키는 로컬 mapping file의 오류 메시지를 정리했습니다. Loader는 파일 path와 entry key를 포함한 `ValueError`를 만듭니다.

### 문제

`collect`, `run`, `backfill` CLI는 `sources.yaml` pydantic 검증 오류만 friendly message로 바꿨습니다. Mapping file은 `build_sources()` 시점에 읽히므로, loader가 만든 좋은 `ValueError`도 CLI에서는 raw traceback으로 보일 수 있었습니다.

### 해결

Source build 단계의 `ValueError`를 `SourcesConfigError`로 감쌉니다. CLI `main()`은 이 타입만 `report_invalid_sources()`로 전달합니다.

| CLI | 기존 | 변경 |
| ---- | ---- | ---- |
| `mimir collect` | SEC mapping file 오류가 traceback으로 전파 | `[mimir] invalid sources.yaml:` 출력 |
| `mimir run` | `collect` 단계에서 traceback으로 전파 | `[mimir] invalid sources.yaml:` 출력 |
| `mimir backfill` | source build 중 traceback으로 전파 | `[mimir] invalid sources.yaml:` 출력 |

---

## User Scenarios

### Scenario 1: collect에서 mapping file JSON이 깨졌다

- Given `ticker_cik_map_path`가 invalid JSON 파일을 가리킨다
- When 운영자가 `mimir collect --cadence daily`를 실행한다
- Then CLI는 exit code 1과 `[mimir] invalid sources.yaml:` 메시지를 출력한다

### Scenario 2: run에서 collect 단계가 source build에 실패한다

- Given full pipeline config가 같은 invalid mapping file을 쓴다
- When 운영자가 `mimir run --cadence daily`를 실행한다
- Then CLI는 source build 오류를 설정 오류로 보여준다

### Scenario 3: backfill에서 source build가 실패한다

- Given backfill 대상 source와 관계없이 source registry를 만들 때 invalid mapping file을 읽는다
- When 운영자가 `mimir backfill --source rss --since 2024-01-01`를 실행한다
- Then CLI는 raw traceback 없이 설정 오류로 실패한다

---

## Acceptance Test

- [x] `collect` CLI가 invalid SEC mapping file을 `[mimir] invalid sources.yaml:`로 출력한다.
- [x] `run` CLI가 invalid SEC mapping file을 `[mimir] invalid sources.yaml:`로 출력한다.
- [x] `backfill` CLI가 invalid SEC mapping file을 `[mimir] invalid sources.yaml:`로 출력한다.
- [x] downstream `ValidationError`를 설정 오류로 오분류하지 않는 기존 테스트를 유지한다.
- [x] README 3종의 테스트 수치가 현재 pytest 수집 개수와 일치한다.
- [x] 개선 카탈로그가 R1l 완료 범위를 추적한다.

---

## 배포

- **호환성:** 정상 config에는 영향이 없습니다.
- **운영 영향:** 잘못된 SEC mapping file 설정이 CLI에서 더 읽기 쉬운 메시지로 실패합니다.
- **롤백:** 커밋을 revert하면 source build 단계의 mapping file 오류가 다시 raw exception으로 전파될 수 있습니다.
