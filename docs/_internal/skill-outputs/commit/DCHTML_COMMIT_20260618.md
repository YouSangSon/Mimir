# 커밋 분석

**Date:** 2026-06-18 KST
**Branch:** `feat/doctor-html-report`

## 변경 파일

| File | Changes |
| ---- | ------- |
| `mimir/report/doctor_html.py` | `render_doctor_html()`를 추가해 `DoctorReport`를 standalone HTML 파일로 저장 |
| `mimir/doctor/doctor_cli.py` | `--html`과 `--lang` 옵션을 추가하고 stdout 출력 뒤 HTML renderer를 호출 |
| `mimir/report/i18n.py` | doctor HTML label과 severity label을 en/ko/zh로 추가 |
| `tests/report/test_doctor_html.py` | HTML escape, severity ordering, all-clear, i18n, lang fallback을 검증 |
| `tests/doctor/test_cli.py` | `mimir doctor --html` 파일 생성과 text stdout 보존을 검증 |
| README 3종 | doctor CLI row에 `--html`과 `--lang` 계약 반영 |
| `docs/IMPROVEMENTS.md`, `docs/architecture/improvement-catalog.md` | DCHTML을 완료된 C1 후속 개선으로 추적 |
| `docs/superpowers/specs`, `docs/superpowers/plans` | DCHTML 설계와 구현 계획을 기록 |

## 커밋 메시지

feat(doctor): add html report output

- `mimir.report.doctor_html.render_doctor_html()`가 `DoctorReport`를 standalone HTML로 저장해 운영자가 doctor 결과를 artifact나 Pages로 공유할 수 있게 추가
- `mimir.doctor.doctor_cli.main()`에 `--html`과 `--lang en|ko|zh`를 연결해 기존 text/JSON stdout과 exit code 정책은 그대로 유지
- `mimir.report.i18n`에 doctor label을 en/ko/zh로 추가하고, renderer가 scope와 message를 escape해 HTML 주입 위험을 막도록 구현
- `tests/report/test_doctor_html.py`와 `tests/doctor/test_cli.py`가 severity ordering, all-clear, 언어 라벨, stdout 보존, JSON+HTML, CRITICAL/WARN strict exit code를 회귀 테스트로 고정
- README 3종과 improvement docs가 새 doctor HTML 출력 계약을 설명하도록 갱신

## 명령어

```bash
git commit -m "feat(doctor): add html report output

- Add mimir.report.doctor_html.render_doctor_html so DoctorReport can be saved as a standalone HTML artifact.
- Wire --html and --lang en|ko|zh through mimir.doctor.doctor_cli.main while preserving existing text/JSON stdout and exit-code behavior.
- Add doctor i18n labels and escape report-controlled strings before writing HTML.
- Cover renderer ordering, escaping, all-clear semantics, language labels, and CLI stdout preservation with regression tests.
- Update README and improvement docs to describe the new doctor HTML output contract."
```

## 분석

- **Type:** `feat` - `mimir doctor`에 사용자가 직접 쓰는 새 HTML 출력 기능이 추가됩니다.
- **Scope:** `doctor` - 핵심 변경이 doctor CLI와 doctor report renderer에 집중됩니다.
- **Verification:** `ruff`, `mypy`, `pytest 509`, `coverage TOTAL 98%`, `git diff --check` 통과
