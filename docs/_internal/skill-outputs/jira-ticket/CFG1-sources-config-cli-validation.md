# CFG1: sources.yaml CLI 검증 일관화

## 요약

1. `sources.yaml`(수집 소스와 분석 옵션을 담는 설정 파일)에 오타가 있을 때, 모든 관련 CLI가 같은 메시지로 실패하도록 맞춥니다.
2. 기존에는 `collect`, `run`, `backfill`만 `[mimir] invalid sources.yaml:` 형식으로 실패했습니다.
3. `analyze`는 pydantic(파이썬 데이터 검증 라이브러리) 오류를 그대로 보여줄 수 있었고, `deliver`와 `dashboard`는 설정 오타를 지나칠 수 있었습니다.
4. `load_validated_sources_config()`를 공유 helper로 추가해 CLI 진입점의 검증 방식을 하나로 모았습니다.
5. 설정 검증 뒤 실행 중에 생기는 데이터 검증 오류는 여전히 원래 오류로 드러나도록 `try/except` 범위를 좁게 유지합니다.

---

## 1. CLI 설정 검증

### 배경

`sources.yaml`은 어떤 소스를 켤지, 리포트 언어를 무엇으로 쓸지, 분석 옵션을 어떻게 조정할지를 정합니다. 운영자는 이 파일을 고친 뒤 `mimir collect`, `mimir analyze`, `mimir deliver`, `mimir dashboard` 같은 명령을 실행합니다.

| 용어 | 설명 |
| ---- | ---- |
| `sources.yaml` | 수집·분석·리포트 설정 파일입니다. |
| pydantic `ValidationError` | 설정 값이 schema(허용된 구조와 타입)에 맞지 않을 때 나는 검증 오류입니다. |
| friendly message | 내부 traceback 대신 사용자가 이해할 수 있는 `[mimir] invalid sources.yaml:` 메시지입니다. |

### 문제

같은 설정 파일을 읽는 명령들이 서로 다른 방식으로 실패했습니다.

| 명령 | 기존 동작 | 운영 영향 |
| ---- | --------- | --------- |
| `collect`, `run`, `backfill` | 설정 검증 실패를 friendly message로 보고 | 기대한 동작 |
| `analyze` | raw pydantic 오류가 노출될 수 있음 | 운영자가 설정 문제인지 코드 문제인지 구분하기 어려움 |
| `deliver`, `dashboard` | `lang`만 raw dict에서 읽음 | `analysys:` 같은 최상위 키 오타를 놓칠 수 있음 |

### 해결

`mimir.config.load_validated_sources_config()`가 raw dict load와 parsed config 검증을 한 번에 수행합니다.

| 변경 지점 | 해결 방식 |
| --------- | --------- |
| `mimir.config` | raw `sources.yaml`과 parsed `SourcesConfig`를 함께 반환하는 helper 추가 |
| `analyze` | helper가 반환한 parsed config를 `run_analyze()`에 전달 |
| `deliver`, `dashboard` | helper로 먼저 검증한 뒤 raw dict의 `lang`을 읽음 |
| `collect`, `run`, `backfill` | 기존 friendly message 계약은 유지하고 helper만 공유 |
| 테스트 | malformed `sources.yaml`에서 analyze/deliver/dashboard가 1을 반환하고 출력 파일을 만들지 않는지 고정 |

---

## User Scenarios

### Scenario 1: 운영자가 설정 파일에 오타를 넣은 뒤 분석을 실행한다

- Given `sources.yaml`에 `analysys:`처럼 허용되지 않는 최상위 키가 있다
- When 운영자가 `mimir analyze --config-dir config`를 실행한다
- Then stderr가 `[mimir] invalid sources.yaml:`로 시작하고 명령은 exit code 1로 끝난다

### Scenario 2: 리포트 생성 전에 설정 오류가 발견된다

- Given `sources.yaml`이 schema에 맞지 않는다
- When 운영자가 `mimir deliver` 또는 `mimir dashboard`를 실행한다
- Then report 또는 dashboard 파일을 쓰지 않고 설정 오류를 먼저 보여준다

### Scenario 3: 실행 중 데이터 검증 오류는 설정 오류로 바뀌지 않는다

- Given `sources.yaml` 검증은 통과했다
- When pipeline 실행 중 다른 데이터 검증 오류가 난다
- Then 그 오류는 `[mimir] invalid sources.yaml:`로 오분류되지 않는다

---

## Acceptance Test

### 설정 오류 표시

- [ ] `mimir analyze`는 malformed `sources.yaml`에서 stderr에 `[mimir] invalid sources.yaml:`를 출력하고 1을 반환한다.
- [ ] `mimir deliver`는 malformed `sources.yaml`에서 report 파일을 만들지 않고 1을 반환한다.
- [ ] `mimir dashboard`는 malformed `sources.yaml`에서 dashboard 파일을 만들지 않고 1을 반환한다.

### 회귀 방지

- [ ] `collect`, `run`, `backfill`의 기존 friendly message 동작은 유지된다.
- [ ] runtime/downstream `ValidationError`는 `sources.yaml` 오류로 오분류되지 않는다.
- [ ] 전체 테스트는 495개 통과하고 coverage는 98% 이상을 유지한다.

---

## 변경 파일 요약

| 영역 | 파일 수 | 주요 파일 |
| ---- | ------- | --------- |
| CLI 설정 검증 | 7 | `mimir/config.py`, `mimir/analyze.py`, `mimir/deliver.py`, `mimir/dashboard.py` 외 |
| 회귀 테스트 | 3 | `tests/test_analyze.py`, `tests/test_deliver.py`, `tests/test_dashboard_cli.py` |
| 문서·추적 | 7 | README 3종, `docs/IMPROVEMENTS.md`, improvement catalog, spec, plan |
| 총계 | 17 | +353 / -24 lines |

---

## 배포

- **호환성:** API, 저장 데이터, CLI 인자 형식은 바뀌지 않습니다.
- **배포 방식:** 일반 코드 배포만 필요합니다. DB migration은 없습니다.
- **롤백:** 이 커밋을 revert하면 `analyze`, `deliver`, `dashboard`의 설정 오류 처리만 이전 상태로 돌아갑니다.

### 배포 후 확인 포인트

| 확인 항목 | 정상 | 이상 시 조치 |
| --------- | ---- | ------------ |
| CLI 설정 오류 메시지 | malformed `sources.yaml`에서 `[mimir] invalid sources.yaml:` 출력 | `mimir.config.load_validated_sources_config()` 호출 경로 확인 |
| 리포트 생성 | 설정이 잘못되면 report/dashboard 파일 미생성 | `deliver.main()`과 `dashboard.main()`의 검증 순서 확인 |
| 정기 실행 | 유효한 설정에서는 기존 pipeline과 동일하게 실행 | 최근 배포 커밋과 `sources.yaml` schema 변경 여부 확인 |
