import logging

from mimir.core.builder import build_sources
from mimir.settings import Settings
from mimir.sources.config import SourcesConfig
from mimir.sources.ecos import DEFAULT_SERIES as ECOS_DEFAULT_SERIES
from mimir.sources.ecos import EcosSource
from mimir.sources.fred import DEFAULT_SERIES as FRED_DEFAULT_SERIES
from mimir.sources.fred import FredSource
from mimir.sources.rss import DEFAULT_FEEDS as RSS_DEFAULT_FEEDS
from mimir.sources.rss import RssFeed, RssSource


def _by_id(sources):
    return {s.meta.id: s for s in sources}


def test_builder_includes_keyless_sources():
    # SEC EDGAR (UA only) and RSS (official feeds) work with no secrets.
    sources = build_sources(Settings.from_env({}))
    ids = {s.meta.id for s in sources}
    assert "sec_edgar" in ids
    assert "rss" in ids


def test_builder_skips_key_gated_sources_and_logs(caplog):
    with caplog.at_level(logging.WARNING):
        sources = build_sources(Settings.from_env({}))
    ids = {s.meta.id for s in sources}
    for gated in ("stooq", "dart", "fred", "ecos"):
        assert gated not in ids
    messages = " ".join(r.message.lower() for r in caplog.records)
    for gated in ("stooq", "dart", "fred", "ecos"):
        assert gated in messages  # skips are logged, not silent


def test_builder_includes_stooq_with_key():
    sources = build_sources(Settings.from_env({"STOOQ_API_KEY": "abc"}))
    assert "stooq" in {s.meta.id for s in sources}


def test_builder_includes_dart_with_key():
    sources = build_sources(Settings.from_env({"DART_API_KEY": "abc"}))
    assert "dart" in {s.meta.id for s in sources}


def test_builder_includes_macro_sources_with_keys():
    sources = build_sources(Settings.from_env({"FRED_API_KEY": "a", "ECOS_API_KEY": "b"}))
    ids = {s.meta.id for s in sources}
    assert "fred" in ids
    assert "ecos" in ids


# --- config-driven extensibility ---


def test_no_config_carries_defaults():
    # Invariant 1: absent config -> each source uses exactly its DEFAULT_*.
    settings = Settings.from_env({"FRED_API_KEY": "a", "ECOS_API_KEY": "b"})
    by_id = _by_id(build_sources(settings))
    assert isinstance(by_id["fred"], FredSource)
    assert by_id["fred"]._series == FRED_DEFAULT_SERIES
    assert isinstance(by_id["ecos"], EcosSource)
    assert by_id["ecos"]._series == ECOS_DEFAULT_SERIES
    assert isinstance(by_id["rss"], RssSource)
    assert by_id["rss"]._feeds == RSS_DEFAULT_FEEDS


def test_explicit_empty_config_still_carries_defaults():
    # Invariant 1: SourcesConfig() (all None) is equivalent to no config.
    settings = Settings.from_env({"FRED_API_KEY": "a", "ECOS_API_KEY": "b"})
    by_id = _by_id(build_sources(settings, SourcesConfig()))
    assert by_id["fred"]._series == FRED_DEFAULT_SERIES
    assert by_id["ecos"]._series == ECOS_DEFAULT_SERIES
    assert by_id["rss"]._feeds == RSS_DEFAULT_FEEDS


def test_config_overrides_fred_series():
    settings = Settings.from_env({"FRED_API_KEY": "a", "ECOS_API_KEY": "b"})
    cfg = SourcesConfig(fred_series=["X"])
    by_id = _by_id(build_sources(settings, cfg))
    assert by_id["fred"]._series == ["X"]
    # Unconfigured sources keep their defaults.
    assert by_id["ecos"]._series == ECOS_DEFAULT_SERIES
    assert by_id["rss"]._feeds == RSS_DEFAULT_FEEDS


def test_config_overrides_rss_feeds():
    settings = Settings.from_env({})
    feed = RssFeed(url="https://x/feed.rss", publisher="P", market="US")
    by_id = _by_id(build_sources(settings, SourcesConfig(rss_feeds=[feed])))
    assert by_id["rss"]._feeds == [feed]
