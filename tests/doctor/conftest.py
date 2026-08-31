from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from mimir.core.source import Dataset, Market
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.paths import partition_path
from mimir.storage.schema import Record


def _default_payload(dataset: Dataset, symbol: str | None) -> dict[str, Any]:
    """A minimal schema-conforming payload per dataset (Record.payload is the
    typed union since INC2). Doctor checks are freshness/coverage only; payload
    contents are irrelevant beyond being valid."""
    if dataset is Dataset.PRICES:
        return {
            "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0,
            "volume": 1.0, "currency": "USD", "interval": "1d",
        }
    if dataset is Dataset.MACRO:
        return {
            "stat_code": "722Y001",
            "item_code": "0101000",
            "item_name": None,
            "value": 1.0,
            "unit": None,
            "time": "202601",
        }
    if dataset is Dataset.NEWS:
        return {
            "title": "t", "url": "https://example.com/a", "publisher": "p",
            "market": "US", "published_at": None, "summary": "",
        }
    if dataset is Dataset.FILINGS:
        return {
            "form_type": "8-K", "title": "8-K", "accession": "a",
            "url": "https://example.com/f", "filed_at": "2026-01-15",
        }
    if dataset is Dataset.INSIGHTS:
        return {
            "symbol": symbol or "AAPL", "market": "US", "as_of": "2026-01-15",
            "direction": "neutral", "stars": 0, "confidence": 0.0, "attention": 0.0,
            "signals": [], "reasons": [],
            "disclaimer": "For information only. Not financial advice.",
        }
    raise ValueError(f"no default payload for dataset {dataset!r}")


def make_record(
    dataset: Dataset,
    day: date,
    *,
    symbol: str | None = None,
    key: str,
    payload: dict[str, Any] | None = None,
    market: Market = Market.US,
) -> Record:
    return Record(
        source="test",
        dataset=dataset,
        market=market,
        symbol=symbol,
        ts=datetime(day.year, day.month, day.day, tzinfo=UTC),
        captured_at=datetime(day.year, day.month, day.day, tzinfo=UTC),
        idempotency_key=key,
        payload=payload if payload is not None else _default_payload(dataset, symbol),
    )


def write_partition(
    root: Path, dataset: Dataset, day: date, records: list[Record]
) -> Path:
    """Write a synthetic partition file directly (bypasses dedup/append logic).

    Allows writing an *empty* partition (records=[]) to exercise the `empty` check.
    """
    path = partition_path(dataset, day, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(rec.model_dump_json() + "\n")
    return path


def write_fresh_tree(root: Path, now: datetime) -> JsonlStore:
    """Every expected dataset has a non-empty latest partition dated `now`,
    plus enough prior prices partitions that `short` has a baseline."""
    today = now.date()
    store = JsonlStore(root=root)
    # prices: several prior days so the short-check median has >= 3 samples.
    for offset in (4, 3, 2, 1, 0):
        day = date.fromordinal(today.toordinal() - offset)
        recs = [
            make_record(Dataset.PRICES, day, symbol=f"S{i}", key=f"p-{day}-{i}")
            for i in range(10)
        ]
        write_partition(root, Dataset.PRICES, day, recs)
    for dataset in (Dataset.FILINGS, Dataset.NEWS, Dataset.INSIGHTS):
        write_partition(
            root, dataset, today,
            [make_record(dataset, today, key=f"{dataset.value}-{today}")],
        )
    # macro: ECOS base rate (monthly) fresh today.
    write_partition(
        root, Dataset.MACRO, today,
        [
            make_record(
                Dataset.MACRO,
                today,
                symbol="722Y001.0101000",
                key=f"m-{today}",
                market=Market.KR,
            )
        ],
    )
    return store
