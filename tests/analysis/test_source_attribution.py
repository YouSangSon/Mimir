"""Lightweight source/JSONL/signal units using synthetic records and fake HTTP."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from mimir.analysis.schema import Insight, to_record
from mimir.analysis.signals.base import SignalDirection
from mimir.analysis.signals.llm_sentiment import HeadlineVerdict, LlmSentimentSignal
from mimir.analysis.signals.macro_regime import MacroRegimeSignal
from mimir.analysis.signals.news_volume import NewsVolumeSignal
from mimir.core.normalize import normalize
from mimir.core.payloads import news_payload
from mimir.core.source import Dataset, FetchContext, Market
from mimir.deliver import run_deliver
from mimir.evaluation.engine import EvaluationEngine
from mimir.evaluation.metrics import Obs, evaluate_bucket
from mimir.historical.series import Bar
from mimir.report.daily_report import build_report_html
from mimir.report.dashboard import build_dashboard_html
from mimir.report.digest import build_digest
from mimir.sources.ecos import EcosSeries, EcosSource
from mimir.sources.rss import RssFeed, RssSource
from mimir.sources.rss_catalog import (
    RssCatalogSelection,
    SecCompanyFilingFeed,
    resolve_rss_catalogs,
    resolve_sec_company_filing_feeds,
)
from mimir.storage.jsonl_store import JsonlStore
from mimir.storage.reader import DataReader
from tests.provenance import synthetic_rights
from tests.report.test_dashboard import _report

NOW = datetime(2026, 5, 31, tzinfo=UTC)


def _feed(name):
    url = f"https://example.test/{name}"
    return RssFeed(
        url=url, publisher=name, market="US", symbol="AAPL", provenance=synthetic_rights(url),
    )


def _news(feed, *, day=NOW, key="article"):
    source = RssSource(feeds=[feed] if feed is not None else None)
    source.get = lambda *a, **kw: SimpleNamespace(text="synthetic")
    source._parse_fn = lambda text: SimpleNamespace(entries=[{
        "title": "AAPL synthetic news", "summary": "", "link": f"https://example.test/{key}",
        "published_parsed": day.timetuple(), "published": day.isoformat(),
    }])
    raw = next(iter(source.fetch(FetchContext(now=day, watchlist={}))))
    return normalize(raw, source.meta, captured_at=day)


def _insight(signal):
    return Insight(
        symbol="AAPL", market=Market.US, as_of=NOW.date(), direction=signal.direction,
        stars=3, confidence=signal.confidence, signals=[signal], reasons=[signal.reason],
    )


@pytest.mark.parametrize("feed", [
    None,
    resolve_rss_catalogs([RssCatalogSelection(id="sec_press_releases")])[0],
    resolve_sec_company_filing_feeds([SecCompanyFilingFeed(ticker="AAPL")])[0],
])
def test_builtin_routes_remain_analyzable_without_becoming_rights_approval(tmp_path, feed):
    store = JsonlStore(root=tmp_path)
    record = _news(feed)
    assert record.idempotency_key == (
        "rss:https://example.test/article"  # no symbol on these built-in selections
    )
    store.append([record])
    signal = NewsVolumeSignal().evaluate("AAPL", Market.US, NOW.date(), DataReader(store))
    assert signal is not None
    assert len(signal.attributions) == 1
    snapshot = signal.attributions[0]
    assert snapshot.origin == "rss_builtin" and snapshot.rights is None
    assert snapshot.source_url == news_payload(record).feed_url
    assert "Rights unverified" in build_digest([_insight(signal)], "daily", NOW.date())


def test_news_baseline_and_capped_classifier_keep_only_actual_input_sources(tmp_path):
    store = JsonlStore(root=tmp_path)
    a, b, base = _feed("today-a"), _feed("today-b"), _feed("baseline")
    store.append([
        _news(a, key="a"), _news(b, key="b"),
        _news(base, day=NOW - timedelta(days=1), key="base"),
    ])
    reader = DataReader(store)
    volume = NewsVolumeSignal().evaluate("AAPL", Market.US, NOW.date(), reader)
    assert volume is not None
    assert [p.publisher for p in volume.attributions] == ["today-a", "today-b", "baseline"]

    class FakeClassifier:
        def classify(self, texts):
            assert len(texts) == 1
            return [
                HeadlineVerdict(direction=SignalDirection.BULLISH, confidence=0.8, rationale="fake")
            ]

    sentiment = LlmSentimentSignal(classifier=FakeClassifier(), max_headlines=1).evaluate(
        "AAPL", Market.US, NOW.date(), reader,
    )
    assert sentiment is not None
    assert sentiment.attributions == [volume.attributions[0]]


def test_default_macro_snapshot_survives_normalization_and_storage(tmp_path):
    store = JsonlStore(root=tmp_path)
    source = EcosSource(api_key="not-used")
    series = EcosSeries(stat_code="722Y001", cycle="M", item_code="0101000")
    for month, value in (("202604", "3.0"), ("202605", "2.5")):
        raw = source._row_to_record(series, {"TIME": month, "DATA_VALUE": value})
        assert raw is not None
        store.append([normalize(raw, source.meta, captured_at=NOW)])
    signal = MacroRegimeSignal().evaluate("005930", Market.KR, NOW.date(), DataReader(store))
    assert signal is not None and signal.direction is SignalDirection.BULLISH
    assert len(signal.attributions) == 1
    assert signal.attributions[0].target == "ecos:722Y001:M:0101000"


def test_saved_source_survives_config_change_and_all_output_renderers_escape_it(tmp_path):
    store = JsonlStore(root=tmp_path / "data")
    feed = _feed("a")
    feed.publisher = "Publisher <A>"
    # Keep URL safe while exercising escaped, user-controlled attribution text.
    feed.url = "https://example.test/a"
    feed.provenance = synthetic_rights(feed.url).model_copy(
        update={"attribution": "Credit <A> & owner"}
    )
    store.append([_news(feed)])
    signal = NewsVolumeSignal().evaluate("AAPL", Market.US, NOW.date(), DataReader(store))
    assert signal is not None
    store.append([to_record(_insight(signal), NOW)])
    feed.publisher = "Publisher B"
    feed.provenance = synthetic_rights(feed.url).model_copy(update={"attribution": "Credit B"})
    result = run_deliver(
        cadence="daily", env={}, data_root=store.root, reports_root=tmp_path / "reports",
        as_of=NOW.date(),
    )
    html = result["report"].read_text()
    assert "Credit &lt;A&gt; &amp; owner" in html and "Credit B" not in html
    saved = Insight.model_validate(DataReader(store).read(Dataset.INSIGHTS)[0].payload)
    digest = build_digest([saved], "daily", NOW.date())
    assert "Credit <A> & owner" in digest and "Credit B" not in digest
    assert "Processed and analyzed by Mimir" in digest
    dashboard = build_dashboard_html(
        doctor_report=_report(), insights=[saved], buckets=[], historical=[], run=None, now=NOW,
    )
    assert "Credit &lt;A&gt; &amp; owner" in dashboard and "Publisher <A>" not in dashboard
    assert build_report_html([saved], NOW.date()).count("Credit &lt;A&gt;") == 1
    # Existing RSS first-write-wins keys do not silently migrate old snapshots.
    assert store.append([_news(feed)]) == 0
    assert (
        news_payload(DataReader(store).read(Dataset.NEWS)[0]).provenance.publisher
        == "Publisher <A>"
    )


def test_evaluation_carries_only_sources_of_contributing_observations():
    a, b = _feed("a").snapshot(), _feed("b").snapshot()
    bars = [Bar(NOW.date() + timedelta(days=i), 100.0 + i, None) for i in range(3)]
    signal = SimpleNamespace(direction=SignalDirection.BULLISH, attributions=[a], signal="macro")
    insight = SimpleNamespace(
        market=Market.US, direction=signal.direction, stars=3, signals=[signal]
    )
    acc = {("per_direction", "bullish", Market.US): [], ("per_star", "3", Market.US): [],
           ("per_signal", "macro", Market.US): []}
    EvaluationEngine._accumulate(acc, insight, bars, 0)
    obs = acc[("per_signal", "macro", Market.US)]
    obs.append(Obs(bars, 2, SignalDirection.BULLISH, (b,)))  # no forward bar
    stat = evaluate_bucket(("per_signal", "macro", Market.US), obs, horizons=(1,), min_n=1)
    assert stat is not None and stat.attributions == [a]
    html = build_report_html([], NOW.date(), evaluation=[stat])
    assert "https://example.test/a" in html and "https://example.test/b" not in html


def test_oversized_digest_is_withheld_instead_of_truncating_attribution(tmp_path, monkeypatch):
    store = JsonlStore(root=tmp_path / "data")
    feed = _feed("long-credit")
    feed.provenance = feed.provenance.model_copy(update={"attribution": "Synthetic credit " * 500})
    store.append([_news(feed)])
    signal = NewsVolumeSignal().evaluate("AAPL", Market.US, NOW.date(), DataReader(store))
    store.append([to_record(_insight(signal), NOW)])
    monkeypatch.setattr(
        "mimir.deliver.send_ping", lambda **kw: pytest.fail("must not send truncated credit")
    )
    result = run_deliver(
        cadence="daily", env={"TELEGRAM_BOT_TOKEN": "fake", "TELEGRAM_CHAT_ID": "fake"},
        data_root=store.root, reports_root=tmp_path / "reports", as_of=NOW.date(),
    )
    assert result["sent"] is False
    assert "Synthetic credit " * 500 in result["report"].read_text()
