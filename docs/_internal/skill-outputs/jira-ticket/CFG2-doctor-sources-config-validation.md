# CFG2: `mimir doctor` sources.yaml 검증

## 요약

1. `mimir doctor`는 운영자가 데이터 상태를 확인할 때 쓰는 점검 명령입니다.
2. 변경 전에는 같은 `--config-dir` 안의 `watchlist.yaml`만 읽고, `sources.yaml` schema 오류는 보지 않았습니다.
3. 그래서 `sources.yaml`에 `analysys:` 같은 오타가 있어도 doctor가 데이터 점검을 계속하고 HTML 파일까지 만들 수 있었습니다.
4. 이제 doctor도 `load_validated_sources_config()`를 먼저 호출합니다.
5. 설정이 잘못되면 데이터 점검이나 HTML 파일 쓰기 전에 `[mimir] invalid sources.yaml:` 메시지와 exit code 1로 실패합니다.

---

## 1. 운영 점검 전에 설정 오류를 잡기

### 배경

`sources.yaml`은 수집 소스, 분석 옵션, 리포트 언어를 담는 설정 파일입니다. 운영자는 같은 `config` directory를 `collect`, `run`, `dashboard`, `doctor` 같은 명령에 넘깁니다.

| 용어 | 설명 |
| ---- | ---- |
| `mimir doctor` | 저장된 데이터의 누락, 오래됨, 짧은 파티션을 읽기 전용으로 점검하는 명령입니다. |
| `sources.yaml` schema | 허용된 최상위 키와 block 구조입니다. 오타가 있으면 설정 오류입니다. |
| friendly message | Python traceback 대신 `[mimir] invalid sources.yaml:`로 시작하는 사용자용 오류입니다. |

### 문제

CFG1은 `analyze`, `deliver`, `dashboard`까지 `sources.yaml` schema 검증을 맞췄습니다. 하지만 `doctor`는 빠져 있었습니다.

| 명령 | CFG2 전 동작 | 운영 영향 |
| ---- | ------------ | --------- |
| `mimir doctor` | `watchlist.yaml`만 읽고 데이터 점검 실행 | 잘못된 `sources.yaml`을 놓칠 수 있음 |
| `mimir doctor --html` | 설정 오류가 있어도 HTML 파일 생성 가능 | 운영자가 정상 점검 결과로 오해할 수 있음 |

### 해결

`doctor_cli.main()`은 argument parse 뒤에 `load_validated_sources_config(config_dir)`를 먼저 호출합니다. 이 helper가 pydantic 검증 오류를 던지면 `report_invalid_sources()`로 exit code 1을 반환합니다.

이 변경은 source를 생성하지 않습니다. 네트워크를 호출하지 않고, SEC mapping file을 다운로드하지 않습니다. Doctor의 데이터 점검은 계속 read-only입니다.

---

## User Scenarios

### Scenario 1: 운영자가 설정 파일에 오타를 넣고 doctor를 실행한다

- Given `sources.yaml`에 `analysys:`처럼 허용되지 않는 최상위 키가 있다
- When 운영자가 `mimir doctor --config-dir config`를 실행한다
- Then stderr가 `[mimir] invalid sources.yaml:`로 시작하고 명령은 exit code 1로 끝난다

### Scenario 2: 잘못된 설정에서 HTML 산출물을 만들지 않는다

- Given `sources.yaml` schema가 깨져 있다
- When 운영자가 `mimir doctor --html reports/doctor.html`을 실행한다
- Then doctor는 `reports/doctor.html`을 만들지 않는다

### Scenario 3: 정상 설정의 doctor 동작은 그대로 유지된다

- Given `sources.yaml`이 없거나 schema가 유효하다
- When 운영자가 text, JSON, HTML, `--strict` 조합으로 doctor를 실행한다
- Then 기존 stdout 형식과 WARN/CRITICAL exit code 정책은 유지된다

---

## Acceptance Test

- [x] `mimir doctor`가 malformed `sources.yaml`에서 stderr에 `[mimir] invalid sources.yaml:`를 출력한다.
- [x] 같은 오류에서 exit code 1을 반환한다.
- [x] `--html`을 함께 넘겨도 HTML 파일을 쓰지 않는다.
- [x] 정상 config의 text/JSON/HTML/strict doctor 테스트는 유지된다.
- [x] README 3종의 테스트 수치가 현재 pytest 수집 개수와 일치한다.
- [x] 개선 카탈로그가 CFG2 완료 범위를 추적한다.

---

## 변경 파일 요약

| 영역 | 파일 | 변경 |
| ---- | ---- | ---- |
| CLI | `mimir/doctor/doctor_cli.py` | `sources.yaml` schema 검증을 doctor 실행 전에 추가 |
| 테스트 | `tests/doctor/test_cli.py` | malformed config + no HTML write 회귀 테스트 추가 |
| 문서 | README 3종, config reference, improvement catalog, CFG2 docs | 새 테스트 수치와 운영 계약 기록 |

---

## 배포

- **호환성:** 정상 `sources.yaml`이나 `sources.yaml` 부재 환경의 doctor 동작은 바뀌지 않습니다.
- **실패 조건:** malformed `sources.yaml`이 있으면 doctor가 이전보다 더 일찍 실패합니다.
- **롤백:** 이 변경을 revert하면 doctor만 다시 `sources.yaml` schema 오류를 보지 않습니다.

### 배포 후 확인 포인트

| 확인 항목 | 정상 | 이상 시 조치 |
| --------- | ---- | ------------ |
| 설정 오류 메시지 | malformed config에서 `[mimir] invalid sources.yaml:` 출력 | `doctor_cli.main()`의 검증 순서 확인 |
| HTML 파일 | 설정 오류에서는 생성되지 않음 | `render_doctor_html()` 호출이 검증 뒤에 있는지 확인 |
| 정상 doctor | fresh data tree에서 exit code 0 | `load_validated_sources_config()`가 absent config를 `{}`로 처리하는지 확인 |
