# R1m-SEC-CIK-MISSING-PATH: SEC ticker CIK missing lookup 경로 표면 정리

## 요약

1. 로컬 SEC `company_tickers.json`을 성공적으로 읽은 뒤 ticker lookup이 실패하면, 오류 메시지에 실제 mapping file 경로를 포함합니다.
2. `load_sec_ticker_cik_map(path)`는 계속 dict-compatible object를 반환합니다.
3. 사용자가 직접 넘긴 plain mapping은 기존 pathless 오류 메시지를 유지합니다.

---

## 배경

R1j는 file-level 오류, R1k는 entry-level 오류, R1l은 CLI 출력 오류를 정리했습니다. 하지만 lookup-time missing ticker 오류는 여전히 아래처럼 파일 경로를 잃고 있었습니다.

```text
SEC ticker CIK map has no entry for ticker MSFT
```

운영자가 여러 `company_tickers.json` snapshot을 두고 있을 때, 이 메시지만으로는 어느 파일을 고쳐야 하는지 바로 알기 어렵습니다.

## 해결

`load_sec_ticker_cik_map(path)`가 plain dict와 동일하게 동작하는 작은 내부 wrapper를 반환하도록 바꿉니다. 이 wrapper는 `path` metadata를 보존합니다.

`_sec_company_filing_identifier()`는 missing ticker lookup이 loader-backed map에서 발생했을 때만 아래 형식으로 실패합니다.

```text
SEC ticker CIK map has no entry for ticker MSFT in <path>
```

사용자가 직접 만든 mapping 예를 들어 `{"AAPL": "0000320193"}`는 기존 메시지를 유지합니다.

## User Scenarios

### Scenario 1: plain mapping missing ticker

- Given caller가 plain mapping `{"AAPL": "0000320193"}`를 넘긴다
- When `MSFT` lookup이 발생한다
- Then 오류 메시지는 기존처럼 path 없이 실패한다

### Scenario 2: loaded mapping missing ticker

- Given `load_sec_ticker_cik_map(path)`로 읽은 `company_tickers.json`이 있다
- When mapping에 없는 `MSFT` lookup이 발생한다
- Then 오류 메시지는 `... in <path>`를 포함한다

## Acceptance Test

- [x] plain mapping missing ticker 테스트가 기존 pathless 메시지를 유지한다.
- [x] loader-backed missing ticker 테스트가 `company_tickers.json` 경로를 포함한다.
- [x] `load_sec_ticker_cik_map(path)`와 plain dict의 equality contract가 유지된다.
- [x] README 3종 테스트 개수가 수집 개수와 맞는다.
- [x] 개선 카탈로그가 R1m 완료 범위를 추적한다.

## 배포

- **호환성:** public resolver signature는 바꾸지 않습니다.
- **운영 영향:** missing ticker 오류에서 어떤 mapping file을 봤는지 즉시 알 수 있습니다.
- **롤백:** wrapper와 path-aware 오류 메시지를 제거하면 기존 pathless 메시지로 돌아갑니다.
