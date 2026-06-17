# Doctor HTML Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone `mimir doctor --html <path>` report with en/ko/zh labels while preserving existing text/JSON stdout and exit-code behavior.

**Architecture:** Add a focused `mimir/report/doctor_html.py` renderer that consumes `DoctorReport`, escapes all user/data strings, and writes a standalone HTML file. Extend `doctor_cli.py` with `--html` and `--lang` without introducing a new dependency on `sources.yaml`.

**Tech Stack:** Python 3.14, argparse, pydantic `DoctorReport`, existing `mimir.report.i18n`, pytest, ruff, mypy.

## Global Constraints

- Follow TDD: RED tests must fail before production code changes.
- Keep `mimir doctor` read-only except for the explicit `--html` output file.
- Do not add scheduled workflow doctor hard gate or `--strict` workflow behavior.
- Do not translate `Finding.message`; only headings, columns, severity labels, and empty state use i18n.
- Escape dataset, scope, severity label, and detail/message before writing HTML.
- Keep `--format text|json` stdout behavior unchanged.
- Keep `uv.lock` unstaged.

---

## File Map

| File | Responsibility |
| ---- | -------------- |
| `tests/report/test_doctor_html.py` | Renderer RED/GREEN coverage for escaping, ordering, empty state, i18n |
| `tests/doctor/test_cli.py` | CLI RED/GREEN coverage for `--html` and `--lang` |
| `mimir/report/doctor_html.py` | Standalone doctor HTML renderer |
| `mimir/report/i18n.py` | Add doctor-specific i18n labels in en/ko/zh |
| `mimir/doctor/doctor_cli.py` | Parse `--html` and `--lang`, call renderer |
| `README.md`, `README.ko.md`, `README.zh.md` | Document CLI contract |
| `docs/IMPROVEMENTS.md` | Track completed DCHTML improvement |
| `docs/architecture/improvement-catalog.md` | Add DCHTML to C1/operations status |
| `docs/superpowers/specs/2026-06-18-doctor-html-report-design.md` | Mark acceptance after verification |

---

### Task 1: Write RED Tests

**Files:**
- Create: `tests/report/test_doctor_html.py`
- Modify: `tests/doctor/test_cli.py`

**Interfaces:**
- Consumes: current `DoctorReport`, `Finding`, `Severity`, `doctor_cli.main()`
- Produces: failing tests that define the DCHTML behavior

- [x] **Step 1: Add renderer tests**

Create `tests/report/test_doctor_html.py`:

```python
from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from mimir.core.source import Dataset
from mimir.doctor.report import DoctorReport, Finding, FindingKind, Severity
from mimir.report.doctor_html import render_doctor_html

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


def _finding(
    severity: Severity,
    *,
    scope: str | None = "AAPL",
    message: str = "latest partition 3 business days stale",
) -> Finding:
    return Finding(
        dataset=Dataset.PRICES,
        scope=scope,
        kind=FindingKind.STALE,
        severity=severity,
        message=message,
        latest_ts=date(2026, 6, 12),
        business_days_stale=3,
    )


def _report(findings: list[Finding]) -> DoctorReport:
    return DoctorReport(checked_at=NOW, data_root="data", findings=findings)


def test_render_doctor_html_orders_findings_and_escapes_content(tmp_path: Path):
    out = tmp_path / "doctor.html"
    render_doctor_html(
        _report(
            [
                _finding(Severity.WARN, scope="<b>WARN</b>", message="<img src=x>"),
                _finding(Severity.CRITICAL, scope="CRIT", message="critical stale"),
            ]
        ),
        out,
    )

    html = out.read_text()
    assert html.startswith("<!doctype html>")
    assert 'lang="en"' in html
    assert "dataset" in html
    assert "severity" in html
    assert html.index("CRITICAL") < html.index("WARN")
    assert "<b>WARN</b>" not in html
    assert "&lt;b&gt;WARN&lt;/b&gt;" in html
    assert "<img src=x>" not in html
    assert "&lt;img src=x&gt;" in html


def test_render_doctor_html_all_clear_state(tmp_path: Path):
    out = tmp_path / "doctor.html"
    render_doctor_html(_report([]), out)

    html = out.read_text()
    assert "All clear" in html
    assert "not financial advice" in html.lower()


def test_render_doctor_html_treats_ok_findings_as_all_clear(tmp_path: Path):
    out = tmp_path / "doctor.html"
    render_doctor_html(_report([_finding(Severity.OK)]), out)

    html = out.read_text()
    assert "All clear" in html
    assert "latest partition 3 business days stale" not in html


def test_render_doctor_html_translated_labels(tmp_path: Path):
    out_ko = tmp_path / "doctor-ko.html"
    render_doctor_html(_report([]), out_ko, lang="ko")
    ko = out_ko.read_text()
    assert 'lang="ko"' in ko
    assert "데이터 닥터" in ko
    assert "이상 없음" in ko

    out_zh = tmp_path / "doctor-zh.html"
    render_doctor_html(_report([]), out_zh, lang="zh")
    zh = out_zh.read_text()
    assert 'lang="zh"' in zh
    assert "数据医生" in zh


def test_render_doctor_html_sanitizes_lang_attribute(tmp_path: Path):
    out = tmp_path / "doctor.html"
    render_doctor_html(_report([]), out, lang='en" onmouseover="alert(1)')

    html = out.read_text()
    assert 'lang="en"' in html
    assert "onmouseover" not in html
```

- [x] **Step 2: Add CLI tests**

Append to `tests/doctor/test_cli.py`:

```python
def test_cli_html_writes_file_and_preserves_text_stdout(
    tmp_path: Path, monkeypatch, capsys
):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    config_dir = _write_config(tmp_path, us=[])
    out = tmp_path / "reports" / "doctor.html"

    code = _run(
        [
            "--config-dir",
            str(config_dir),
            "--data-root",
            str(data_root),
            "--html",
            str(out),
        ],
        monkeypatch,
    )

    assert code == 0
    stdout = capsys.readouterr().out
    assert "mimir doctor" in stdout
    html = out.read_text()
    assert "Mimir" in html
    assert "All clear" in html


def test_cli_html_respects_lang(tmp_path: Path, monkeypatch, capsys):
    data_root = tmp_path / "data"
    write_fresh_tree(data_root, NOW)
    config_dir = _write_config(tmp_path, us=[])
    out = tmp_path / "reports" / "doctor.html"

    code = _run(
        [
            "--config-dir",
            str(config_dir),
            "--data-root",
            str(data_root),
            "--html",
            str(out),
            "--lang",
            "ko",
        ],
        monkeypatch,
    )

    assert code == 0
    html = out.read_text()
    assert 'lang="ko"' in html
    assert "데이터 닥터" in html
```

- [x] **Step 3: Verify RED**

Run:

```bash
uv run pytest \
  tests/report/test_doctor_html.py \
  tests/doctor/test_cli.py::test_cli_html_writes_file_and_preserves_text_stdout \
  tests/doctor/test_cli.py::test_cli_html_respects_lang \
  -q
```

Expected before implementation:

- renderer tests fail with `ModuleNotFoundError: No module named 'mimir.report.doctor_html'`
- CLI tests fail because `doctor_cli` does not accept `--html`

---

### Task 2: Implement Renderer and CLI

**Files:**
- Create: `mimir/report/doctor_html.py`
- Modify: `mimir/report/i18n.py`
- Modify: `mimir/doctor/doctor_cli.py`

**Interfaces:**
- Produces: `render_doctor_html(report: DoctorReport, out_path: Path, lang: str = DEFAULT_LANG) -> None`
- Produces: `mimir doctor --html PATH --lang en|ko|zh`

- [x] **Step 1: Add i18n keys**

In `mimir/report/i18n.py`, add the doctor keys to `en`, `ko`, and `zh`.

Required keys:

```python
"doctor_page_title": "...",
"doctor_heading": "...",
"doctor_checked_at": "...",
"doctor_data_root": "...",
"doctor_worst": "...",
"doctor_col_dataset": "...",
"doctor_col_scope": "...",
"doctor_col_severity": "...",
"doctor_col_detail": "...",
"doctor_sev_ok": "...",
"doctor_sev_warn": "...",
"doctor_sev_critical": "...",
"doctor_all_clear": "...",
```

- [x] **Step 2: Add renderer**

Create `mimir/report/doctor_html.py`:

```python
from __future__ import annotations

import html
from pathlib import Path

from mimir.doctor.report import DoctorReport, Finding, Severity
from mimir.report.i18n import DEFAULT_LANG, normalize_lang, t

SEVERITY_COLOR = {
    Severity.CRITICAL: "#dc2626",
    Severity.WARN: "#d97706",
    Severity.OK: "#16a34a",
}


def _esc(value: object) -> str:
    return html.escape(str(value))


def _ordered_findings(findings: list[Finding]) -> list[Finding]:
    rank = {Severity.CRITICAL: 0, Severity.WARN: 1, Severity.OK: 2}
    return sorted(findings, key=lambda f: rank[f.severity])


def _severity_label(severity: Severity, lang: str) -> str:
    return t(f"doctor_sev_{severity.value}", lang)


def _finding_row(finding: Finding, lang: str) -> str:
    color = SEVERITY_COLOR[finding.severity]
    label = _severity_label(finding.severity, lang)
    severity = f'<span class="sev" style="background:{color}">{_esc(label)}</span>'
    scope = _esc(finding.scope) if finding.scope else "&mdash;"
    return (
        f"<tr><td>{_esc(finding.dataset.value)}</td><td>{scope}</td>"
        f"<td>{severity}</td><td>{_esc(finding.message)}</td></tr>"
    )


def _findings_table(report: DoctorReport, lang: str) -> str:
    if report.worst is Severity.OK:
        return f'<p class="empty">{t("doctor_all_clear", lang)}</p>'
    headers = (
        f"<th>{t('doctor_col_dataset', lang)}</th>"
        f"<th>{t('doctor_col_scope', lang)}</th>"
        f"<th>{t('doctor_col_severity', lang)}</th>"
        f"<th>{t('doctor_col_detail', lang)}</th>"
    )
    rows = "\n".join(_finding_row(f, lang) for f in _ordered_findings(report.findings))
    return f"<table><tr>{headers}</tr>\n{rows}\n</table>"


def render_doctor_html(
    report: DoctorReport,
    out_path: Path,
    lang: str = DEFAULT_LANG,
) -> None:
    lang = normalize_lang(lang)
    checked_at = report.checked_at.isoformat(timespec="seconds")
    worst_label = _severity_label(report.worst, lang)
    worst_color = SEVERITY_COLOR[report.worst]
    table = _findings_table(report, lang)
    doc = f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>{t("doctor_page_title", lang)}</title>
<style>
 body{{font-family:system-ui,-apple-system,sans-serif;margin:2rem;background:#0b0f17;color:#e5e7eb}}
 h1{{font-size:1.4rem}}
 .meta{{color:#9ca3af;margin-bottom:.4rem}}
 table{{border-collapse:collapse;width:100%;margin-top:1rem;font-size:.9rem}}
 td,th{{border:1px solid #1f2937;padding:.4rem .7rem;text-align:left}}
 th{{color:#94a3b8;font-weight:600;background:#111827}}
 .sev,.badge{{color:#fff;border-radius:6px;padding:.1rem .5rem;font-size:.8rem}}
 .empty{{color:#9ca3af}}
 .dis{{color:#6b7280;font-size:.8rem;margin-top:2rem;border-top:1px solid #1f2937;padding-top:1rem}}
</style></head>
<body>
<h1>{t("doctor_heading", lang)}</h1>
<p class="meta">{t("doctor_checked_at", lang)}: {checked_at}</p>
<p class="meta">{t("doctor_data_root", lang)}: {_esc(report.data_root)}</p>
<p><span class="badge" style="background:{worst_color}">{t("doctor_worst", lang)}: {_esc(worst_label)}</span></p>
{table}
<p class="dis">{t("disclaimer_status", lang)}</p>
</body></html>"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
```

- [x] **Step 3: Wire CLI**

In `mimir/doctor/doctor_cli.py`:

```python
from mimir.report.doctor_html import render_doctor_html
from mimir.report.i18n import DEFAULT_LANG, LANGS
```

Add parser args:

```python
parser.add_argument("--html", help="optional path for a standalone doctor HTML report")
parser.add_argument("--lang", choices=LANGS, default=DEFAULT_LANG)
```

After stdout emit:

```python
if args.html:
    render_doctor_html(report, Path(args.html), lang=args.lang)
```

- [x] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest \
  tests/report/test_doctor_html.py \
  tests/doctor/test_cli.py::test_cli_html_writes_file_and_preserves_text_stdout \
  tests/doctor/test_cli.py::test_cli_html_respects_lang \
  -q
```

Expected: selected tests pass.

---

### Task 3: Docs and Final Gates

**Files:**
- Modify: `README.md`
- Modify: `README.ko.md`
- Modify: `README.zh.md`
- Modify: `docs/IMPROVEMENTS.md`
- Modify: `docs/architecture/improvement-catalog.md`
- Modify: `docs/superpowers/specs/2026-06-18-doctor-html-report-design.md`
- Modify: `docs/superpowers/plans/2026-06-18-doctor-html-report.md`

**Interfaces:**
- Consumes: final test count and verification results
- Produces: user-facing docs and completed tracking

- [x] **Step 1: Update README CLI rows**

Change the doctor CLI row in all three READMEs to include:

```text
[--html reports/doctor.html] [--lang en|ko|zh]
```

- [x] **Step 2: Update improvement docs**

In `docs/IMPROVEMENTS.md`, add a completed LOW/MEDIUM item:

```markdown
- [x] **doctor HTML report**: C1 doctor spec의 선택 후속인 `--html` 출력이 아직 없었다. → `mimir doctor --html <path> --lang en|ko|zh`가 3언어 라벨의 standalone HTML을 쓰고 기존 text/JSON stdout과 exit code를 유지한다.
```

In `docs/architecture/improvement-catalog.md`, add `DCHTML` near C1/OPS1 and update the sequence map.

- [x] **Step 3: Mark spec and plan checkboxes**

After verification, mark the DCHTML spec acceptance criteria and plan tasks complete.

- [x] **Step 4: Run gates**

Run:

```bash
uv run pytest tests/report/test_doctor_html.py tests/doctor/test_cli.py -q
uv run ruff check .
uv run mypy mimir
uv run pytest -q
uv run coverage run -m pytest
uv run coverage report --fail-under=80
git diff --check
```

- [x] **Step 5: Commit locally**

Keep `uv.lock` unstaged.

```bash
git add \
  mimir/report/doctor_html.py \
  mimir/report/i18n.py \
  mimir/doctor/doctor_cli.py \
  tests/report/test_doctor_html.py \
  tests/doctor/test_cli.py \
  README.md README.ko.md README.zh.md \
  docs/IMPROVEMENTS.md \
  docs/architecture/improvement-catalog.md \
  docs/superpowers/specs/2026-06-18-doctor-html-report-design.md \
  docs/superpowers/plans/2026-06-18-doctor-html-report.md
git commit -m "feat(doctor): add html report output"
```
