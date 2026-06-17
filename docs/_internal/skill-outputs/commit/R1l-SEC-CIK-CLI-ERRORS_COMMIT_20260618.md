# 커밋 분석

**Date:** 2026-06-18 KST
**Branch:** `feat/sec-ticker-cik-map`

## Provenance

이 커밋 문서는 R1k 이후의 R1l 후속 변경만 설명합니다. 현재 브랜치에는 DOCHEALTH와 R1i~R1k 커밋도 포함되어 있지만, 해당 변경은 별도 commit artifact에 기록되어 있습니다.

## 변경 파일

| File | Changes |
| ---- | ------- |
| `mimir/config.py` | `SourcesConfigError` 추가, friendly report helper가 build-time config error도 받을 수 있게 확장 |
| `mimir/collect.py` | source build `ValueError`를 `SourcesConfigError`로 감싸고 CLI에서 friendly report |
| `mimir/run.py` | `run_collect()`에서 올라온 `SourcesConfigError`를 CLI에서 friendly report |
| `mimir/backfill.py` | source registry build `ValueError`를 `SourcesConfigError`로 감싸고 CLI에서 friendly report |
| `tests/test_collect.py`, `tests/test_run.py`, `tests/test_backfill.py` | SEC mapping file build error, missing ticker mapping CLI 회귀 테스트와 non-config `ValueError` 오분류 방지 테스트 추가 |
| README 3종 | pytest 수집 개수 535로 갱신 |
| `docs/reference/config/sources.md` | CLI 오류 표면 문서화 |
| `docs/IMPROVEMENTS.md`, `docs/architecture/improvement-catalog.md` | R1l 완료 범위 갱신 |
| R1l ticket/spec/commit artifacts | 추적 가능한 산출물 추가 |

## 커밋 메시지

fix(cli): report SEC ticker map build errors

- Wrap source-build ValueError failures as SourcesConfigError so SEC ticker CIK map file errors surface as config errors.
- Teach collect, run, and backfill CLIs to report these failures with the existing invalid sources.yaml format.
- Add regression tests, update README health metadata, and document the R1l operational error surface.

## 명령어

```bash
git commit -m "fix(cli): report SEC ticker map build errors

- Wrap source-build ValueError failures as SourcesConfigError so SEC ticker CIK map file errors surface as config errors.
- Teach collect, run, and backfill CLIs to report these failures with the existing invalid sources.yaml format.
- Add regression tests, update README health metadata, and document the R1l operational error surface."
```

## 분석

- **Type:** `fix` - CLI가 build-time config 오류를 stack trace 없이 보고하게 합니다.
- **Scope:** `cli` - 핵심 변경이 CLI boundary와 config error type에 집중됩니다.
- **Verification:** targeted tests 10 passed, `ruff`, `mypy`, full pytest 535 passed, coverage TOTAL 98%, `git diff --check` 통과, whole-branch reviewer P1 finding fixed
