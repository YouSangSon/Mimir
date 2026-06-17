# R1n-SEC-CIK-CLI-PATH-CONTRACT SEC ticker CIK CLI path contract Tech Spec

## 한눈에 보기

R1m이 추가한 path-aware missing ticker 오류가 `collect`, `run`, `backfill` CLI stderr에서 계속 보이도록, 세 회귀 테스트가 정확한 local `company_tickers.json` 경로 문자열을 요구합니다.

## 요약

R1m은 source resolver 동작을 고쳤지만, CLI 테스트는 아직 느슨했습니다. 이번 증분은 production code를 바꾸지 않고 test contract를 강화해 operator-facing stderr surface를 고정합니다.

| 결정 | 이유 | 결과 |
| ---- | ---- | ---- |
| 기존 CLI prefix 유지 확인 | friendly config error contract를 계속 보장하기 위해 | stderr는 `[mimir] invalid sources.yaml:`로 시작한다 |
| full `str(path)` 포함 확인 | 어떤 local mapping file을 봤는지 회귀 없이 보장하기 위해 | path-aware 오류가 세 CLI 모두에서 고정된다 |
| invalid JSON 테스트는 유지 | 범위를 넓히지 않고 brief ownership를 지키기 위해 | 기존 JSON parse error contract는 그대로 남는다 |

## 목표

- `tests/test_collect.py`가 local `company_tickers.json` path 포함을 검증한다.
- `tests/test_run.py`가 local `company_tickers.json` path 포함을 검증한다.
- `tests/test_backfill.py`가 `config_dir / "company_tickers.json"` path 포함을 검증한다.
- `tests/test_readme_docs.py`와 docs status tracking이 R1n 완료를 반영한다.

## 목표가 아닌 것

| 항목 | 제외 이유 |
| ---- | --------- |
| CLI production message format 변경 | R1m/R1l 계약은 이미 구현되어 있다 |
| SEC mapping file download/cache | brief가 명시적으로 제외한다 |
| missing lookup에서 raw ticker fallback | 잘못된 SEC feed를 조용히 만들 수 있다 |
| README test count 변경 | 새 테스트 추가가 아니라 기존 테스트 강화 작업이다 |

## 현재 문제

현재 세 CLI 테스트는 다음처럼 느슨하다.

```python
assert "SEC ticker CIK map has no entry for ticker MSFT" in err
```

이 검증은 경로가 빠져도 통과한다. 즉 R1m production behavior가 회귀해도 테스트가 막지 못한다.

## 설계

세 테스트는 모두 아래 구조를 사용한다.

```python
map_path = ...
assert err.startswith("[mimir] invalid sources.yaml:")
assert f"SEC ticker CIK map has no entry for ticker MSFT in {map_path}" in err
```

이 설계는 다음 장점이 있다.

- prefix contract와 path contract를 분리해서 읽기 쉽다.
- pydantic formatting 변화로 multi-line stderr가 생겨도 핵심 운영 계약은 계속 고정된다.
- exact local path를 사용하므로 relative path/working directory drift를 숨기지 않는다.

## 파일별 변경

| 파일 | 변경 |
| ---- | ---- |
| `tests/test_collect.py` | `tmp_path / "company_tickers.json"`를 path assertion에 사용 |
| `tests/test_run.py` | `tmp_path / "company_tickers.json"`를 path assertion에 사용 |
| `tests/test_backfill.py` | `config_dir / "company_tickers.json"`를 path assertion에 사용 |
| `tests/test_readme_docs.py` | latest completed ID 목록에 R1n 추가 |
| `docs/IMPROVEMENTS.md` | 테스트 계약 강화 항목 추가 |
| `docs/architecture/improvement-catalog.md` | 상태, 표, 상세 섹션, 결론에 R1n 추가 |

## 실패 / 예외 처리

| 상황 | 처리 |
| ---- | ---- |
| stderr prefix가 바뀜 | 테스트 실패 |
| stderr에서 path가 빠짐 | 테스트 실패 |
| invalid JSON CLI stderr | 기존 테스트가 그대로 검증 |
| pytest 수집 개수 drift | `tests/test_readme_docs.py`가 별도로 검증 |

## 테스트 전략

| 테스트 | 고정하는 계약 |
| ------ | ------------- |
| `test_collect_cli_reports_missing_sec_ticker_mapping` | collect CLI가 exact local map path를 stderr에 포함 |
| `test_main_reports_missing_sec_ticker_mapping` in `tests/test_run.py` | run CLI가 exact local map path를 stderr에 포함 |
| `test_main_reports_missing_sec_ticker_mapping` in `tests/test_backfill.py` | backfill CLI가 `config_dir` 기준 exact local map path를 stderr에 포함 |
| `test_readme_test_badges_match_collected_pytest_count` | README counts drift 없음 |
| `test_improvement_catalog_summary_mentions_latest_completed_ids` | R1n status tracking 고정 |

## 운영 영향

| 항목 | 영향 |
| ---- | ---- |
| runtime behavior | 변경 없음 |
| test sensitivity | CLI stderr 회귀를 더 빨리 잡는다 |
| docs/status tracking | R1n 완료 범위가 명확해진다 |

## 검증 결과

| 명령 | 결과 |
| ---- | ---- |
| `UV_FROZEN=1 uv run pytest tests/test_collect.py::test_collect_cli_reports_missing_sec_ticker_mapping tests/test_run.py::test_main_reports_missing_sec_ticker_mapping tests/test_backfill.py::test_main_reports_missing_sec_ticker_mapping tests/test_readme_docs.py -q` | 통과 |
| `UV_FROZEN=1 uv run ruff check .` | 통과 |
| `UV_FROZEN=1 uv run mypy mimir` | 통과 |
| `UV_FROZEN=1 uv run pytest -q` | 통과 |
| `git diff --check` | 통과 |
| `UV_FROZEN=1 uv run coverage run -m pytest` | 통과 |
| `UV_FROZEN=1 uv run coverage report --fail-under=80` | 통과 (총 98%) |

---
**버전:** v1.0
**작성일:** 2026-06-18
**상태:** 구현 완료
**관련 문서:** `docs/_internal/skill-outputs/jira-ticket/R1n-SEC-CIK-CLI-PATH-CONTRACT-sec-ticker-cik-cli-path-contract.md`
