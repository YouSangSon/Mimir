# 커밋 분석

**Date:** 2026-06-18 KST
**Branch:** `feat/sec-ticker-cik-map`

## Provenance

이 커밋 문서는 R1m missing lookup path 후속 변경만 설명합니다. 이전 R1i~R1l 작업은 각각의 commit artifact에 따로 기록되어 있습니다.

## 변경 파일

| File | Changes |
| ---- | ------- |
| `mimir/sources/rss_catalog.py` | dict-compatible SEC ticker map wrapper 추가, loader path metadata 보존, missing ticker 오류에 path 조건부 포함 |
| `tests/sources/test_rss_catalog.py` | plain mapping pathless 회귀 유지, loader-backed missing ticker path 포함 회귀 추가 |
| `tests/test_readme_docs.py` | improvement catalog 최신 완료 ID에 R1m 추가 |
| README 3종 | pytest 수집 개수 538로 갱신 |
| `docs/reference/config/sources.md` | missing ticker lookup path-aware 오류 메시지 문서화 |
| `docs/IMPROVEMENTS.md`, `docs/architecture/improvement-catalog.md` | R1m 완료 범위와 잔여 deferred 범위 갱신 |
| R1m ticket/spec/commit artifacts | 추적 가능한 산출물 추가 |

## 커밋 메시지

fix(sources): include SEC ticker map path in missing entries

- Preserve loader path metadata on the SEC ticker map without changing resolver signatures.
- Include the mapping file path when a loader-backed SEC ticker lookup is missing.
- Add a regression test, refresh README test counts, and document the R1m error-surface fix.

## 분석

- **Type:** `fix` - lookup-time missing ticker 오류 메시지에 운영 문맥을 보강합니다.
- **Scope:** `sources` - SEC RSS resolver와 그 문서/테스트에만 닿습니다.
- **Verification:** targeted tests, `ruff`, `mypy`, full pytest, coverage, `git diff --check`를 실행한다.
