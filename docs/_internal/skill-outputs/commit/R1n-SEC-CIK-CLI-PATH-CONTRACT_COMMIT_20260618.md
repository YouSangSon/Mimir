# 커밋 분석

**Date:** 2026-06-18 KST
**Branch:** `feat/sec-cik-missing-map-path`

## Provenance

이 커밋 문서는 R1n CLI stderr path contract 작업만 설명합니다. R1m 이전 resolver/runtime 변경은 각 ticket artifact에 이미 기록되어 있습니다.

## 변경 파일

| File | Changes |
| ---- | ------- |
| `tests/test_collect.py` | collect CLI missing ticker stderr가 exact local map path를 포함하는지 검증 |
| `tests/test_run.py` | run CLI missing ticker stderr가 exact local map path를 포함하는지 검증 |
| `tests/test_backfill.py` | backfill CLI missing ticker stderr가 `config_dir` 기준 exact local map path를 포함하는지 검증 |
| `tests/test_readme_docs.py` | latest completed ID 목록에 R1n 추가 |
| `docs/IMPROVEMENTS.md` | R1n 테스트 계약 강화 항목 추가 |
| `docs/architecture/improvement-catalog.md` | 상태 요약, 표, 상세 섹션, 결론에 R1n 추가 |
| R1n ticket/spec/commit artifacts | 추적 가능한 문서 산출물 추가 |
| `.git/sdd/R1n-SEC-CIK-CLI-PATH-CONTRACT-report.md` | 작업 보고서 작성 |

## 커밋 메시지

test(cli): require SEC ticker map path in missing errors

- Strengthen collect, run, and backfill CLI regressions to require the local `company_tickers.json` path in stderr.
- Keep the friendly `[mimir] invalid sources.yaml:` prefix contract intact.
- Record R1n status tracking in backlog, improvement catalog, and ticket/spec artifacts.

## 분석

- **Type:** `test` - production behavior는 그대로 두고 operator-facing stderr contract를 회귀 테스트로 고정합니다.
- **Scope:** `cli` - collect/run/backfill CLI 테스트와 해당 문서 추적 범위에만 닿습니다.
- **Verification:** targeted pytest, `ruff`, `mypy`, full pytest, coverage(가능 시), `git diff --check`를 실행합니다.
