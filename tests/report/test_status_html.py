from datetime import UTC, datetime
from pathlib import Path

from mimir.core.source import Cadence
from mimir.manifest.manifest import RunRecord, SourceResult
from mimir.report.status_html import render_status_html


def test_render_writes_html_with_counts(tmp_path: Path):
    out = tmp_path / "status.html"
    run = RunRecord(
        ran_at=datetime(2026, 5, 31, 12, 0, tzinfo=UTC),
        cadence=Cadence.DAILY,
        results=[
            SourceResult(source="stooq", ok=True, fetched=2, stored=2),
            SourceResult(source="dart", ok=False, error="boom"),
        ],
    )
    render_status_html(run, out)
    html = out.read_text()
    assert "<html" in html.lower()
    assert "stooq" in html
    assert "dart" in html
    assert "boom" in html
    assert "not financial advice" in html.lower()


def test_render_status_html_translated(tmp_path: Path):
    run = RunRecord(
        ran_at=datetime(2026, 5, 31, 12, 0, tzinfo=UTC),
        cadence=Cadence.DAILY,
        results=[SourceResult(source="stooq", ok=True, fetched=2, stored=2)],
    )
    out_ko = tmp_path / "ko.html"
    render_status_html(run, out_ko, lang="ko")
    ko = out_ko.read_text()
    assert 'lang="ko"' in ko
    assert "수집 상태" in ko  # collection status
    assert "마지막 실행" in ko  # last run (exercises {time}/{cadence} format)
    assert "수집=2 저장=2" in ko  # fetched/stored detail format

    out_zh = tmp_path / "zh.html"
    render_status_html(run, out_zh, lang="zh")
    zh = out_zh.read_text()
    assert 'lang="zh"' in zh
    assert "采集状态" in zh


def test_render_status_html_sanitizes_lang_attribute(tmp_path: Path):
    run = RunRecord(
        ran_at=datetime(2026, 5, 31, 12, 0, tzinfo=UTC),
        cadence=Cadence.DAILY,
        results=[SourceResult(source="stooq", ok=True, fetched=2, stored=2)],
    )
    out = tmp_path / "status.html"
    render_status_html(run, out, lang='en" onmouseover="alert(1)')
    html = out.read_text()
    assert 'lang="en"' in html
    assert "onmouseover" not in html
