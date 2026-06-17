# R1j-SEC-CIK-ERRORS: SEC ticker CIK map 오류 표면 정리

## 요약

1. `sources.rss.sec.ticker_cik_map_path`가 가리키는 로컬 파일을 읽을 수 없을 때 low-level 예외 대신 경로가 포함된 설정 오류를 반환합니다.
2. 깨진 JSON이나 SEC `company_tickers.json` 형태가 아닌 최상위 JSON도 명확한 설정 오류로 실패합니다.
3. 자동 다운로드, stale 판단, ticker fallback은 추가하지 않습니다. R1i의 opt-in local file 경계를 유지합니다.

---

## 1. 운영자가 바로 고칠 수 있는 오류 메시지

### 배경

R1i는 SEC ticker를 10자리 CIK로 바꾸기 위해 사용자가 제공한 로컬 `company_tickers.json` 파일을 읽습니다.

### 문제

파일이 없거나 JSON이 깨졌을 때 `FileNotFoundError` 또는 `JSONDecodeError`가 그대로 노출되면, 운영자는 이것이 설정 오류인지 내부 버그인지 바로 판단하기 어렵습니다.

### 해결

`load_sec_ticker_cik_map()`가 파일 읽기와 JSON 파싱 경계에서 오류를 `ValueError`로 정규화하고, 메시지에 대상 path를 포함합니다.

| 실패 | 결과 |
| ---- | ---- |
| 파일 없음 | `SEC ticker CIK map file not found: <path>` |
| 읽기 실패 | `SEC ticker CIK map file could not be read: <path>` |
| invalid JSON | `SEC ticker CIK map file is not valid JSON: <path>` |
| 최상위 JSON이 object가 아님 | `SEC ticker CIK map must be a JSON object: <path>` |

---

## User Scenarios

### Scenario 1: mapping file이 없다

- Given `sources.rss.sec.ticker_cik_map_path`가 누락된 파일을 가리킨다
- When Mimir가 RSS source를 구성한다
- Then 경로가 포함된 설정 오류로 실패한다

### Scenario 2: mapping file JSON이 깨졌다

- Given mapping file이 valid JSON이 아니다
- When Mimir가 mapping file을 읽는다
- Then JSON 파싱 오류 대신 경로가 포함된 설정 오류로 실패한다

### Scenario 3: mapping file 최상위 shape가 틀렸다

- Given mapping file 최상위 값이 JSON object가 아니다
- When Mimir가 mapping file을 읽는다
- Then SEC mapping file shape 오류로 실패한다

---

## Acceptance Test

- [x] missing mapping file은 path가 포함된 `ValueError`를 발생시킨다.
- [x] unreadable mapping file은 path가 포함된 `ValueError`를 발생시킨다.
- [x] invalid JSON mapping file은 path가 포함된 `ValueError`를 발생시킨다.
- [x] non-object JSON mapping file은 path가 포함된 `ValueError`를 발생시킨다.
- [x] README 3종의 테스트 수치가 현재 pytest 수집 개수와 일치한다.
- [x] 개선 카탈로그가 R1j 완료 범위를 추적한다.

---

## 배포

- **호환성:** `ticker_cik_map_path`를 쓰지 않는 환경에는 영향이 없습니다.
- **운영 영향:** 잘못된 mapping file 설정은 더 읽기 쉬운 메시지로 실패합니다.
- **롤백:** 커밋을 revert하면 기존 low-level 예외 표면으로 돌아갑니다.
