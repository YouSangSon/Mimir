# DCHTML: doctor HTML report 출력 추가

## 요약

1. `mimir doctor`가 기존 text/JSON 출력은 유지하면서 HTML 파일도 만들 수 있게 합니다.
2. 운영자는 `--html reports/doctor.html`로 진단 결과를 GitHub Pages나 artifact에 그대로 공유할 수 있습니다.
3. HTML 라벨은 `--lang en|ko|zh`로 고를 수 있습니다.
4. WARN/CRITICAL이 없으면 OK/info finding이 있어도 운영상 all-clear로 표시합니다.
5. README 3종, 개선 카탈로그, 설계/계획 문서가 같은 CLI 계약을 설명하도록 맞췄습니다.

---

## 1. Doctor HTML 출력

### 배경

`mimir doctor`는 저장된 데이터가 최신인지, 비어 있지 않은지, watchlist와 맞는지 확인하는 읽기 전용 진단 명령입니다. 기존에는 터미널용 text와 자동화용 JSON만 제공했습니다.

| 용어 | 설명 |
| ---- | ---- |
| `DoctorReport` | doctor가 만든 진단 결과 객체입니다. 점검 시각, data root, finding 목록을 담습니다. |
| finding | 데이터가 없거나 오래됐다는 진단 항목입니다. OK/info finding은 운영 힌트이고 WARN/CRITICAL은 문제입니다. |
| standalone HTML | 별도 서버 없이 파일 하나만 열어도 볼 수 있는 보고서입니다. |

### 문제

운영자가 doctor 결과를 링크나 artifact로 공유하려면 text 출력을 복사하거나 JSON을 사람이 읽어야 했습니다. 기존 C1 데이터 닥터 설계도 `--html`과 3언어 라벨을 선택 후속으로 남겨 두었습니다.

### 해결

`mimir/report/doctor_html.py`에 전용 renderer를 추가했습니다. 이 renderer는 이미 계산된 `DoctorReport`만 받아 HTML 파일을 씁니다.

| 변경 | 결과 |
| ---- | ---- |
| `render_doctor_html(report, out_path, lang)` 추가 | doctor 결과를 standalone HTML로 저장 |
| parent directory 자동 생성 | `reports/doctor.html` 같은 새 경로도 바로 사용 가능 |
| CRITICAL, WARN, OK 순서 정렬 | 가장 중요한 문제를 먼저 표시 |
| WARN/CRITICAL 없음 all-clear | OK/info 힌트가 있어도 운영자는 정상 상태로 읽음 |

---

## 2. CLI 계약 확장

### 배경

`mimir doctor`의 기존 계약은 `--format text|json`과 `--strict`였습니다. `--strict`는 WARN만 있어도 비정상 exit code를 내는 운영 옵션입니다.

### 문제

HTML 파일을 만들기 위해 별도 명령을 추가하면 기존 text/JSON 자동화와 exit code 정책이 갈라질 수 있습니다.

### 해결

기존 명령에 선택 옵션만 추가했습니다.

```text
mimir doctor [--html reports/doctor.html] [--lang en|ko|zh]
```

`--html`이 있어도 stdout은 기존 `--format`을 그대로 따릅니다. exit code도 기존 정책을 그대로 씁니다.

| 조건 | 결과 |
| ---- | ---- |
| `--html` 없음 | 기존 동작과 동일 |
| `--html` 있음 | stdout 출력 후 HTML 파일도 저장 |
| `--lang ko` | HTML 라벨을 한국어로 출력 |
| CRITICAL finding 있음 | exit code 1 유지 |
| WARN만 있고 `--strict` 없음 | exit code 0 유지 |

---

## 3. 보안과 i18n

### 배경

doctor finding에는 dataset, scope, message처럼 저장된 데이터에서 온 문자열이 들어갑니다. 이 값이 HTML에 들어가면 XSS(스크립트 주입) 위험을 막아야 합니다.

### 문제

HTML renderer가 문자열을 그대로 넣으면 `<img onerror=...>` 같은 값이 브라우저에서 실행될 수 있습니다. `<html lang>`도 사용자가 넘긴 값이므로 attribute injection(속성 주입)을 막아야 합니다.

### 해결

renderer는 report-controlled 문자열을 모두 escape합니다. `--lang`은 기존 `normalize_lang()`으로 `en`, `ko`, `zh`만 허용합니다.

| 입력 | 처리 |
| ---- | ---- |
| dataset, scope, message | `html.escape()` 적용 |
| severity label | i18n label 생성 후 escape |
| invalid renderer lang | `en`으로 fallback |
| invalid CLI lang | argparse choices에서 거부 |

---

## User Scenarios

### Scenario 1: 운영자가 doctor 결과를 HTML로 공유한다

- Given 데이터 수집 결과가 `data/`에 저장되어 있다
- When 운영자가 `mimir doctor --html reports/doctor.html`을 실행한다
- Then 터미널에는 기존 text 요약이 출력된다
- Then `reports/doctor.html` 파일이 생성된다

### Scenario 2: 한국어 운영 문서를 위해 doctor report를 만든다

- Given 운영자가 한국어 라벨이 필요하다
- When `mimir doctor --html reports/doctor.html --lang ko`를 실행한다
- Then HTML의 제목과 라벨이 한국어로 표시된다

### Scenario 3: 저장 데이터에 HTML처럼 보이는 문자열이 있다

- Given finding scope나 message에 `<img src=x>` 같은 문자열이 있다
- When HTML report를 만든다
- Then 브라우저는 해당 문자열을 태그가 아니라 텍스트로 보여준다

---

## Acceptance Test

### HTML report 생성

- [ ] `mimir doctor --html <path>`가 parent directory를 만들고 HTML 파일을 저장한다.
- [ ] `--html`을 써도 text stdout은 기존처럼 유지된다.
- [ ] `--format json --html <path>`를 써도 JSON stdout과 HTML 파일 생성이 함께 동작한다.

### 언어와 표시

- [ ] `--lang ko`가 `<html lang="ko">`와 한국어 라벨을 만든다.
- [ ] `--lang zh`가 중국어 라벨을 만든다.
- [ ] renderer에 잘못된 lang 문자열이 들어오면 `en`으로 fallback한다.

### 보안과 회귀

- [ ] scope와 message에 HTML 문자가 있어도 escape된다.
- [ ] CRITICAL finding은 WARN보다 먼저 표시된다.
- [ ] OK/info finding만 있으면 all-clear로 표시된다.

---

## 변경 파일 요약

| 영역 | 파일 수 | 주요 파일 |
| ---- | ----: | --------- |
| HTML renderer와 CLI | 3 | `mimir/report/doctor_html.py`, `mimir/doctor/doctor_cli.py`, `mimir/report/i18n.py` |
| 회귀 테스트 | 2 | `tests/report/test_doctor_html.py`, `tests/doctor/test_cli.py` |
| 사용자 문서와 개선 추적 | 5 | README 3종, `docs/IMPROVEMENTS.md`, `docs/architecture/improvement-catalog.md` |
| 설계/계획 문서 | 2 | DCHTML spec, DCHTML implementation plan |

---

## 배포

- **호환성:** 기존 CLI 옵션, stdout 형식, exit code 정책은 유지됩니다.
- **배포 방식:** 일반 코드 배포만 필요합니다. DB migration은 없습니다.
- **롤백:** 구현 커밋을 revert하면 `--html`과 `--lang` 옵션이 사라지고 기존 text/JSON doctor만 남습니다.

### 배포 후 확인 포인트

| 확인 항목 | 정상 | 이상 시 조치 |
| --------- | ---- | ------------ |
| HTML 파일 생성 | 지정 경로에 HTML 파일 생성 | `doctor_cli.py`의 `--html` path와 parent directory 권한 확인 |
| 언어 라벨 | `lang` attribute와 라벨이 요청 언어와 일치 | `mimir/report/i18n.py`의 doctor key 확인 |
| escape 처리 | `<`와 `>`가 HTML entity로 표시 | `mimir/report/doctor_html.py`의 `_esc()` 적용 지점 확인 |
