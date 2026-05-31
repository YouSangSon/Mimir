import json
from datetime import UTC, datetime

import requests
import responses

from mimir.core.source import Dataset, FetchContext, LegalStatus, Market
from mimir.sources.fred import FredSource

OBS = {
    "observations": [
        {"date": "2026-05-28", "value": "4.50"},
        {"date": "2026-05-29", "value": "4.55"},
        {"date": "2026-05-30", "value": "."},  # FRED uses "." for missing -> skipped
    ]
}


def _ctx():
    return FetchContext(watchlist={"us": [], "kr": []}, now=datetime(2026, 5, 31, tzinfo=UTC))


@responses.activate
def test_fred_emits_observations_and_skips_missing():
    responses.add(
        responses.GET,
        "https://api.stlouisfed.org/fred/series/observations",
        body=json.dumps(OBS),
        status=200,
    )
    src = FredSource(api_key="dummy", series=["DGS10"], session=requests.Session())
    recs = list(src.fetch(_ctx()))
    assert len(recs) == 2  # the "." value is skipped
    first = recs[0]
    assert first.symbol == "DGS10"
    assert first.idempotency_key == "fred:DGS10:2026-05-28"
    assert first.payload["value"] == 4.50
    assert first.payload["series_id"] == "DGS10"
    assert first.ts == datetime(2026, 5, 28, tzinfo=UTC)


def test_fred_meta():
    assert FredSource.meta.market is Market.US
    assert FredSource.meta.dataset is Dataset.MACRO
    assert FredSource.meta.legal_status is LegalStatus.OFFICIAL
    assert FredSource.meta.requires_secret == "FRED_API_KEY"
