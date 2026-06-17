# 커밋 분석

**Date:** 2026-06-18 KST
**Branch:** `feat/sec-ticker-cik-map`

## Provenance

이 커밋 문서는 R1j 이후의 R1k 후속 변경만 설명합니다. 현재 브랜치에는 DOCHEALTH, R1i, R1j 커밋도 포함되어 있지만, 해당 변경은 별도 commit artifact에 기록되어 있습니다.

## 변경 파일

| File | Changes |
| ---- | ------- |
| `mimir/sources/rss_catalog.py` | SEC mapping loader가 entry key를 보존하고 entry-level validation 오류에 path/key를 포함 |
| `tests/sources/test_rss_catalog.py` | non-object entry, invalid ticker, missing `cik_str`, invalid `cik_str` 회귀 테스트 추가 |
| README 3종 | pytest 수집 개수 528로 갱신 |
| `docs/reference/config/sources.md` | entry-level 오류 표면 문서화 |
| `docs/IMPROVEMENTS.md`, `docs/architecture/improvement-catalog.md` | R1k 완료 범위와 남은 deferred 범위 갱신 |
| `tests/test_readme_docs.py` | 최신 완료 ID 회귀 테스트에 R1k 추가 |
| R1k ticket/spec/commit artifacts | 추적 가능한 산출물 추가 |

## 커밋 메시지

fix(sources): add SEC ticker map entry context

- Preserve SEC ticker CIK map entry keys while parsing local mapping files.
- Wrap entry-level shape and validation failures with path-aware, entry-aware ValueError messages.
- Add regression tests, update README health metadata, and document the R1k operational error surface.

## 명령어

```bash
git commit -m "fix(sources): add SEC ticker map entry context

- Preserve SEC ticker CIK map entry keys while parsing local mapping files.
- Wrap entry-level shape and validation failures with path-aware, entry-aware ValueError messages.
- Add regression tests, update README health metadata, and document the R1k operational error surface."
```

## 분석

- **Type:** `fix` - 잘못된 local mapping entry의 오류 위치를 운영자가 알 수 있게 정리합니다.
- **Scope:** `sources` - 핵심 변경이 RSS catalog loader에 집중됩니다.
- **Verification:** targeted tests 49 passed, `ruff`, `mypy`, full pytest 528 passed, coverage TOTAL 98%, `git diff --check` 통과, reviewer findings 없음
