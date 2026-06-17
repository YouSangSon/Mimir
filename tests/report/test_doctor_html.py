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
