# R1i-SEC-CIK: SEC ticker CIK 로컬 매핑 지원

## 요약

1. SEC company filing RSS 설정에서 `ticker`를 쓸 때, 운영자가 제공한 로컬 `company_tickers.json` 파일로 ticker를 10자리 CIK로 바꿀 수 있게 합니다.
2. SEC mapping file은 정확성과 범위가 보장되지 않으므로, Mimir가 파일을 자동 다운로드하거나 stale 여부를 판단하지 않습니다.
3. 같은 ticker가 서로 다른 CIK로 중복되면 모호한 mapping으로 보고 실패합니다.
4. 파일에 ticker가 없으면 ticker token으로 조용히 되돌아가지 않고 실패합니다.
5. README, 설정 reference, 확장성 문서, 개선 카탈로그가 새 opt-in 계약과 남은 보류 범위를 설명합니다.

---

## 1. SEC filing feed ticker 정규화

### 배경

SEC(미국 증권거래위원회)는 EDGAR filing search와 Atom feed를 제공합니다. CIK(Central Index Key)는 SEC가 filer를 식별하는 10자리 번호입니다. Ticker는 거래소에서 쓰는 종목 코드입니다.

| 용어 | 설명 |
| ---- | ---- |
| CIK | SEC 시스템에서 회사나 filer를 식별하는 번호 |
| ticker | `AAPL`, `MSFT` 같은 종목 코드 |
| `company_tickers.json` | SEC가 제공하는 ticker, CIK, 회사명 mapping 파일 |
| Atom feed | SEC Company Search 결과를 RSS/Atom 형식으로 받는 URL |

### 문제

기존 `sources.rss.sec.company_filings[].ticker`는 ticker token을 SEC URL의 `CIK=` query에 그대로 넣었습니다. 이 경로는 편하지만, CIK 기반 URL과 중복 feed 검출을 맞추기 어렵습니다. 운영자가 CIK를 직접 찾지 않으면 더 결정적인 URL을 만들 수 없었습니다.

### 해결

`sources.rss.sec.ticker_cik_map_path`를 추가했습니다. 이 값이 있으면 Mimir는 로컬 JSON 파일을 읽고 ticker를 10자리 CIK로 바꿉니다.

| Before | After |
| ------ | ----- |
| `ticker: AAPL` → `CIK=AAPL` | `ticker_cik_map_path`가 있으면 `ticker: AAPL` → `CIK=0000320193` |
| mapping file 없음 | 기존 ticker token 경로 유지 |
| mapping에 ticker 없음 | 명확한 설정 오류로 실패 |
| 같은 ticker가 다른 CIK로 중복 | ambiguous mapping 오류로 실패 |

---

## 2. Config path와 문서 계약

### 배경

CLI는 `--config-dir`로 `sources.yaml` 위치를 바꿀 수 있습니다. 설정 파일 안의 상대 경로는 사용자가 보통 config directory 기준으로 이해합니다.

### 문제

경로를 현재 작업 디렉터리 기준으로만 해석하면, `mimir collect --config-dir /path/to/config`처럼 실행할 때 mapping file 위치가 헷갈릴 수 있습니다.

### 해결

`load_validated_sources_config()`가 `ticker_cik_map_path` 상대 경로를 config directory 기준으로 절대화합니다. programmatic API에서 `SourcesConfig`를 직접 만들면 전달한 `Path`를 그대로 사용합니다.

---

## User Scenarios

### Scenario 1: 운영자가 SEC mapping file로 ticker feed를 CIK URL로 만든다

- Given 운영자가 SEC `company_tickers.json` 파일을 config directory에 저장했다
- When `sources.rss.sec.ticker_cik_map_path`와 `company_filings[].ticker`를 설정한다
- Then Mimir가 ticker를 10자리 CIK로 바꾼 Atom feed URL을 만든다

### Scenario 2: mapping file에 ticker가 없다

- Given `company_filings[].ticker`가 `MSFT`다
- When mapping file에 `MSFT` 항목이 없다
- Then Mimir는 ticker token fallback을 하지 않고 설정 오류로 실패한다

### Scenario 3: mapping file에 같은 ticker가 다른 CIK로 중복된다

- Given mapping file에 `DUP` ticker가 서로 다른 CIK로 두 번 나온다
- When Mimir가 RSS feed를 만든다
- Then ambiguous mapping 오류가 발생한다

---

## Acceptance Test

### SEC ticker CIK lookup

- [x] SEC `company_tickers.json` 형태를 읽어 ticker를 10자리 CIK로 정규화한다.
- [x] mapping file이 있으면 `ticker: AAPL` feed URL이 `CIK=0000320193`을 사용한다.
- [x] mapping file이 없으면 기존 ticker token URL 동작을 유지한다.
- [x] mapping file에 ticker가 없으면 실패한다.
- [x] 같은 ticker가 다른 CIK로 중복되면 실패한다.

### Config와 문서

- [x] `sources.rss.sec.ticker_cik_map_path`가 `sources.yaml` schema에서 검증된다.
- [x] CLI config loader가 상대 경로를 config directory 기준으로 해석한다.
- [x] README 3종의 테스트 수치가 현재 pytest 수집 개수와 일치한다.
- [x] 개선 카탈로그와 개선 백로그가 R1i 완료 범위와 남은 보류 범위를 설명한다.

---

## 변경 파일 요약

| 영역 | 파일 수 | 주요 파일 |
| ---- | ------: | --------- |
| SEC RSS resolver | 3 | `mimir/sources/rss_catalog.py`, `mimir/sources/config.py`, `mimir/core/builder.py` |
| Config path 처리 | 1 | `mimir/config.py` |
| 회귀 테스트 | 5 | `tests/sources/test_rss_catalog.py`, `tests/sources/test_config.py`, `tests/core/test_builder.py`, `tests/test_config.py`, `tests/test_readme_docs.py` |
| 사용자 문서 | 6 | README 3종, `config/sources.yaml`, config reference, architecture docs |

---

## 배포

- **호환성:** `ticker_cik_map_path`를 설정하지 않으면 기존 ticker token 동작을 유지합니다.
- **배포 방식:** 일반 코드 배포만 필요합니다. DB migration은 없습니다.
- **롤백:** 커밋을 revert하면 `ticker_cik_map_path` 설정이 사라지고 기존 ticker token 또는 직접 CIK 입력만 남습니다.

### 배포 후 확인 포인트

| 확인 항목 | 정상 | 이상 시 조치 |
| --------- | ---- | ------------ |
| RSS source 생성 | mapping file이 있는 ticker feed가 10자리 CIK URL로 생성됨 | `sources.yaml`의 `ticker_cik_map_path`와 JSON 파일 내용을 확인 |
| 누락 ticker | 명확한 설정 오류 발생 | mapping file을 갱신하거나 `cik`를 직접 입력 |
| SEC 요청량 | 추가 네트워크 요청 없음 | resolver가 live download를 하지 않는지 배포 diff 확인 |
