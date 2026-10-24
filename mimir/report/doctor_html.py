from __future__ import annotations

from pathlib import Path

from mimir.doctor.report import DoctorReport, Finding, Severity
from mimir.report.html import REPORT_CSS, SEVERITY_COLOR, VIEWPORT_META, esc, render_table
from mimir.report.i18n import DEFAULT_LANG, normalize_lang, t

_SEVERITY_RANK: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.WARN: 1,
    Severity.OK: 2,
}

def _empty(value: object | None) -> str:
    return "—" if value is None else esc(value)


def _ordered_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda finding: _SEVERITY_RANK[finding.severity])


def _severity_label(severity: Severity, lang: str) -> str:
    return t(f"doctor_sev_{severity.value}", lang)


def _finding_row(finding: Finding, lang: str) -> str:
    severity = esc(_severity_label(finding.severity, lang))
    badge = (
        f'<span class="sev" style="background:{SEVERITY_COLOR[finding.severity]}">'
        f"{severity}</span>"
    )
    return (
        f"<tr><td>{esc(finding.dataset.value)}</td>"
        f"<td>{_empty(finding.scope)}</td>"
        f"<td>{badge}</td>"
        f"<td>{esc(finding.message)}</td></tr>"
    )


def _findings_section(report: DoctorReport, lang: str) -> str:
    if report.worst is Severity.OK:
        return f'<p class="empty">{t("doctor_all_clear", lang)}</p>'

    headers = (
        f"<th scope=\"col\">{t('doctor_col_dataset', lang)}</th>"
        f"<th scope=\"col\">{t('doctor_col_scope', lang)}</th>"
        f"<th scope=\"col\">{t('doctor_col_severity', lang)}</th>"
        f"<th scope=\"col\">{t('doctor_col_detail', lang)}</th>"
    )
    rows = "\n".join(_finding_row(finding, lang) for finding in _ordered_findings(report.findings))
    return render_table(headers, rows, t("doctor_heading", lang))


def render_doctor_html(
    report: DoctorReport,
    out_path: Path,
    lang: str = DEFAULT_LANG,
) -> None:
    lang = normalize_lang(lang)
    checked_at = esc(report.checked_at.isoformat())
    data_root = esc(report.data_root)
    worst = esc(_severity_label(report.worst, lang))
    findings = _findings_section(report, lang)

    doc = f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">{VIEWPORT_META}
<title>{t("doctor_page_title", lang)}</title>
<style>{REPORT_CSS}</style></head>
<body><main>
<h1>{t("doctor_heading", lang)}</h1>
<p class="meta">{t("doctor_checked_at", lang)}: {checked_at}</p>
<p class="meta">{t("doctor_data_root", lang)}: {data_root}</p>
<p class="meta">{t("doctor_worst", lang)}: {worst}</p>
{findings}
<p class="dis">{t("disclaimer_status", lang)}</p>
</main></body></html>"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
