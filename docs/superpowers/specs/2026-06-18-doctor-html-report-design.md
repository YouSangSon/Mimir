# Doctor HTML Report — 설계

> **스펙 ID**: DCHTML
> **작성일**: 2026-06-18
> **상태**: 구현 완료 · 검증 완료
> **선행**: [데이터 닥터 설계](2026-06-13-data-doctor-design.md) · [발전 카탈로그](../../architecture/improvement-catalog.md)

---

## 1. 한눈에 보기

`mimir doctor`는 저장된 데이터의 신선도와 품질을 읽기 전용으로 점검한다. 변경 전 CLI는 text와 JSON만 출력했다.

원래 C1 데이터 닥터 설계는 선택 후속으로 `--html` 출력과 3언어(en/ko/zh) 라벨을 남겨 두었다. 이 변경은 그 후속을 닫는다.

구현 후 `mimir doctor --html reports/doctor.html --lang ko`는 기존 stdout 출력과 exit code를 유지하면서, 같은 `DoctorReport`를 standalone HTML 파일로 저장한다.

---

## 2. 문제

### 2.1 운영자가 공유할 수 있는 doctor 산출물이 없다

Text 출력은 터미널에서 빠르게 보기 좋다. JSON 출력은 자동화가 읽기 좋다. 하지만 운영자가 GitHub Pages나 artifact로 공유할 수 있는 단일 HTML 산출물은 없다.

| 변경 전 출력 | 장점 | 한계 |
| --------- | ---- | ---- |
| text | 터미널에서 즉시 읽기 좋음 | 링크로 공유하거나 보존하기 어려움 |
| JSON | 자동화가 읽기 좋음 | 사람이 첫 화면에서 상태를 파악하기 어려움 |
| HTML | 변경 전에는 없음 | C1 spec의 선택 후속이 미완료였음 |

### 2.2 C1 수용 기준 일부가 코드와 맞지 않았다

`docs/superpowers/specs/2026-06-13-data-doctor-design.md`는 `--html`이 3언어 라벨로 doctor 섹션을 렌더한다고 적었다. 변경 전 `doctor_cli.py`의 `--format` choices는 `json|text`뿐이었다.

이 격차는 신규 아이디어가 아니라 기존 C1 spec의 남은 수용 기준이다. 그래서 ADR-0001의 추적 가능성 기준상 구현 대상이다.

---

## 3. 목표와 비목표

### 목표

- `mimir doctor` CLI에 `--html <path>`를 추가한다.
- HTML 출력은 기존 text/JSON stdout을 대체하지 않는다.
- HTML 출력은 기존 exit code 정책을 바꾸지 않는다.
- `--lang en|ko|zh`로 HTML 라벨 언어를 고를 수 있게 한다.
- renderer는 `DoctorReport`를 입력으로 받는 순수하고 작은 표면을 가진다.
- `Finding.message`는 번역하지 않고, 라벨과 severity 표시만 i18n한다.
- dataset, scope, severity, message는 HTML escape한다.

### 비목표

- scheduled workflow에 doctor hard gate를 추가하지 않는다.
- dashboard HTML에 doctor 전용 페이지를 끼워 넣지 않는다.
- JSON schema를 바꾸지 않는다.
- `Finding.message` 자체를 3언어로 번역하지 않는다.
- `sources.yaml` 검증을 doctor 기본 경로에 새로 추가하지 않는다.

---

## 4. 설계

### 4.1 독립 renderer를 둔다

새 파일 `mimir/report/doctor_html.py`를 추가한다.

```python
def render_doctor_html(
    report: DoctorReport,
    out_path: Path,
    lang: str = DEFAULT_LANG,
) -> None:
    ...
```

이 함수는 `render_status_html()`처럼 parent directory를 만들고 파일을 덮어쓴다. 입력은 이미 계산된 `DoctorReport`다. 파일을 쓰는 것 외에는 데이터 저장소나 네트워크에 접근하지 않는다.

### 4.2 HTML 구조

HTML은 doctor 전용 페이지다.

| 영역 | 내용 |
| ---- | ---- |
| `<html lang>` | `normalize_lang()`으로 `en|ko|zh`만 허용 |
| header | doctor heading, checked time, data root, worst severity |
| table | dataset, scope, severity, detail |
| empty state | WARN/CRITICAL finding이 없으면 `doctor_all_clear` 출력 |
| disclaimer | 기존 `disclaimer_status` 재사용 |

Finding 정렬은 dashboard와 같은 정책을 쓴다.

1. CRITICAL
2. WARN
3. OK

### 4.3 i18n 키

`mimir/report/i18n.py`에 아래 키를 세 언어 모두 추가한다.

| key | 용도 |
| --- | ---- |
| `doctor_page_title` | HTML title |
| `doctor_heading` | h1 |
| `doctor_checked_at` | 점검 시각 |
| `doctor_data_root` | 데이터 root |
| `doctor_worst` | 최악 severity badge label |
| `doctor_col_dataset` | table header |
| `doctor_col_scope` | table header |
| `doctor_col_severity` | table header |
| `doctor_col_detail` | table header |
| `doctor_sev_ok` | severity label |
| `doctor_sev_warn` | severity label |
| `doctor_sev_critical` | severity label |
| `doctor_all_clear` | empty state |

Severity 값은 `Finding.severity`의 raw value를 그대로 보여주지 않고 i18n label을 쓴다.

### 4.4 CLI 계약

`mimir doctor`에 두 옵션을 추가한다.

```text
--html PATH
--lang {en,ko,zh}
```

`--html`이 없으면 기존 동작과 같다. `--html`이 있으면 stdout은 기존 `--format`에 따라 그대로 출력하고, 같은 report를 HTML 파일로도 쓴다.

Exit code 정책도 기존과 같다.

| 조건 | exit code |
| ---- | --------- |
| CRITICAL 있음 | 1 |
| WARN만 있음 | 0 |
| WARN만 있고 `--strict` | 1 |
| WARN/CRITICAL 없음 | 0 |

---

## 5. 테스트 전략

| 테스트 | 고정하는 계약 |
| ------ | ------------- |
| `test_render_doctor_html_orders_findings_and_escapes_content` | CRITICAL/WARN 정렬, HTML escaping, table label |
| `test_render_doctor_html_all_clear_state` | WARN/CRITICAL finding이 없으면 empty state와 disclaimer 출력 |
| `test_render_doctor_html_treats_ok_findings_as_all_clear` | OK/info finding은 운영상 all-clear로 표시 |
| `test_render_doctor_html_translated_labels` | ko/zh 라벨과 `<html lang>` 출력 |
| `test_render_doctor_html_sanitizes_lang_attribute` | 잘못된 lang이 `en`으로 fallback |
| `test_cli_html_writes_file_and_preserves_text_stdout` | `--html`이 파일을 쓰고 text stdout을 유지 |
| `test_cli_html_respects_lang` | CLI `--lang ko`가 HTML 라벨을 바꿈 |
| `test_cli_json_html_preserves_json_stdout` | `--format json --html`이 JSON stdout과 HTML 파일 생성을 함께 유지 |
| `test_cli_html_preserves_critical_exit_code` | CRITICAL finding의 exit code 1을 HTML 출력에서도 유지 |
| `test_cli_html_preserves_strict_warn_exit_code` | WARN + `--strict`의 exit code 1을 HTML 출력에서도 유지 |

RED 단계에서는 `mimir.report.doctor_html` import가 실패하고, CLI parser가 `--html`을 모른다는 실패가 나야 한다.

---

## 6. 수용 기준

- [x] `mimir doctor --html <path>`가 doctor HTML 파일을 만든다.
- [x] `--html`은 기존 stdout 형식과 exit code를 바꾸지 않는다.
- [x] `--lang en|ko|zh`가 HTML 라벨 언어를 제어한다.
- [x] invalid lang은 argparse choices에서 막히거나 renderer에서 `en`으로 정규화된다.
- [x] HTML은 `Finding.scope`, `Finding.message`, dataset, severity 표시를 escape한다.
- [x] `Finding.message` 본문은 번역하지 않고 사실 문자열로 유지한다.
- [x] README 3종과 C1/DCHTML 문서가 CLI 계약을 설명한다.
- [x] ruff, mypy, pytest, coverage gate, diff-check가 통과한다.

---

## 7. 남는 한계

이 증분은 doctor HTML 파일을 만들지만 scheduled workflow에 별도 `mimir.doctor --html` step을 추가하지 않는다. Scheduled workflow는 이미 dashboard를 publish하고, doctor finding은 dashboard health table에 표시된다. Doctor HTML을 artifact나 Pages에 별도 publish할지는 운영 정책이 필요하다.
