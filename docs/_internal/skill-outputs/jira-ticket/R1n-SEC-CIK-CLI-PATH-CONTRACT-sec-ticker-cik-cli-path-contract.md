# R1n-SEC-CIK-CLI-PATH-CONTRACT: SEC ticker CIK CLI stderr 경로 계약 고정

## 요약

1. `collect`, `run`, `backfill` CLI 테스트가 모두 `[mimir] invalid sources.yaml:` prefix를 계속 요구합니다.
2. 세 테스트는 각자 만든 로컬 `company_tickers.json`의 정확한 경로 문자열이 stderr에 포함되는지 확인합니다.
3. README 테스트 개수는 바뀌지 않습니다. 이번 작업은 새 테스트를 추가하지 않고 기존 계약을 강화합니다.

---

## 배경

R1m은 loader-backed SEC ticker lookup 오류를 다음 형식으로 정리했습니다.

```text
SEC ticker CIK map has no entry for ticker MSFT in <path>
```

하지만 CLI 회귀 테스트는 아직도 `ticker MSFT` 부분문자열만 확인하고 있었습니다. 그래서 향후 CLI가 경로를 빠뜨려도 테스트가 통과할 수 있었습니다.

운영자 관점에서는 이 경로가 중요합니다. 여러 `company_tickers.json` snapshot을 두고 있으면, 어떤 파일을 보고 실패했는지 stderr 한 줄에서 바로 확인해야 합니다.

## 해결

세 CLI 회귀 테스트를 강화해 operator-facing stderr 계약을 직접 고정합니다.

- `tests/test_collect.py::test_collect_cli_reports_missing_sec_ticker_mapping`
- `tests/test_run.py::test_main_reports_missing_sec_ticker_mapping`
- `tests/test_backfill.py::test_main_reports_missing_sec_ticker_mapping`

각 테스트는 아래 두 조건을 함께 확인합니다.

1. stderr가 `[mimir] invalid sources.yaml:`로 시작한다.
2. stderr에 `SEC ticker CIK map has no entry for ticker MSFT in <path>`가 포함된다.

`backfill`은 brief 요구대로 `config_dir / "company_tickers.json"` 경로를 사용합니다.

## User Scenarios

### Scenario 1: collect CLI

- Given `collect` CLI가 `ticker_cik_map_path: company_tickers.json`을 읽는다
- When mapping에 `MSFT`가 없다
- Then stderr는 prefix와 local map path를 함께 보여준다

### Scenario 2: run CLI

- Given `run` CLI가 같은 설정을 읽는다
- When mapping에 `MSFT`가 없다
- Then stderr는 같은 path-aware 오류 계약을 유지한다

### Scenario 3: backfill CLI

- Given `backfill` CLI가 `--config-dir` 아래의 `company_tickers.json`을 읽는다
- When mapping에 `MSFT`가 없다
- Then stderr는 `config_dir / "company_tickers.json"`의 정확한 경로를 포함한다

## Acceptance Test

- [x] `collect` CLI 회귀 테스트가 exact local path 포함을 요구한다.
- [x] `run` CLI 회귀 테스트가 exact local path 포함을 요구한다.
- [x] `backfill` CLI 회귀 테스트가 `config_dir` 기준 path 포함을 요구한다.
- [x] README 3종 테스트 개수는 기존 수집 개수와 계속 일치한다.
- [x] 개선 카탈로그와 백로그가 R1n 완료 상태를 추적한다.

## 배포

- **호환성:** production behavior는 바꾸지 않습니다. 테스트와 문서 계약만 강화합니다.
- **운영 영향:** CLI stderr가 어느 mapping file을 보고 실패했는지 회귀 없이 유지됩니다.
- **롤백:** 테스트와 문서에서 R1n 항목을 제거하면 이전 느슨한 substring 검증 상태로 돌아갑니다.
