import pytest
import requests
import responses

from mimir.core.errors import FetchError
from mimir.sources.base import http_get


@responses.activate
def test_http_get_returns_on_2xx():
    responses.add(responses.GET, "https://x.test/ok", body="hi", status=200)
    resp = http_get("https://x.test/ok", session=requests.Session())
    assert resp.text == "hi"


@responses.activate
def test_http_get_raises_on_4xx():
    responses.add(responses.GET, "https://x.test/nope", status=404)
    with pytest.raises(FetchError):
        http_get("https://x.test/nope", session=requests.Session(), max_retries=0)


@responses.activate
def test_http_get_retries_then_succeeds_on_5xx():
    responses.add(responses.GET, "https://x.test/flaky", status=503)
    responses.add(responses.GET, "https://x.test/flaky", body="ok", status=200)
    resp = http_get(
        "https://x.test/flaky",
        session=requests.Session(),
        max_retries=1,
        sleep=lambda s: None,
    )
    assert resp.text == "ok"


@responses.activate
def test_http_get_raises_after_retry_exhaustion():
    responses.add(responses.GET, "https://x.test/down", status=503)
    with pytest.raises(FetchError):
        http_get(
            "https://x.test/down", session=requests.Session(), max_retries=2, sleep=lambda s: None
        )


@responses.activate
def test_http_get_retries_on_429_then_succeeds():
    responses.add(responses.GET, "https://x.test/limited", status=429)
    responses.add(responses.GET, "https://x.test/limited", body="ok", status=200)
    resp = http_get(
        "https://x.test/limited", session=requests.Session(), max_retries=1, sleep=lambda s: None
    )
    assert resp.text == "ok"
