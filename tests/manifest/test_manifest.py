from datetime import UTC, datetime
from pathlib import Path

from mimir.core.source import Cadence
from mimir.manifest.manifest import Manifest, SourceResult


def test_manifest_writes_and_reads_back(tmp_path: Path):
    m = Manifest(root=tmp_path)
    m.write(
        now=datetime(2026, 5, 31, 12, 0, tzinfo=UTC),
        cadence=Cadence.DAILY,
        results=[
            SourceResult(source="stooq", ok=True, fetched=2, stored=2, invalid=0),
            SourceResult(source="dart", ok=False, error="boom"),
        ],
    )
    path = tmp_path / "_manifest/2026/05/31.jsonl"
    assert path.exists()
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1
    assert '"stored":2' in lines[0].replace(" ", "")
    assert "boom" in lines[0]


def test_source_result_ok_default_counts():
    r = SourceResult(source="x", ok=True)
    assert r.fetched == 0 and r.stored == 0 and r.invalid == 0 and r.error is None
