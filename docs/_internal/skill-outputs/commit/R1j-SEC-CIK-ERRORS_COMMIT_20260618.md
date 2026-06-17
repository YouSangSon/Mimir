# 커밋 분석

**Date:** 2026-06-18 KST
**Branch:** `feat/sec-ticker-cik-map`

## Provenance

이 커밋 문서는 R1i 이후의 R1j 후속 변경만 설명합니다. 현재 브랜치에는 DOCHEALTH와 R1i 커밋도 포함되어 있지만, 해당 변경은 별도 commit artifact에 기록되어 있습니다.

## 변경 파일

| File | Changes |
| ---- | ------- |
| `mimir/sources/rss_catalog.py` | SEC ticker CIK map file 읽기/JSON 파싱 오류를 path 포함 `ValueError`로 정규화 |
| `tests/sources/test_rss_catalog.py` | missing file, unreadable file, invalid JSON, non-object JSON 회귀 테스트 추가 |
| README 3종 | pytest 수집 개수 524로 갱신 |
| `docs/reference/config/sources.md` | mapping file 오류 표면 문서화 |
| `docs/IMPROVEMENTS.md`, `docs/architecture/improvement-catalog.md` | R1j 완료 범위와 남은 deferred 범위 갱신 |
| `tests/test_readme_docs.py` | 최신 완료 ID 회귀 테스트에 R1j 추가 |
| R1j ticket/spec/commit artifacts | 추적 가능한 산출물 추가 |

## 커밋 메시지

fix(sources): clarify SEC ticker map file errors

- Normalize SEC ticker CIK map file read, parse, and top-level shape failures into path-aware ValueError messages.
- Preserve the R1i opt-in local file boundary without adding live download, stale checks, or ticker fallback.
- Add regression tests, update README health metadata, and document the R1j operational error surface.

## 명령어

```bash
git commit -m "fix(sources): clarify SEC ticker map file errors

- Normalize SEC ticker CIK map file read, parse, and top-level shape failures into path-aware ValueError messages.
- Preserve the R1i opt-in local file boundary without adding live download, stale checks, or ticker fallback.
- Add regression tests, update README health metadata, and document the R1j operational error surface."
```

## 분석

- **Type:** `fix` - 잘못된 local mapping file의 오류 표면을 운영자가 이해할 수 있게 정리합니다.
- **Scope:** `sources` - 핵심 변경이 RSS catalog loader에 집중됩니다.
- **Verification:** targeted tests 45 passed, `ruff`, `mypy`, full pytest 524 passed, coverage TOTAL 98%, `git diff --check` 통과
