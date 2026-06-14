from datetime import UTC, date, datetime
from pathlib import Path

from mimir.core.source import Dataset, Market
from mimir.history import run_history
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.schema import Record

CLOSES = [100, 100, 90, 95, 96, 86, 92, 93, 83, 90, 92, 95]  # drops at idx 2,5,8


def test_run_history_writes_historical_insights(tmp_path: Path):
    data_root = tmp_path / "data"
    store = JsonlStore(root=data_root)
    store.append(
        [
            Record(
                source="seed",
                dataset=Dataset.PRICES,
                market=Market.US,
                symbol="AAPL",
                ts=datetime(2026, 5, day + 1, tzinfo=UTC),
                captured_at=datetime(2026, 5, 31, tzinfo=UTC),
                idempotency_key=f"p:AAPL:{day}",
                payload={
                    "open": float(c),
                    "high": float(c),
                    "low": float(c),
                    "close": float(c),
                    "volume": 1000.0,
                    "currency": "USD",
                    "interval": "1d",
                },
            )
            for day, c in enumerate(CLOSES)
        ]
    )
    insights = run_history(
        watchlist={"us": ["AAPL"], "kr": []},
        data_root=data_root,
        as_of=date(2026, 5, 31),
        captured_at=datetime(2026, 5, 31, tzinfo=UTC),
    )
    assert any(i.event_type == "sharp_drop" for i in insights)
    assert (data_root / "historical/2026/05/31.jsonl").exists()
