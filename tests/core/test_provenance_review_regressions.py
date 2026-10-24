import json
from datetime import UTC, datetime

import pytest

from mimir import backfill
from mimir.analysis.schema import Insight, to_record
from mimir.analysis.signals.base import SignalDirection, SignalResult
from mimir.core import builder
from mimir.core.source import Dataset, Market
from mimir.dashboard import run_dashboard
from mimir.deliver import run_deliver
from mimir.evaluation.engine import EvaluationEngine
from mimir.evaluation.schema import BucketStat
from mimir.report.daily_report import build_report_html
from mimir.settings import Settings
from mimir.sources.config import RuntimeSourcesConfig, SourcesConfig, TickerCikMapRefresh
from mimir.sources.rss import RssFeed, RssSource
from mimir.sources.rss_catalog import RssCatalogSelection, resolve_rss_catalogs
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.paths import partition_path
from mimir.storage.reader import DataReader
from tests.provenance import synthetic_rights

NOW = datetime(2026, 5, 31, tzinfo=UTC)


@pytest.mark.parametrize("update", [{"permissions": ()}, {"attribution": ""}])
def test_unvalidated_rights_copy_is_rejected_before_side_effects(tmp_path, monkeypatch, update):
    url = "https://example.test/feed"
    feed = RssFeed(url=url, publisher="Test", market="US", provenance=synthetic_rights(url))
    feed.provenance = feed.provenance.model_copy(update=update)
    cfg = SourcesConfig(rss_feeds=[feed])
    cfg.rss_sec_ticker_cik_map_path = tmp_path / "map.json"
    cfg.rss_sec_ticker_cik_map_refresh = TickerCikMapRefresh(enabled=True)
    monkeypatch.setattr(
        builder, "refresh_sec_ticker_cik_map", lambda *a, **kw: pytest.fail("refresh")
    )
    monkeypatch.setattr(builder, "load_source_specs", lambda *a: pytest.fail("plugins"))
    with pytest.raises(ValueError, match="provenance"):
        builder.build_sources(Settings.from_env({}), cfg)
    assert not cfg.rss_sec_ticker_cik_map_path.exists()


@pytest.mark.parametrize("copy", [False, True])
def test_builtin_marker_does_not_authorize_a_changed_feed_url(copy):
    feed = resolve_rss_catalogs([RssCatalogSelection(id="sec_press_releases")])[0]
    if copy:
        feed = feed.model_copy(update={"url": "https://example.test/unreviewed"})
    else:
        feed.url = "https://example.test/unreviewed"
    with pytest.raises(ValueError, match="provenance"):
        RssSource(feeds=[feed])


def test_explicit_manual_evidence_on_builtin_copy_is_preserved():
    feed = resolve_rss_catalogs([RssCatalogSelection(id="sec_press_releases")])[0]
    feed.provenance = synthetic_rights(feed.url)
    snapshot = RssSource(feeds=[feed])._feeds[0].snapshot()
    assert snapshot.origin == "rss_manual"
    assert snapshot.rights == feed.provenance


def test_typed_backfill_rejects_evidence_before_settings_or_plugins(tmp_path, monkeypatch):
    runtime = RuntimeSourcesConfig(source_config=SourcesConfig(rss_feeds=[
        RssFeed(url="https://example.test/feed", publisher="Test", market="US"),
    ]))
    monkeypatch.setattr(backfill.Settings, "from_env", lambda *a, **kw: pytest.fail("settings"))
    monkeypatch.setattr(backfill, "load_source_specs", lambda *a: pytest.fail("plugins"))
    with pytest.raises(ValueError, match="provenance"):
        backfill.run_backfill(
            source_id="rss", since=NOW.date(), env={}, watchlist={"us": [], "kr": []},
            sources_config=runtime, data_root=tmp_path / "data", now=NOW,
        )
    assert not (tmp_path / "data").exists()


def _legacy_insight():
    return Insight(
        symbol="005930", market=Market.KR, as_of=NOW.date(), direction=SignalDirection.BULLISH,
        stars=3, confidence=.4, reasons=["LEGACY_UNPROVEN_RESULT"],
        signals=[SignalResult(signal="macro_regime", direction=SignalDirection.BULLISH,
                              strength=.3, confidence=.4, reason="legacy source")],
    )


def test_legacy_derived_values_are_readable_but_not_republished_or_evaluated(tmp_path):
    root = tmp_path / "data"
    record = to_record(_legacy_insight(), NOW)
    raw = json.loads(record.model_dump_json())
    raw["payload"]["signals"][0].pop("attributions", None)
    path = partition_path(Dataset.INSIGHTS, NOW.date(), root)
    path.parent.mkdir(parents=True)
    original = json.dumps(raw) + "\n"
    path.write_text(original)
    store = JsonlStore(root=root)
    reader = DataReader(store)
    assert len(reader.read(Dataset.INSIGHTS)) == 1
    report = EvaluationEngine(reader, store).run(NOW.date(), NOW)
    assert report.insights_evaluated == 0 and report.buckets == []
    result = run_deliver(
        cadence="daily", env={}, data_root=root, reports_root=tmp_path / "reports",
        as_of=NOW.date(),
    )
    assert result["insights"] == 0 and result["sent"] is False
    assert "LEGACY_UNPROVEN_RESULT" not in result["report"].read_text()
    dashboard = run_dashboard(
        data_root=root, reports_root=tmp_path / "reports", watchlist={"us": [], "kr": []},
        as_of=NOW.date(), now=NOW,
    )
    assert "LEGACY_UNPROVEN_RESULT" not in dashboard.read_text()
    assert path.read_text() == original


def test_serialization_does_not_promote_absent_source_fields_to_explicit_empty():
    legacy = _legacy_insight().signals[0]
    assert "attributions" not in legacy.model_dump(mode="json")
    bucket = BucketStat(dimension="per_signal", key="macro_regime", market=Market.KR, horizons=[])
    assert "attributions" not in bucket.model_dump(mode="json")
    assert "macro_regime" not in build_report_html([], NOW.date(), evaluation=[bucket])


def test_explicit_empty_new_signal_evidence_preserves_out_of_scope_plugin_inputs():
    new = _legacy_insight().signals[0].model_copy(update={"attributions": []})
    insight = _legacy_insight().model_copy(update={"signals": [new]})
    assert "LEGACY_UNPROVEN_RESULT" in build_report_html([insight], NOW.date())


def test_legacy_unrelated_signal_buckets_remain_visible():
    buckets = [
        BucketStat(dimension=dimension, key=key, market=Market.US, horizons=[])
        for dimension, key in [
            ("per_signal", "price_momentum"), ("per_signal", "external_plugin"),
            ("per_signal", "macro_regime"), ("per_direction", "LEGACY_AGGREGATE"),
        ]
    ]
    rendered = build_report_html([], NOW.date(), evaluation=buckets)
    assert "price_momentum" in rendered and "external_plugin" in rendered
    assert "macro_regime" not in rendered and "LEGACY_AGGREGATE" not in rendered
