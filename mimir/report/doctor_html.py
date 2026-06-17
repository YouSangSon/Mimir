from __future__ import annotations

import html
from pathlib import Path

from mimir.doctor.report import DoctorReport, Finding, Severity
from mimir.report.i18n import DEFAULT_LANG, normalize_lang, t

_SEVERITY_RANK: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.WARN: 1,
    Severity.OK: 2,
}

_SEVERITY_COLOR: dict[Severity, str] = {
    Severity.CRITICAL: "#dc2626",
    Severity.WARN: "#d97706",
    Severity.OK: "#16a34a",
}


def _esc(value: object) -> str:
    return html.escape(str(value))


def _empty(value: object | None) -> str:
    return "—" if value is None else _esc(value)


def _ordered_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda finding: _SEVERITY_RANK[finding.severity])


def _severity_label(severity: Severity, lang: str) -> str:
    return t(f"doctor_sev_{severity.value}", lang)


def _finding_row(finding: Finding, lang: str) -> str:
    severity = _esc(_severity_label(finding.severity, lang))
    badge = (
        f'<span class="sev" style="background:{_SEVERITY_COLOR[finding.severity]}">'
        f"{severity}</span>"
    )
    return (
        f"<tr><td>{_esc(finding.dataset.value)}</td>"
        f"<td>{_empty(finding.scope)}</td>"
        f"<td>{badge}</td>"
        f"<td>{_esc(finding.message)}</td></tr>"
    )


def _findings_section(report: DoctorReport, lang: str) -> str:
    if report.worst is Severity.OK:
        return f'<p class="empty">{t("doctor_all_clear", lang)}</p>'

    headers = (
        f"<th>{t('doctor_col_dataset', lang)}</th>"
        f"<th>{t('doctor_col_scope', lang)}</th>"
        f"<th>{t('doctor_col_severity', lang)}</th>"
        f"<th>{t('doctor_col_detail', lang)}</th>"
    )
    rows = "\n".join(_finding_row(finding, lang) for finding in _ordered_findings(report.findings))
    return f"<table><tr>{headers}</tr>\n{rows}\n</table>"


def render_doctor_html(
    report: DoctorReport,
    out_path: Path,
    lang: str = DEFAULT_LANG,
) -> None:
    lang = normalize_lang(lang)
    checked_at = _esc(report.checked_at.isoformat())
    data_root = _esc(report.data_root)
    worst = _esc(_severity_label(report.worst, lang))
    findings = _findings_section(report, lang)

    doc = f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>{t("doctor_page_title", lang)}</title>
<style>
 body{{font-family:system-ui,-apple-system,sans-serif;margin:2rem;background:#0b0f17;color:#e5e7eb}}
 h1{{font-size:1.4rem;margin-bottom:.5rem}}
 .meta{{color:#9ca3af;margin:.2rem 0}}
 table{{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.9rem}}
 td,th{{border:1px solid #1f2937;padding:.4rem .7rem;text-align:left;vertical-align:top}}
 th{{color:#94a3b8;font-weight:600;background:#111827}}
 .sev{{color:#fff;border-radius:6px;padding:.1rem .5rem;font-size:.8rem;white-space:nowrap}}
 .empty{{color:#9ca3af;margin-top:1.5rem}}
 .dis{{color:#6b7280;font-size:.8rem;margin-top:2rem;border-top:1px solid #1f2937;padding-top:1rem}}
</style></head>
<body>
<h1>{t("doctor_heading", lang)}</h1>
<p class="meta">{t("doctor_checked_at", lang)}: {checked_at}</p>
<p class="meta">{t("doctor_data_root", lang)}: {data_root}</p>
<p class="meta">{t("doctor_worst", lang)}: {worst}</p>
{findings}
<p class="dis">{t("disclaimer_status", lang)}</p>
</body></html>"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
