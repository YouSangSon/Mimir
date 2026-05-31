import json
from datetime import UTC, datetime

import requests
import responses

from mimir.core.source import Dataset, FetchContext, LegalStatus, Market
from mimir.sources.dart import DartSource

LIST_RESPONSE = {
    "status": "000",
    "message": "정상",
    "list": [
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "stock_code": "005930",
            "report_nm": "주요사항보고서",
            "rcept_no": "20260529000123",
            "flr_nm": "삼성전자",
            "rcept_dt": "20260529",
            "rm": "",
        },
        {
            "corp_code": "00999999",
            "corp_name": "관심없는회사",
            "stock_code": "111111",
            "report_nm": "분기보고서",
            "rcept_no": "20260529000999",
            "flr_nm": "x",
            "rcept_dt": "20260529",
            "rm": "",
        },
    ],
}


def _ctx():
    return FetchContext(watchlist={"kr": ["005930"]}, now=datetime(2026, 5, 31, tzinfo=UTC))


@responses.activate
def test_dart_filters_to_watchlist_stock_codes():
    responses.add(
        responses.GET,
        "https://opendart.fss.or.kr/api/list.json",
        body=json.dumps(LIST_RESPONSE),
        status=200,
    )
    src = DartSource(api_key="dummy", session=requests.Session())
    recs = list(src.fetch(_ctx()))
    assert len(recs) == 1
    rec = recs[0]
    assert rec.symbol == "005930"
    assert rec.idempotency_key == "dart:20260529000123"
    assert rec.payload["form_type"] == "주요사항보고서"
    assert rec.ts == datetime(2026, 5, 29, tzinfo=UTC)
    assert "20260529000123" in rec.payload["url"]


def test_dart_meta():
    assert DartSource.meta.market is Market.KR
    assert DartSource.meta.dataset is Dataset.FILINGS
    assert DartSource.meta.legal_status is LegalStatus.OFFICIAL
    assert DartSource.meta.requires_secret == "DART_API_KEY"


@responses.activate
def test_dart_error_status_raises():
    import pytest

    from mimir.core.errors import FetchError

    responses.add(
        responses.GET,
        "https://opendart.fss.or.kr/api/list.json",
        body=json.dumps({"status": "010", "message": "등록되지 않은 키입니다."}),
        status=200,
    )
    src = DartSource(api_key="dummy", session=requests.Session())
    with pytest.raises(FetchError):
        list(src.fetch(_ctx()))


@responses.activate
def test_dart_no_data_status_is_empty():
    responses.add(
        responses.GET,
        "https://opendart.fss.or.kr/api/list.json",
        body=json.dumps({"status": "013", "message": "조회된 데이터가 없습니다."}),
        status=200,
    )
    src = DartSource(api_key="dummy", session=requests.Session())
    assert list(src.fetch(_ctx())) == []
