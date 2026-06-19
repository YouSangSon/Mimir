from datetime import UTC, datetime, timedelta

from mimir.core.errors import FetchError
from mimir.sources.config import TickerCikMapRefresh
from mimir.sources.sec_ticker_cik_refresh import refresh_sec_ticker_cik_map

VALID = '{"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}'


class _FakeResp:
    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


class _Recorder:
    def __init__(self, resp=None, exc=None):
        self._resp = resp
        self._exc = exc
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url, *, session, headers):
        self.calls.append((url, headers))
        if self._exc is not None:
            raise self._exc
        return self._resp


def _enabled(**over):
    return TickerCikMapRefresh(enabled=True, **over)


def _now_after(path, hours):
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC) + timedelta(hours=hours)


def test_disabled_makes_no_request_and_no_file(tmp_path):
    path = tmp_path / "company_tickers.json"
    rec = _Recorder(exc=AssertionError("network must not be touched when disabled"))
    refresh_sec_ticker_cik_map(
        path, TickerCikMapRefresh(enabled=False), user_agent="Svc me@x.com", http_get_fn=rec
    )
    assert rec.calls == []
    assert not path.exists()


def test_fresh_file_within_ttl_skips_request(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text("old", encoding="utf-8")
    rec = _Recorder(exc=AssertionError("fresh file must not trigger a request"))
    refresh_sec_ticker_cik_map(
        path,
        _enabled(max_age_hours=168),
        user_agent="Svc me@x.com",
        now=_now_after(path, 1),
        http_get_fn=rec,
    )
    assert rec.calls == []
    assert path.read_text(encoding="utf-8") == "old"


def test_missing_file_downloads_and_writes_file_and_etag(tmp_path):
    path = tmp_path / "company_tickers.json"
    rec = _Recorder(resp=_FakeResp(200, text=VALID, headers={"ETag": '"abc"'}))
    refresh_sec_ticker_cik_map(path, _enabled(), user_agent="Svc me@x.com", http_get_fn=rec)
    assert path.read_text(encoding="utf-8") == VALID
    assert (tmp_path / "company_tickers.json.etag").read_text(encoding="utf-8") == '"abc"'
    assert rec.calls[0][1]["User-Agent"] == "Svc me@x.com"  # fair-access UA sent


def test_stale_file_sends_if_none_match_and_304_keeps_file(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text("cached", encoding="utf-8")
    (tmp_path / "company_tickers.json.etag").write_text('"abc"', encoding="utf-8")
    rec = _Recorder(resp=_FakeResp(304))
    refresh_sec_ticker_cik_map(
        path,
        _enabled(max_age_hours=168),
        user_agent="Svc me@x.com",
        now=_now_after(path, 200),
        http_get_fn=rec,
    )
    assert rec.calls[0][1]["If-None-Match"] == '"abc"'
    assert path.read_text(encoding="utf-8") == "cached"


def test_304_resets_ttl_so_next_build_skips_request(tmp_path):
    # A 304 keeps the cached file AND refreshes its mtime, so the TTL gate suppresses
    # the NEXT build's request — no repeated 304 storms against SEC fair-access.
    path = tmp_path / "company_tickers.json"
    path.write_text("cached", encoding="utf-8")
    (tmp_path / "company_tickers.json.etag").write_text('"abc"', encoding="utf-8")
    rec = _Recorder(resp=_FakeResp(304))
    refresh_sec_ticker_cik_map(
        path,
        _enabled(max_age_hours=168),
        user_agent="Svc me@x.com",
        now=_now_after(path, 200),
        http_get_fn=rec,
    )
    assert len(rec.calls) == 1  # was stale -> one conditional request
    rec2 = _Recorder(exc=AssertionError("304 must reset TTL; next build should skip"))
    refresh_sec_ticker_cik_map(
        path,
        _enabled(max_age_hours=168),
        user_agent="Svc me@x.com",
        now=_now_after(path, 1),  # shortly after the 304 touched mtime -> fresh
        http_get_fn=rec2,
    )
    assert rec2.calls == []


def test_download_failure_keeps_existing_file(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text("cached", encoding="utf-8")
    rec = _Recorder(exc=FetchError("boom"))
    refresh_sec_ticker_cik_map(
        path,
        _enabled(max_age_hours=168),
        user_agent="Svc me@x.com",
        now=_now_after(path, 200),
        http_get_fn=rec,
    )
    assert path.read_text(encoding="utf-8") == "cached"  # unchanged, no crash


def test_non_object_json_is_not_adopted(tmp_path):
    path = tmp_path / "company_tickers.json"
    path.write_text("cached", encoding="utf-8")
    rec = _Recorder(resp=_FakeResp(200, text="[1, 2, 3]"))  # valid JSON, but not an object
    refresh_sec_ticker_cik_map(
        path,
        _enabled(max_age_hours=168),
        user_agent="Svc me@x.com",
        now=_now_after(path, 200),
        http_get_fn=rec,
    )
    assert path.read_text(encoding="utf-8") == "cached"  # not overwritten


def test_invalid_entry_download_is_not_adopted(tmp_path):
    # A JSON object whose entries fail the loader's validation (here: missing cik_str)
    # must NOT overwrite the existing good cache. The download is validated through the
    # canonical loader before adopt; the temp file is cleaned up on rejection.
    path = tmp_path / "company_tickers.json"
    path.write_text("cached", encoding="utf-8")
    rec = _Recorder(resp=_FakeResp(200, text='{"0": {"ticker": "AAPL"}}'))
    refresh_sec_ticker_cik_map(
        path,
        _enabled(max_age_hours=168),
        user_agent="Svc me@x.com",
        now=_now_after(path, 200),
        http_get_fn=rec,
    )
    assert path.read_text(encoding="utf-8") == "cached"  # good cache preserved
    assert not (tmp_path / "company_tickers.json.tmp").exists()  # temp cleaned up
