# R1m-SEC-CIK-MISSING-PATH SEC ticker CIK missing lookup path Tech Spec

## 한눈에 보기

SEC `company_tickers.json`를 정상적으로 읽은 뒤 missing ticker lookup이 실패하면, 이제 오류 메시지에 실제 mapping file 경로가 포함됩니다.

## 요약

R1j, R1k, R1l은 file-level, entry-level, CLI-level 오류 표면을 정리했습니다. 남은 gap은 lookup-time failure였습니다. loader-backed mapping이든 plain mapping이든 resolver signature는 모두 `Mapping[str, str]`이기 때문에, path metadata를 public API에 새로 노출하지 않고 내부 dict-compatible wrapper로 해결합니다.

| 결정 | 이유 | 결과 |
| ---- | ---- | ---- |
| private dict subclass 사용 | public resolver signature를 바꾸지 않기 위해 | `load_sec_ticker_cik_map(path)`는 여전히 dict처럼 동작한다 |
| wrapper에 `path` 저장 | lookup-time error가 file context를 읽게 하기 위해 | missing ticker 오류가 `... in <path>`를 포함할 수 있다 |
| plain mapping은 pathless 유지 | caller-provided mapping contract를 바꾸지 않기 위해 | 기존 테스트와 수동 사용 패턴이 유지된다 |

## 목표

- `load_sec_ticker_cik_map(path)`가 dict-compatible object를 계속 반환한다.
- loader-backed mapping은 `path` metadata를 보존한다.
- `_sec_company_filing_identifier()`가 loader-backed missing ticker에서 path를 포함한다.
- plain mapping은 기존 pathless 메시지를 유지한다.

## 목표가 아닌 것

| 항목 | 제외 이유 |
| ---- | --------- |
| SEC mapping file 자동 다운로드 | resolver의 no-network 경계를 유지해야 한다 |
| missing ticker에서 raw ticker fallback | 잘못된 feed를 조용히 만들 수 있다 |
| public resolver 시그니처 변경 | 변경 범위를 불필요하게 넓힌다 |
| mapping loader 재설계 | R1m은 missing lookup error surface만 다룬다 |

## 현재 문제

정상적으로 읽힌 mapping file이라도 missing ticker lookup은 file context를 잃고 있었다.

```mermaid
flowchart TD
    A[load_sec_ticker_cik_map(path)] --> B[dict[str, str]]
    B --> C[_sec_company_filing_identifier]
    C -->|ticker missing, before R1m| D[ValueError without path]
    C -->|ticker missing, after R1m| E[ValueError with path]
```

문제의 핵심은 loader가 만든 값이 plain `dict`가 되면서 `path`를 잃는 점이었다.

## 설계

### Internal wrapper

`mimir/sources/rss_catalog.py` 안에 private dict subclass를 둔다.

```python
class _SecTickerCikMap(dict[str, str]):
    def __init__(..., path: Path | None = None, ...) -> None:
        ...
        self.path = path
```

이 타입은 다음 성질을 유지해야 한다.

- `dict`와 equality 비교가 된다.
- `Mapping[str, str]`처럼 `.get()` 등 기존 사용이 그대로 된다.
- public 함수 반환 타입 힌트는 `dict[str, str]`를 유지한다.

### Lookup behavior

`_sec_company_filing_identifier()`는 `sec_ticker_cik_map.get(selection.ticker)`가 `None`일 때, mapping object에 `Path` 타입의 `path` attribute가 있는지 확인한다.

- 있으면: `SEC ticker CIK map has no entry for ticker <ticker> in <path>`
- 없으면: `SEC ticker CIK map has no entry for ticker <ticker>`

## 실패 / 예외 처리

| 상황 | 처리 |
| ---- | ---- |
| plain mapping missing ticker | 기존 pathless `ValueError` |
| loader-backed mapping missing ticker | path-aware `ValueError` |
| loader file/entry parse 실패 | R1j/R1k 계약 유지 |
| CLI 출력 | R1l 계약 유지 |

## 테스트 전략

| 테스트 | 고정하는 계약 |
| ------ | ------------- |
| `test_resolve_sec_company_filing_feed_missing_ticker_mapping_raises` | plain mapping은 pathless 메시지 유지 |
| `test_resolve_sec_company_filing_feed_missing_loaded_ticker_mapping_includes_path` | loader-backed missing ticker는 file path 포함 |
| `test_load_sec_ticker_cik_map_reads_official_json_shape` | loader return value가 dict equality를 유지 |
| `test_readme_test_badges_match_collected_pytest_count` | README test count drift 방지 |
| `test_improvement_catalog_summary_mentions_latest_completed_ids` | R1m completion tracking |

## 운영 영향

| 항목 | 영향 |
| ---- | ---- |
| 정상 lookup | 변경 없음 |
| missing ticker triage | 어느 `company_tickers.json` 파일을 봤는지 즉시 확인 가능 |
| network/freshness policy | 변경 없음 |
| API surface | 변경 없음 |

## 검증 결과

| 명령 | 결과 |
| ---- | ---- |
| `UV_FROZEN=1 uv run pytest tests/sources/test_rss_catalog.py tests/test_readme_docs.py -q` | 통과 |
| `UV_FROZEN=1 uv run ruff check .` | 통과 |
| `UV_FROZEN=1 uv run mypy mimir` | 통과 |
| `UV_FROZEN=1 uv run pytest -q` | 통과 |
| `UV_FROZEN=1 uv run coverage run -m pytest` | 통과 |
| `UV_FROZEN=1 uv run coverage report --fail-under=80` | 통과 |
| `git diff --check` | 통과 |

---
**버전:** v1.0
**작성일:** 2026-06-18
**상태:** 구현 완료
**관련 문서:** `docs/_internal/skill-outputs/jira-ticket/R1m-SEC-CIK-MISSING-PATH-sec-ticker-cik-missing-path.md`
