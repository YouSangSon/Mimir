from datetime import UTC, date, datetime
from pathlib import Path

from mimir import analyze as analyze_module
from mimir.analyze import run_analyze
from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record


def _price(day, close, volume) -> Record:
    return Record(
        source="seed",
        dataset=Dataset.PRICES,
        market=Market.US,
        symbol="AAPL",
        ts=datetime(2026, 5, day, tzinfo=UTC),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
        idempotency_key=f"p:AAPL:{day}",
        payload={
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": volume,
            "currency": "USD",
            "interval": "1d",
        },
    )


def test_run_analyze_writes_insights(tmp_path: Path):
    data_root = tmp_path / "data"
    JsonlStore(root=data_root).append([_price(27, 100.0, 1000), _price(29, 110.0, 5000)])

    insights = run_analyze(
        watchlist={"us": ["AAPL"], "kr": []},
        data_root=data_root,
        as_of=date(2026, 5, 31),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
    )
    assert len(insights) == 1
    assert (data_root / "insights/2026/05/31.jsonl").exists()


def test_main_reports_invalid_sources_yaml(tmp_path: Path, capsys):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "sources.yaml").write_text(
        "analysys:\n  news:\n    use_default_aliases: false\n",
        encoding="utf-8",
    )
    (config_dir / "watchlist.yaml").write_text("us: []\nkr: []\n", encoding="utf-8")

    rc = analyze_module.main(["--config-dir", str(config_dir)])

    assert rc == 1
    assert capsys.readouterr().err.startswith("[mimir] invalid sources.yaml:")
