# R1k-SEC-CIK-ENTRY-ERRORS: SEC ticker CIK map entry 오류 위치 표시

## 요약

1. SEC `company_tickers.json` 파일 안의 개별 entry가 깨졌을 때 파일 경로와 entry key를 오류 메시지에 포함합니다.
2. Entry가 JSON object가 아니거나 `ticker`/`cik_str` 값이 잘못되면 운영자가 어느 항목을 고쳐야 하는지 바로 알 수 있습니다.
3. R1i/R1j의 경계는 유지합니다. 파일 자동 다운로드, stale 판단, ticker fallback은 추가하지 않습니다.

---

## 1. 큰 mapping file에서 고칠 위치를 알려주는 오류

### 배경

SEC(미국 증권거래위원회)의 `company_tickers.json` 파일은 ticker, CIK, 회사명을 담은 큰 JSON object입니다. Mimir는 이 파일을 로컬에서만 읽고 ticker를 10자리 CIK로 바꿉니다.

### 문제

R1j는 파일이 없거나 JSON이 깨진 경우를 정리했습니다. 그러나 파일은 읽혔지만 특정 entry가 잘못된 경우에는 어느 entry가 문제인지 메시지에 드러나지 않았습니다. 운영자는 수천 개 entry 중 잘못된 항목을 직접 찾아야 했습니다.

### 해결

`load_sec_ticker_cik_map()`가 entry key를 함께 전달합니다. Entry 검증 실패는 파일 path와 entry key가 포함된 설정 오류로 실패합니다.

| 실패 | 결과 |
| ---- | ---- |
| entry가 object가 아님 | `SEC ticker CIK map entry '0' must be a JSON object: <path>` |
| invalid ticker | `invalid SEC ticker CIK map entry '0' in <path>: ...` |
| missing/invalid `cik_str` | `invalid SEC ticker CIK map entry '0' in <path>: ...` |
| duplicate ticker + different CIK | 기존 ambiguous mapping 오류를 유지하며 path와 entry key를 덧붙임 |

---

## User Scenarios

### Scenario 1: entry가 배열이다

- Given mapping file에 `"0": []` entry가 있다
- When Mimir가 mapping file을 읽는다
- Then entry key와 파일 경로가 포함된 설정 오류로 실패한다

### Scenario 2: ticker token이 잘못됐다

- Given mapping file에 공백이 들어간 ticker가 있다
- When Mimir가 ticker를 정규화한다
- Then entry key와 파일 경로가 포함된 설정 오류로 실패한다

### Scenario 3: `cik_str`가 빠졌다

- Given mapping file entry에 `ticker`만 있고 `cik_str`가 없다
- When Mimir가 CIK를 정규화한다
- Then entry key와 파일 경로가 포함된 설정 오류로 실패한다

---

## Acceptance Test

- [x] non-object entry는 path와 entry key가 포함된 `ValueError`를 발생시킨다.
- [x] invalid ticker entry는 path와 entry key가 포함된 `ValueError`를 발생시킨다.
- [x] missing `cik_str` entry는 path와 entry key가 포함된 `ValueError`를 발생시킨다.
- [x] invalid `cik_str` entry는 path와 entry key가 포함된 `ValueError`를 발생시킨다.
- [x] 기존 official JSON shape와 duplicate ambiguity 테스트는 유지된다.
- [x] README 3종의 테스트 수치가 현재 pytest 수집 개수와 일치한다.
- [x] 개선 카탈로그가 R1k 완료 범위를 추적한다.

---

## 배포

- **호환성:** 정상 mapping file에는 영향이 없습니다.
- **운영 영향:** 깨진 mapping file을 고칠 때 어느 entry를 봐야 하는지 바로 알 수 있습니다.
- **롤백:** 커밋을 revert하면 entry-level 오류 메시지는 다시 path/key 없는 형태로 돌아갑니다.
