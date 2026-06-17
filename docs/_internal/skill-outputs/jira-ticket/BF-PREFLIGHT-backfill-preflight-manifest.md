# BF-PREFLIGHT: backfill preflight 실패 manifest 기록

## 요약

1. `backfill`(과거 데이터를 다시 가져와 저장하는 명령)이 fetch 전에 실패해도 실행 기록을 남기도록 보강합니다.
2. 기존에는 `stooq`처럼 등록된 source가 API key 누락으로 제외되면 `SystemExit`만 나고 `_manifest` 기록이 없었습니다.
3. 이제 등록된 source가 secret 또는 optional package gate 때문에 사용할 수 없으면 `ok=false` manifest를 남깁니다.
4. 진짜 unknown source id는 cadence(일간·주간 같은 실행 주기)를 알 수 없으므로 manifest 없이 argument error로 유지합니다.
5. 기존 runtime 실패 기록과 README 3종, 개선 추적 문서를 같은 계약으로 맞췄습니다.

---

## 1. Backfill 실패 기록 범위 확장

### 배경

`data/_manifest/YYYY/MM/DD.jsonl`은 수집 또는 백필 실행 결과를 한 줄씩 남기는 운영 로그입니다. 운영자는 이 파일로 어떤 source가 성공했는지, 몇 건을 가져왔는지, 실패 원인이 무엇인지 확인합니다.

| 용어 | 설명 |
| ---- | ---- |
| `backfill` | 지정한 source에서 과거 기간 데이터를 다시 가져와 저장하는 명령입니다. |
| source | SEC RSS, Stooq, FRED처럼 데이터를 가져오는 제공자입니다. |
| preflight | fetch를 시작하기 전에 source를 만들 수 있는지 확인하는 단계입니다. |
| manifest | 실행 결과를 기록하는 JSONL 로그입니다. |

### 문제

기존 `run_backfill()`은 source build 결과에서 요청한 source id를 찾은 뒤에야 manifest를 만들었습니다. 그래서 등록된 source라도 API key나 optional package가 없어서 build 단계에서 빠지면 기록이 남지 않았습니다.

| 상황 | 기존 결과 | 운영 문제 |
| ---- | --------- | --------- |
| `stooq` API key 없음 | `SystemExit("unknown or unavailable source: stooq")`만 발생 | 어떤 실행이 실패했는지 manifest에서 확인할 수 없음 |
| `pykrx` package 없음 | `SystemExit("unknown or unavailable source: pykrx")`만 발생 | 설치 누락과 unknown id를 구분하기 어려움 |
| `not_a_source` 요청 | 같은 `SystemExit` 발생 | 이 경우는 등록 정보가 없어서 manifest를 쓰면 거짓 cadence가 생김 |

### 해결

`SourceSpec`(source를 만들기 위한 등록 정보)에 static metadata를 선택 필드로 추가했습니다. `run_backfill()`은 source를 만들기 전에 manifest 객체와 spec 목록을 준비합니다.

| 변경 지점 | 해결 방식 |
| --------- | --------- |
| `mimir.core.builder.SourceSpec` | `meta` 필드를 추가해 built-in source의 id와 cadence를 fetch 전에도 알 수 있게 함 |
| `load_source_specs()` | built-in spec과 entry point spec을 한 번에 로드하는 helper 추가 |
| `build_sources(..., specs=...)` | backfill이 같은 spec 목록으로 build 결과와 preflight metadata를 비교할 수 있게 함 |
| `run_backfill()` | 등록됐지만 unavailable인 source는 zero-count `ok=false` manifest를 먼저 기록 |
| unknown source boundary | 등록 정보가 없으면 기존처럼 manifest 없이 argument error 유지 |

---

## 2. 실패 원인 노출 방식

### 배경

Manifest의 `error` 필드는 운영자가 다음 행동을 정하는 데 쓰입니다. 하지만 secret 값은 어떤 로그에도 쓰면 안 됩니다.

### 문제

기존 user-facing 오류 메시지는 `unknown or unavailable source: <id>`로 묶여 있습니다. 이 문구는 CLI 호환성에는 좋지만, 운영자가 API key 누락인지 package 누락인지 바로 알기 어렵습니다.

### 해결

CLI의 `SystemExit` 메시지는 그대로 유지하고, manifest에는 secret 값이 아닌 gate reason만 씁니다.

| gate | manifest error |
| ---- | -------------- |
| missing secret | `STOOQ_API_KEY is not set` |
| missing optional package | `package not installed (pip install -e '.[kr]')` |
| registered source지만 원인 미상 | `unknown or unavailable source: <id>` |

이 방식은 기존 호출자의 실패 감지를 깨지 않으면서 운영 로그의 원인 파악성을 높입니다.

---

## User Scenarios

### Scenario 1: 운영자가 `stooq` 백필을 실행했지만 API key가 없다

- Given 환경 변수에 `STOOQ_API_KEY`가 없다
- When 운영자가 `mimir backfill stooq --since 2018-01-01`을 실행한다
- Then 명령은 기존처럼 `unknown or unavailable source: stooq`로 실패한다
- Then `_manifest`에는 `source="stooq"`, `ok=false`, `error="STOOQ_API_KEY is not set"`이 남는다

### Scenario 2: 한국 주식 백필을 실행했지만 선택 패키지가 없다

- Given `pykrx` package가 설치되지 않았다
- When 운영자가 `mimir backfill pykrx --since 2018-01-01`을 실행한다
- Then 명령은 실패한다
- Then `_manifest`에는 설치 안내가 들어간 `ok=false` 기록이 남는다

### Scenario 3: 운영자가 오타가 있는 source id를 입력한다

- Given 사용자가 `not_a_source`처럼 등록되지 않은 id를 입력한다
- When `backfill`이 source 목록을 확인한다
- Then 명령은 argument error로 끝난다
- Then cadence를 알 수 없으므로 `_manifest`에는 새 실행 기록을 쓰지 않는다

---

## Acceptance Test

### Preflight 실패 기록

- [ ] `stooq` API key가 없을 때 backfill은 `SystemExit`를 유지하고 zero-count `ok=false` manifest를 남긴다.
- [ ] `pykrx` package가 없을 때 backfill은 package hint가 들어간 `ok=false` manifest를 남긴다.
- [ ] preflight failure manifest의 cadence는 built-in source metadata에서 온다.

### 경계 유지

- [ ] unknown source id는 manifest를 쓰지 않는다.
- [ ] fetch, normalize, store 중 발생한 runtime 실패는 기존처럼 `ok=false` manifest를 남기고 원래 예외를 다시 올린다.
- [ ] 기존 plugin이 `SourceSpec(id, factory)`만 넘기는 방식은 계속 동작한다.

### 회귀 방지

- [ ] 전체 테스트는 499개 통과한다.
- [ ] coverage는 98%이고 fail-under 80 gate를 통과한다.
- [ ] `ruff`, `mypy`, `git diff --check`가 통과한다.

---

## 변경 파일 요약

| 영역 | 파일 수 | 주요 파일 |
| ---- | ------- | --------- |
| Backfill preflight 기록 | 2 | `mimir/backfill.py`, `mimir/core/builder.py` |
| 회귀 테스트 | 2 | `tests/test_backfill.py`, `tests/core/test_builder.py` |
| 사용자 문서·개선 추적 | 7 | README 3종, improvement docs, spec, plan |
| 총계 | 11 | +853 / -41 lines |

---

## 배포

- **호환성:** CLI error boundary와 manifest schema는 바뀌지 않습니다.
- **배포 방식:** 일반 코드 배포만 필요합니다. DB migration은 없습니다.
- **롤백:** 구현 커밋을 revert하면 registered-unavailable source는 다시 manifest 없이 `SystemExit`만 남습니다.

### 배포 후 확인 포인트

| 확인 항목 | 정상 | 이상 시 조치 |
| --------- | ---- | ------------ |
| missing secret backfill | `_manifest`에 `ok=false`, zero counts, secret name만 기록 | `run_backfill()`의 preflight branch와 `SourceSpec.meta` 확인 |
| optional package backfill | `_manifest`에 package 설치 hint 기록 | `required_module` gate와 `missing_module_hint` 확인 |
| unknown source id | `_manifest` 미생성 | 잘못된 cadence를 쓰는 fallback이 들어갔는지 확인 |
