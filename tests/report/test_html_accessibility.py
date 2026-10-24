from __future__ import annotations

import re
from pathlib import Path

import pytest

from mimir.report.daily_report import DIRECTION_COLOR, build_report_html, rebuild_index
from mimir.report.dashboard import build_dashboard_html
from mimir.report.doctor_html import render_doctor_html
from mimir.report.html import SEVERITY_COLOR
from mimir.report.status_html import render_status_html
from tests.report.test_dashboard import (
    NOW,
    _bucket,
    _finding,
    _full,
    _historical,
    _insight,
    _report,
    _run,
)


@pytest.mark.parametrize("page", ["daily", "index", "dashboard", "doctor", "status"])
def test_static_pages_support_zoom_landmarks_and_keyboard_tables(tmp_path: Path, page: str):
    if page == "daily":
        doc = build_report_html([_insight()], NOW.date(), evaluation=[_bucket()])
    elif page == "index":
        doc = rebuild_index(tmp_path).read_text()
    elif page == "dashboard":
        doc = _full()
    else:
        path = tmp_path / f"{page}.html"
        if page == "doctor":
            render_doctor_html(_report([_finding()]), path)
        else:
            render_status_html(_run(), path)
        doc = path.read_text()
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in doc
    assert "maximum-scale" not in doc and "user-scalable=no" not in doc
    assert doc.count("<main>") == doc.count("</main>") == 1
    tables = re.findall(r"<table>.*?</table>", doc, re.S)
    assert len(tables) == (0 if page == "index" else 5 if page == "dashboard" else 1)
    regions = re.findall(r'<div class="table-scroll"[^>]*>', doc)
    assert len(regions) == len(tables)
    for region in regions:
        assert 'tabindex="0"' in region and 'role="region"' in region
        assert re.search(r'aria-label="[^"]+"', region)
    for table in tables:
        assert "<thead>" in table and "<tbody>" in table
        headers = re.findall(r"<th\b[^>]*>", table)
        assert headers and all('scope="col"' in header for header in headers)
        rows = re.findall(r"<tr>(.*?)</tr>", table.split("<tbody>")[1], re.S)
        assert all(len(re.findall(r"<td\b", row)) == len(headers) for row in rows)


@pytest.mark.parametrize("lang,event,horizons", [
    ("en", "event · occurrences", "forward returns (n)"),
    ("ko", "사건 · 발생 횟수", "이후 수익률 (n)"),
    ("zh", "事件 · 次数", "后续收益 (n)"),
])
def test_historical_table_has_translated_headers(lang: str, event: str, horizons: str):
    doc = build_dashboard_html(
        doctor_report=_report(), insights=[], buckets=[], historical=[_historical()],
        run=None, lang=lang, now=NOW,
    )
    assert f'<th scope="col">{event}</th>' in doc
    assert f'<th scope="col">{horizons}</th>' in doc


def test_white_badge_text_has_aa_contrast():
    for color in {*SEVERITY_COLOR.values(), *DIRECTION_COLOR.values()}:
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                  for v in channels]
        luminance = sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))
        assert 1.05 / (luminance + 0.05) >= 4.5, color
