import json
from datetime import UTC, date, datetime

import requests
import responses

from mimir.core.source import Dataset, FetchContext, LegalStatus
from mimir.sources.sec_edgar import SecEdgarSource

TICKERS = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
SUBMISSIONS = {
    "filings": {
        "recent": {
            "accessionNumber": ["0000320193-26-000050"],
            "form": ["8-K"],
            "filingDate": ["2026-05-29"],
            "primaryDocument": ["aapl-20260529.htm"],
        }
    }
}


def _ctx():
    return FetchContext(watchlist={"us": ["AAPL"]}, now=datetime(2026, 5, 31, tzinfo=UTC))


@responses.activate
def test_sec_edgar_emits_recent_filings():
    responses.add(
        responses.GET,
        "https://www.sec.gov/files/company_tickers.json",
        body=json.dumps(TICKERS),
        status=200,
    )
    responses.add(
        responses.GET,
        "https://data.sec.gov/submissions/CIK0000320193.json",
        body=json.dumps(SUBMISSIONS),
        status=200,
    )
    src = SecEdgarSource(session=requests.Session(), user_agent="Mimir test@example.com")
    recs = list(src.fetch(_ctx()))
    assert len(recs) == 1
    rec = recs[0]
    assert rec.symbol == "AAPL"
    assert rec.idempotency_key == "sec_edgar:0000320193:0000320193-26-000050"
    assert rec.payload["form_type"] == "8-K"
    assert rec.ts == datetime(2026, 5, 29, tzinfo=UTC)
    assert rec.payload["accession"] == "0000320193-26-000050"
    assert rec.payload["url"].startswith(
        "https://www.sec.gov/Archives/edgar/data/320193/000032019326000050/"
    )


def test_sec_edgar_meta():
    assert SecEdgarSource.meta.dataset is Dataset.FILINGS
    assert SecEdgarSource.meta.legal_status is LegalStatus.OFFICIAL


SUBMISSIONS_WITH_FILES = {
    "filings": {
        "recent": {
            "accessionNumber": ["0000320193-26-000050"],
            "form": ["8-K"],
            "filingDate": ["2026-05-29"],
            "primaryDocument": ["aapl-2026.htm"],
        },
        "files": [{"name": "CIK0000320193-submissions-001.json"}],
    }
}
ARCHIVE_BLOCK = {
    "accessionNumber": ["0000320193-19-000010"],
    "form": ["10-K"],
    "filingDate": ["2019-10-31"],
    "primaryDocument": ["aapl-2019.htm"],
}


@responses.activate
def test_sec_edgar_backfill_reads_archive_files():
    responses.add(responses.GET, "https://www.sec.gov/files/company_tickers.json",
                  body=json.dumps(TICKERS), status=200)
    responses.add(responses.GET, "https://data.sec.gov/submissions/CIK0000320193.json",
                  body=json.dumps(SUBMISSIONS_WITH_FILES), status=200)
    responses.add(
        responses.GET,
        "https://data.sec.gov/submissions/CIK0000320193-submissions-001.json",
        body=json.dumps(ARCHIVE_BLOCK),
        status=200,
    )
    ctx = FetchContext(
        watchlist={"us": ["AAPL"]},
        now=datetime(2026, 5, 31, tzinfo=UTC),
        backfill_since=date(2018, 1, 1),
    )
    src = SecEdgarSource(session=requests.Session(), user_agent="Mimir test@example.com")
    recs = list(src.fetch(ctx))
    accessions = {r.payload["accession"] for r in recs}
    # both the recent filing and the older archived filing are returned
    assert accessions == {"0000320193-26-000050", "0000320193-19-000010"}
