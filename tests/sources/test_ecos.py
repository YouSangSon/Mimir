import json
import re
from datetime import UTC, date, datetime

import pytest
import requests
import responses

from mimir.core.errors import FetchError
from mimir.core.source import Dataset, FetchContext, LegalStatus, Market
from mimir.sources.ecos import EcosSeries, EcosSource

OK = {
    "StatisticSearch": {
        "list_total_count": 2,
        "row": [
            {
                "STAT_CODE": "722Y001",
                "ITEM_CODE1": "0101000",
                "ITEM_NAME1": "한국은행 기준금리",
                "TIME": "202604",
                "DATA_VALUE": "3.50",
                "UNIT_NAME": "%",
            },
            {
                "STAT_CODE": "722Y001",
                "ITEM_CODE1": "0101000",
                "ITEM_NAME1": "한국은행 기준금리",
                "TIME": "202605",
                "DATA_VALUE": "3.50",
                "UNIT_NAME": "%",
            },
        ],
    }
}
NO_DATA = {"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}
ERROR = {"RESULT": {"CODE": "INFO-100", "MESSAGE": "인증키가 유효하지 않습니다."}}

URL_RE = re.compile(r"https://ecos\.bok\.or\.kr/api/StatisticSearch/.*")
SERIES = [EcosSeries(stat_code="722Y001", cycle="M", item_code="0101000")]


def _ctx():
    return FetchContext(watchlist={"us": [], "kr": []}, now=datetime(2026, 5, 31, tzinfo=UTC))


@responses.activate
def test_ecos_parses_monthly_rows():
    responses.add(responses.GET, URL_RE, body=json.dumps(OK), status=200)
    src = EcosSource(api_key="dummy", series=SERIES, session=requests.Session())
    recs = list(src.fetch(_ctx()))
    assert len(recs) == 2
    first = recs[0]
    assert first.symbol == "722Y001.0101000"
    assert first.idempotency_key == "ecos:722Y001:0101000:202604"
    assert first.payload["value"] == 3.50
    assert first.ts == datetime(2026, 4, 1, tzinfo=UTC)  # YYYYMM -> day 1


@responses.activate
def test_ecos_parses_quarterly_rows():
    # Quarterly TIME tokens ("YYYYQn") must keep a stable idempotency key and land
    # on the first day of the quarter, which fixes the storage partition.
    quarterly = {
        "StatisticSearch": {
            "list_total_count": 1,
            "row": [
                {
                    "STAT_CODE": "722Y001",
                    "ITEM_CODE1": "0101000",
                    "ITEM_NAME1": "분기 지표",
                    "TIME": "2026Q2",
                    "DATA_VALUE": "1.25",
                    "UNIT_NAME": "%",
                }
            ],
        }
    }
    responses.add(responses.GET, URL_RE, body=json.dumps(quarterly), status=200)
    series = [EcosSeries(stat_code="722Y001", cycle="Q", item_code="0101000")]
    src = EcosSource(api_key="dummy", series=series, session=requests.Session())
    recs = list(src.fetch(_ctx()))
    assert len(recs) == 1
    rec = recs[0]
    assert rec.idempotency_key == "ecos:722Y001:0101000:2026Q2"
    assert rec.ts == datetime(2026, 4, 1, tzinfo=UTC)  # Q2 -> first day of quarter
    assert rec.ts.date() == date(2026, 4, 1)  # storage partition day


@responses.activate
def test_ecos_parses_annual_rows():
    # Annual TIME tokens ("YYYY") land on Jan 1 and keep the raw token in the key.
    annual = {
        "StatisticSearch": {
            "list_total_count": 1,
            "row": [
                {
                    "STAT_CODE": "722Y001",
                    "ITEM_CODE1": "0101000",
                    "ITEM_NAME1": "연간 지표",
                    "TIME": "2026",
                    "DATA_VALUE": "2.00",
                    "UNIT_NAME": "%",
                }
            ],
        }
    }
    responses.add(responses.GET, URL_RE, body=json.dumps(annual), status=200)
    series = [EcosSeries(stat_code="722Y001", cycle="A", item_code="0101000")]
    src = EcosSource(api_key="dummy", series=series, session=requests.Session())
    recs = list(src.fetch(_ctx()))
    assert len(recs) == 1
    rec = recs[0]
    assert rec.idempotency_key == "ecos:722Y001:0101000:2026"
    assert rec.ts == datetime(2026, 1, 1, tzinfo=UTC)
    assert rec.ts.date() == date(2026, 1, 1)


@responses.activate
def test_ecos_skips_rows_with_blank_or_missing_value():
    # A blank "" or absent DATA_VALUE means "no observation"; the row is skipped
    # rather than coerced to a bogus float.
    payload = {
        "StatisticSearch": {
            "list_total_count": 3,
            "row": [
                {"STAT_CODE": "722Y001", "ITEM_CODE1": "0101000",
                 "TIME": "202604", "DATA_VALUE": "", "UNIT_NAME": "%"},
                {"STAT_CODE": "722Y001", "ITEM_CODE1": "0101000",
                 "TIME": "202605", "UNIT_NAME": "%"},  # DATA_VALUE absent
                {"STAT_CODE": "722Y001", "ITEM_CODE1": "0101000",
                 "TIME": "202606", "DATA_VALUE": "3.75", "UNIT_NAME": "%"},
            ],
        }
    }
    responses.add(responses.GET, URL_RE, body=json.dumps(payload), status=200)
    src = EcosSource(api_key="dummy", series=SERIES, session=requests.Session())
    recs = list(src.fetch(_ctx()))
    assert [r.payload["time"] for r in recs] == ["202606"]


@responses.activate
def test_ecos_no_data_result_is_empty_not_error():
    responses.add(responses.GET, URL_RE, body=json.dumps(NO_DATA), status=200)
    src = EcosSource(api_key="dummy", series=SERIES, session=requests.Session())
    assert list(src.fetch(_ctx())) == []


@responses.activate
def test_ecos_error_result_raises():
    responses.add(responses.GET, URL_RE, body=json.dumps(ERROR), status=200)
    src = EcosSource(api_key="dummy", series=SERIES, session=requests.Session())
    with pytest.raises(FetchError):
        list(src.fetch(_ctx()))


@responses.activate
def test_ecos_redacts_api_key_in_http_errors():
    # The key lives in the URL path; an HTTP error must not leak it downstream.
    responses.add(responses.GET, URL_RE, status=404)
    src = EcosSource(api_key="SECRETKEY123", series=SERIES, session=requests.Session())
    with pytest.raises(FetchError) as ei:
        list(src.fetch(_ctx()))
    assert "SECRETKEY123" not in str(ei.value)
    assert "***" in str(ei.value)


@responses.activate
def test_ecos_paginates_via_list_total_count():
    def _row(t):
        return {"STAT_CODE": "722Y001", "ITEM_CODE1": "0101000", "ITEM_NAME1": "기준금리",
                "TIME": t, "DATA_VALUE": "3.50", "UNIT_NAME": "%"}

    page1 = {"StatisticSearch": {"list_total_count": 150, "row": [_row("202601")]}}
    page2 = {"StatisticSearch": {"list_total_count": 150, "row": [_row("202602")]}}
    responses.add(responses.GET, URL_RE, body=json.dumps(page1), status=200)
    responses.add(responses.GET, URL_RE, body=json.dumps(page2), status=200)
    src = EcosSource(api_key="dummy", series=SERIES, session=requests.Session())
    recs = list(src.fetch(_ctx()))
    assert {r.payload["time"] for r in recs} == {"202601", "202602"}


def test_ecos_meta():
    assert EcosSource.meta.market is Market.KR
    assert EcosSource.meta.dataset is Dataset.MACRO
    assert EcosSource.meta.legal_status is LegalStatus.OFFICIAL
    assert EcosSource.meta.requires_secret == "ECOS_API_KEY"
