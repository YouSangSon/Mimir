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
