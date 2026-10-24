from datetime import UTC, datetime, timedelta

import pytest

from mimir.analysis.signals.macro_regime import MacroRegimeSignal
from mimir.analysis.signals.news_volume import NewsVolumeSignal
from mimir.core import builder
from mimir.core.source import Dataset, Market
from mimir.settings import Settings
from mimir.sources.config import SourcesConfig, TickerCikMapRefresh, parse_sources_config
from mimir.sources.ecos import EcosSeries, EcosSource
from mimir.sources.rss import RssFeed
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from mimir.storage.schema import Record

NOW = datetime(2026, 5, 31, tzinfo=UTC)


@pytest.mark.parametrize(
    "source,block",
    [
        ("ecos", {"series": [{"stat_code": "722Y001", "cycle": "D", "item_code": "0101000"}]}),
        (
            "rss",
            {"feeds": [{"url": "https://example.test/feed", "publisher": "Test", "market": "US"}]},
        ),
        (
            "rss",
            {
                "feeds": [
                    {
                        "url": "https://www.sec.gov/news/pressreleases.rss",
                        "publisher": "SEC",
                        "market": "US",
                    }
                ]
            },
        ),
    ],
)
def test_manual_sources_require_target_specific_provenance_even_when_disabled(source, block):
    with pytest.raises(ValueError, match="provenance"):
        parse_sources_config({"disabled_ids": [source], "sources": {source: block}})


@pytest.mark.parametrize("source", ["ecos", "rss"])
def test_mutated_typed_config_fails_before_refresh_plugins_or_output(tmp_path, monkeypatch, source):
    cfg = SourcesConfig()
    if source == "ecos":
        cfg.ecos_series = [EcosSeries(stat_code="custom", cycle="M", item_code="1")]
    else:
        cfg.rss_feeds = [RssFeed(url="https://example.test/feed", publisher="Test", market="US")]
    cfg.rss_sec_ticker_cik_map_refresh = TickerCikMapRefresh(enabled=True)
    cfg.rss_sec_ticker_cik_map_path = tmp_path / "map.json"
    monkeypatch.setattr(
        builder, "refresh_sec_ticker_cik_map", lambda *a, **kw: pytest.fail("refresh")
    )
    monkeypatch.setattr(builder, "load_source_specs", lambda *a, **kw: pytest.fail("plugins"))
    with pytest.raises(ValueError, match="provenance"):
        builder.build_sources(Settings.from_env({}), cfg)
    assert not cfg.rss_sec_ticker_cik_map_path.exists()


def test_exact_default_ecos_record_has_bok_rights_snapshot():
    series = EcosSeries(stat_code="722Y001", cycle="M", item_code="0101000")
    raw = EcosSource._row_to_record(series, {"TIME": "202605", "DATA_VALUE": "2.5"})
    assert raw is not None
    snapshot = raw.payload["provenance"]
    assert snapshot["target"] == "ecos:722Y001:M:0101000"
    assert snapshot["rights"]["rights_holder"] == "Bank of Korea"


def test_legacy_ecos_and_rss_remain_readable_but_do_not_gain_new_analysis(tmp_path):
    store = JsonlStore(root=tmp_path)
    records = []
    for index, value in enumerate((3.0, 2.5)):
        records.append(Record(
            source="ecos", dataset=Dataset.MACRO, market=Market.KR,
            symbol="722Y001.0101000", ts=NOW - timedelta(days=30 * (1 - index)),
            captured_at=NOW, idempotency_key=f"legacy-ecos:{index}",
            payload={"stat_code": "722Y001", "item_code": "0101000", "item_name": None,
                     "value": value, "unit": None, "time": "202605"},
        ))
    records.append(Record(
        source="rss", dataset=Dataset.NEWS, market=Market.GLOBAL, symbol="AAPL",
        ts=NOW, captured_at=NOW, idempotency_key="legacy-rss",
        payload={"title": "AAPL news", "url": "https://example.test/article",
                 "publisher": "SEC", "market": "US", "published_at": None, "summary": ""},
    ))
    store.append(records)
    reader = DataReader(store)
    assert len(reader.read(Dataset.NEWS)) == 1
    assert MacroRegimeSignal().evaluate("005930", Market.KR, NOW.date(), reader) is None
    assert NewsVolumeSignal().evaluate("AAPL", Market.US, NOW.date(), reader) is None


@pytest.mark.parametrize("field,value", [
    ("author", " "), ("rights_holder", ""), ("basis", " "), ("attribution", ""),
    ("terms_urls", ()), ("checked_on", "not-a-date"),
    ("permissions", ("store", "analyze", "commercial", "redistribute")),
])
def test_usage_evidence_rejects_incomplete_or_invalid_fields(field, value):
    from mimir.core.provenance import UsageRights
    from tests.provenance import synthetic_rights

    data = synthetic_rights("https://example.test/feed").model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValueError):
        UsageRights.model_validate(data)


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "https://user:password@example.test/feed",
    "https://example.test/feed?token=private", "https://example.test:bad/feed",
    "https://example.test/invalid path",
])
def test_citation_urls_reject_unsafe_or_credential_bearing_values(url):
    from tests.provenance import synthetic_rights

    data = synthetic_rights("https://example.test/feed").model_dump(mode="json")
    data["source_url"] = url
    from mimir.core.provenance import UsageRights

    with pytest.raises(ValueError):
        UsageRights.model_validate(data)


@pytest.mark.parametrize("series", [None, [], [EcosSeries(
    stat_code="722Y001", cycle="M", item_code="0101000",
)]])
def test_default_none_empty_and_exact_explicit_tuple_keep_builtin_behavior(series):
    source = EcosSource(api_key="unused", series=series)
    assert [(s.stat_code, s.cycle, s.item_code) for s in source._series] == [
        ("722Y001", "M", "0101000")
    ]


@pytest.mark.parametrize("marker", ["builtin", "_builtin_route", "route"])
def test_manual_yaml_cannot_claim_a_builtin_discovery_path(marker):
    from pydantic import ValidationError

    feed = {"url": "https://www.sec.gov/news/pressreleases.rss", "publisher": "SEC", "market": "US"}
    feed[marker] = "catalog:sec_press_releases"
    with pytest.raises(ValidationError):
        parse_sources_config({"sources": {"rss": {"feeds": [feed]}}})


def test_wrong_target_evidence_is_rejected_before_building():
    from tests.provenance import synthetic_rights

    raw = {"sources": {"rss": {"feeds": [{
        "url": "https://example.test/a", "publisher": "A", "market": "US",
        "provenance": synthetic_rights("https://example.test/b").model_dump(mode="json"),
    }]}}}
    with pytest.raises(ValueError, match="provenance"):
        parse_sources_config(raw)


def test_cli_schema_diagnostic_never_echoes_provenance_input(tmp_path, monkeypatch, capsys):
    import yaml

    from mimir import collect
    from tests.provenance import synthetic_rights

    raw = synthetic_rights("https://example.test/feed").model_dump(mode="json")
    raw["permissions"] = ["PRIVATE_CREDENTIAL_SENTINEL"]
    (tmp_path / "watchlist.yaml").write_text("us: []\nkr: []\n")
    (tmp_path / "sources.yaml").write_text(yaml.safe_dump({"sources": {"rss": {"feeds": [{
        "url": "https://example.test/feed", "publisher": "Test", "market": "US",
        "provenance": raw,
    }]}}}))
    monkeypatch.setattr(collect.Settings, "from_env", lambda *a, **kw: pytest.fail("settings"))
    assert collect.main(["--cadence", "daily", "--config-dir", str(tmp_path)]) == 1
    error = capsys.readouterr().err
    assert error.startswith("[mimir] invalid sources.yaml:")
    assert "permissions" in error and "PRIVATE_CREDENTIAL_SENTINEL" not in error
