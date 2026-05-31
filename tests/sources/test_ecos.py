import json
import re
from datetime import UTC, datetime

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


def test_ecos_meta():
    assert EcosSource.meta.market is Market.KR
    assert EcosSource.meta.dataset is Dataset.MACRO
    assert EcosSource.meta.legal_status is LegalStatus.OFFICIAL
    assert EcosSource.meta.requires_secret == "ECOS_API_KEY"
