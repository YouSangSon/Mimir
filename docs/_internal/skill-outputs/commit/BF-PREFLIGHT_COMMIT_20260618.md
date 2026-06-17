# 커밋 분석

**Date:** 2026-06-18 02:34:47 KST
**Branch:** `feat/backfill-preflight-manifest`

## 변경 파일

| File | Changes |
| ---- | ------- |
| `mimir/core/builder.py` | `SourceSpec.meta`와 `load_source_specs()`를 추가해 source build 전에 registered source의 id와 cadence를 알 수 있게 정리 |
| `mimir/backfill.py` | `run_backfill()`이 registered-unavailable source를 찾으면 zero-count `ok=false` manifest를 기록하고 기존 `SystemExit`를 유지하도록 보강 |
| `tests/test_backfill.py` | missing secret, missing optional package, unknown source, runtime failure 보존 경계를 회귀 테스트로 고정 |
| `tests/core/test_builder.py` | built-in `SourceSpec`가 preflight manifest에 필요한 static metadata를 제공하는지 확인 |
| README 3종 | registered-unavailable source는 manifest를 쓰고 unknown source는 쓰지 않는 boundary를 사용자 문서에 반영 |
| `docs/IMPROVEMENTS.md`, `docs/architecture/improvement-catalog.md` | BF-PREFLIGHT를 완료된 견고성 개선으로 추적 |
| `docs/superpowers/specs`, `docs/superpowers/plans` | 설계와 구현 계획을 검증 결과에 맞춰 기록 |

## 커밋 메시지

fix(backfill): record preflight source failures

- `mimir.core.builder.SourceSpec`가 static source metadata를 들고, `load_source_specs()`가 같은 spec 목록을 build와 preflight lookup에 제공하도록 정리
- `mimir.backfill.run_backfill()`이 API key나 optional package 누락으로 제외된 registered source를 zero-count `ok=false` manifest로 기록하도록 보강
- unknown source id는 cadence를 알 수 없으므로 manifest 없이 기존 argument error를 유지해 실행 로그에 거짓 cadence가 남지 않게 고정
- `tests/test_backfill.py`와 `tests/core/test_builder.py`가 missing secret, missing package, unknown source, runtime failure 보존 경계를 검증
- README 3종과 improvement docs가 registered-unavailable source와 unknown source의 차이를 설명하도록 갱신

## 명령어

```bash
git commit -m "fix(backfill): record preflight source failures

- Add static source metadata to built-in SourceSpec entries so backfill can identify registered sources that were skipped before fetch.
- Write zero-count ok=false manifests for missing secret and optional-package gates while preserving the existing SystemExit boundary.
- Cover registered-unavailable, missing-package, unknown-source, and runtime-failure cases with regression tests.
- Update README and improvement docs to explain unavailable versus unknown source behavior."
```

## 분석

- **Type:** `fix` - 등록된 source가 fetch 전에 제외될 때 실패 실행 기록이 빠지던 사용자-visible 운영 문제를 고칩니다.
- **Scope:** `backfill` - 핵심 변경이 `run_backfill()`의 source lookup과 failure manifest 기록에 집중됩니다.
- **Files:** 11개
- **Lines:** +853 / -41 lines
- **Verification:** `ruff`, `mypy`, `pytest 499`, `coverage TOTAL 98%`, `git diff --check` 통과
