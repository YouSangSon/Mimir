# DOCHEALTH: README health metadata 동기화

## 요약

1. README 3종의 테스트 badge와 상태 표가 실제 pytest 수집 개수와 맞도록 갱신합니다.
2. `tests/test_readme_docs.py`가 README badge/table 값과 `pytest --collect-only` 결과를 비교해 수치 drift를 막습니다.
3. 개선 카탈로그의 상단 상태와 결론이 최신 완료 ID를 빠뜨리지 않도록 회귀 테스트로 고정합니다.
4. `docs/IMPROVEMENTS.md`와 개선 카탈로그에 `DOCHEALTH` 완료 항목을 남깁니다.

---

## 배경

README는 프로젝트의 현재 품질 상태를 빠르게 보여주는 첫 화면입니다. 이 저장소는 tests badge와 품질 표에 테스트 개수를 직접 적고 있어, 테스트가 추가된 뒤 README 수치가 뒤처질 수 있습니다.

| 항목 | 기존 상태 | 문제 |
| ---- | --------- | ---- |
| README tests badge | `499 passing` | 실제 full suite와 불일치 |
| README 품질 표 | `499 passing` | badge와 같은 수동 갱신 지점 |
| 개선 카탈로그 상태 | 일부 최신 ID 누락 | 완료된 증분이 요약에서 빠질 수 있음 |

---

## 해결

### README health 테스트

`tests/test_readme_docs.py`는 현재 pytest가 수집하는 테스트 수를 기준값으로 삼습니다. 이후 README 3종에서 tests badge와 품질 표의 수치를 읽어 같은 값인지 비교합니다.

| 검증 대상 | 고정하는 계약 |
| --------- | ------------- |
| `README.md` | 영문 첫 화면의 badge와 품질 표가 실제 테스트 수와 일치 |
| `README.ko.md` | 한국어 README도 같은 상태 수치 유지 |
| `README.zh.md` | 중국어 README도 같은 상태 수치 유지 |

### 개선 카탈로그 테스트

상단 상태 줄과 결론 문단에 최신 완료 ID가 모두 들어 있는지 확인합니다. 이번 증분에서는 `R1h-SEC-TICKER`, `DCHTML`, `DOCHEALTH`를 고정합니다.

---

## Acceptance Test

- [x] README 3종의 tests badge가 `511 passing`으로 동기화된다.
- [x] README 3종의 품질 표도 `511 passing`으로 동기화된다.
- [x] `pytest --collect-only` 결과와 README 수치가 다르면 테스트가 실패한다.
- [x] 개선 카탈로그 상태와 결론에 최신 완료 ID가 없으면 테스트가 실패한다.
- [x] `docs/IMPROVEMENTS.md`가 README health metadata drift를 완료 항목으로 기록한다.

---

## 검증 결과

| 명령 | 결과 |
| ---- | ---- |
| `uv run pytest tests/test_readme_docs.py -q` | 2 passed |
| `uv run ruff check .` | pass |
| `uv run mypy mimir` | pass, 82 files |
| `uv run pytest -q` | 511 passed |
| `uv run coverage run -m pytest` | 511 passed |
| `uv run coverage report --fail-under=80` | TOTAL 98% |

---

## 배포

- **호환성:** 런타임 동작 변경은 없습니다.
- **운영 영향:** README와 개선 문서의 상태값이 실제 테스트 수와 함께 움직입니다.
- **롤백:** 해당 커밋을 revert하면 README 수치와 문서 회귀 테스트가 이전 상태로 돌아갑니다.
