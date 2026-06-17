import logging

import pytest
from pydantic import BaseModel, ConfigDict

from mimir.core.builder import (
    BUILTIN_SOURCE_SPECS,
    SourceSpec,
    _build_sources_from_specs,
    _load_entry_point_source_specs,
    _validate_unique_source_ids,
    build_sources,
)
from mimir.core.source import Cadence, Dataset, LegalStatus, Market, RateLimit, SourceMeta
from mimir.settings import Settings
from mimir.sources.config import SourcesConfig
from mimir.sources.ecos import DEFAULT_SERIES as ECOS_DEFAULT_SERIES
from mimir.sources.ecos import EcosSource
from mimir.sources.fred import DEFAULT_SERIES as FRED_DEFAULT_SERIES
from mimir.sources.fred import FredSource
from mimir.sources.rss import DEFAULT_FEEDS as RSS_DEFAULT_FEEDS
from mimir.sources.rss import RssFeed, RssSource
from mimir.sources.rss_catalog import RssCatalogSelection, SecCompanyFilingFeed
from mimir.sources.sec_edgar import SecEdgarSource


class _FakeEntryPoint:
    def __init__(self, name, value=None, error: Exception | None = None):
        self.name = name
        self._value = value
        self._error = error

    def load(self):
        if self._error:
            raise self._error
        return self._value


class _PluginSource:
    meta = SourceMeta(
        id="plugin_news",
        market=Market.GLOBAL,
        dataset=Dataset.NEWS,
        cadence=Cadence.HOURLY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1.0),
    )

    def fetch(self, ctx):
        return []


class _ConfiguredPluginSource:
    meta = SourceMeta(
        id="plugin_news",
        market=Market.GLOBAL,
        dataset=Dataset.NEWS,
        cadence=Cadence.HOURLY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1.0),
    )

    def __init__(self, base_url: str):
        self.base_url = base_url

    def fetch(self, ctx):
        return []


class _PluginMacroSource:
    meta = SourceMeta(
        id="plugin_macro",
        market=Market.GLOBAL,
        dataset=Dataset.MACRO,
        cadence=Cadence.DAILY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1.0),
    )

    def fetch(self, ctx):
        return []


class _MismatchedPluginSource:
    meta = SourceMeta(
        id="plugin_news",
        market=Market.GLOBAL,
        dataset=Dataset.NEWS,
        cadence=Cadence.HOURLY,
        legal_status=LegalStatus.OFFICIAL,
        rate_limit=RateLimit(max_per_second=1.0),
    )

    def fetch(self, ctx):
        return []


def _patch_entry_points(monkeypatch, entry_points):
    monkeypatch.setattr(
        "mimir.core.builder.importlib.metadata.entry_points",
        lambda group=None: entry_points if group == "mimir.sources" else [],
    )


def _by_id(sources):
    return {s.meta.id: s for s in sources}


def test_builtin_source_specs_keep_existing_order():
    assert [spec.id for spec in BUILTIN_SOURCE_SPECS] == [
        "sec_edgar",
        "rss",
        "stooq",
        "dart",
        "fred",
        "ecos",
        "pykrx",
    ]


def test_builtin_source_specs_expose_static_metadata_for_preflight_manifest():
    metas = {spec.id: spec.meta for spec in BUILTIN_SOURCE_SPECS}

    assert all(meta is not None for meta in metas.values())
    assert metas["stooq"] is not None
    assert metas["stooq"].id == "stooq"
    assert metas["stooq"].cadence == Cadence.DAILY
    assert metas["stooq"].requires_secret == "STOOQ_API_KEY"


def test_duplicate_source_spec_ids_raise_value_error():
    specs = (
        SourceSpec(
            "sec_edgar",
            lambda settings, cfg: SecEdgarSource(user_agent=settings.sec_user_agent),
        ),
        SourceSpec(
            "sec_edgar",
            lambda settings, cfg: SecEdgarSource(user_agent=settings.sec_user_agent),
        ),
    )

    with pytest.raises(ValueError, match="duplicate source id"):
        _validate_unique_source_ids(specs)


def test_build_sources_from_specs_skips_secret_gated_sources(caplog):
    def fail_if_called(settings, cfg):
        raise AssertionError("secret-gated source factory should not be called")

    specs = (
        SourceSpec(
            "stooq",
            fail_if_called,
            required_secret_attr="stooq_api_key",
            required_secret_name="STOOQ_API_KEY",
        ),
    )

    with caplog.at_level(logging.WARNING):
        sources = _build_sources_from_specs(Settings.from_env({}), SourcesConfig(), specs)

    assert sources == []
    assert "skipping source 'stooq': STOOQ_API_KEY is not set" in " ".join(
        r.message for r in caplog.records
    )


def test_build_sources_from_specs_rejects_source_id_mismatch():
    specs = (
        SourceSpec(
            "stooq",
            lambda settings, cfg: SecEdgarSource(user_agent=settings.sec_user_agent),
        ),
    )

    with pytest.raises(ValueError, match="source spec id 'stooq' built source id 'sec_edgar'"):
        _build_sources_from_specs(Settings.from_env({}), SourcesConfig(), specs)


def test_load_entry_point_source_specs_accepts_single_spec(monkeypatch):
    spec = SourceSpec("plugin_news", lambda settings, cfg: _PluginSource())
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("plugin_news", spec)])

    assert _load_entry_point_source_specs() == (spec,)


def test_load_entry_point_source_specs_accepts_sequence(monkeypatch):
    news_spec = SourceSpec("plugin_news", lambda settings, cfg: _PluginSource())
    macro_spec = SourceSpec("plugin_macro", lambda settings, cfg: _PluginMacroSource())
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("plugin_bundle", (news_spec, macro_spec))])

    assert _load_entry_point_source_specs() == (news_spec, macro_spec)


def test_entry_point_source_specs_are_loaded_in_name_order(monkeypatch):
    alpha_spec = SourceSpec("alpha_plugin", lambda settings, cfg: _PluginSource())
    zulu_spec = SourceSpec("zulu_plugin", lambda settings, cfg: _PluginSource())
    _patch_entry_points(
        monkeypatch,
        [
            _FakeEntryPoint("zulu_plugin", zulu_spec),
            _FakeEntryPoint("alpha_plugin", alpha_spec),
        ],
    )

    assert [spec.id for spec in _load_entry_point_source_specs()] == [
        "alpha_plugin",
        "zulu_plugin",
    ]


def test_entry_point_source_spec_id_must_match_entry_point_name(monkeypatch):
    spec = SourceSpec("plugin_b", lambda settings, cfg: _PluginSource())
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("plugin_a", spec)])

    with pytest.raises(ValueError, match="entry point 'plugin_a' loaded source spec 'plugin_b'"):
        _load_entry_point_source_specs()


def test_broken_entry_point_source_spec_is_skipped_and_logged(monkeypatch, caplog):
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("broken", error=RuntimeError("boom"))])

    with caplog.at_level(logging.WARNING):
        assert _load_entry_point_source_specs() == ()

    assert "skipping source plugin 'broken'" in " ".join(r.message for r in caplog.records)


def test_entry_point_wrong_object_type_raises_value_error(monkeypatch):
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("bad", object())])

    with pytest.raises(ValueError, match="entry point 'bad' must load SourceSpec"):
        _load_entry_point_source_specs()


def test_build_sources_includes_entry_point_sources_after_builtins(monkeypatch):
    spec = SourceSpec("plugin_news", lambda settings, cfg: _PluginSource())
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("plugin_news", spec)])
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)

    sources = build_sources(Settings.from_env({}))

    assert [source.meta.id for source in sources] == ["sec_edgar", "rss", "plugin_news"]


def test_build_sources_passes_plugin_namespace_to_factory():
    class PluginConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")
        base_url: str

    def build_plugin(settings, cfg):
        plugin_cfg = cfg.parse_plugin_config("plugin_news", PluginConfig)
        return _ConfiguredPluginSource(base_url=plugin_cfg.base_url)

    specs = (SourceSpec("plugin_news", build_plugin),)
    cfg = SourcesConfig(plugin_settings={"plugin_news": {"base_url": "https://plugin.test"}})

    sources = _build_sources_from_specs(Settings.from_env({}), cfg, specs)

    assert len(sources) == 1
    assert isinstance(sources[0], _ConfiguredPluginSource)
    assert sources[0].base_url == "https://plugin.test"


def test_builder_warns_for_unmatched_plugin_config(caplog):
    cfg = SourcesConfig(plugin_settings={"missing_plugin": {"base_url": "https://x"}})

    with caplog.at_level(logging.WARNING):
        _build_sources_from_specs(Settings.from_env({}), cfg, ())

    assert "source plugin config 'missing_plugin' has no matching source spec" in " ".join(
        r.message for r in caplog.records
    )


def test_builder_warns_when_plugin_namespace_targets_builtin_source(caplog):
    cfg = SourcesConfig(plugin_settings={"rss": {"feeds": []}})

    with caplog.at_level(logging.WARNING):
        _build_sources_from_specs(Settings.from_env({}), cfg, ())

    messages = " ".join(r.message for r in caplog.records)
    assert "source plugin config 'rss' targets built-in source 'rss'" in messages
    assert "use sources.rss instead" in messages


def test_builder_warns_when_plugin_namespace_targets_non_configurable_builtin(caplog):
    cfg = SourcesConfig(plugin_settings={"sec_edgar": {"user_agent": "x"}})

    with caplog.at_level(logging.WARNING):
        _build_sources_from_specs(Settings.from_env({}), cfg, ())

    messages = " ".join(r.message for r in caplog.records)
    assert "source plugin config 'sec_edgar' targets built-in source 'sec_edgar'" in messages
    assert "built-in sources do not read sources.plugins" in messages
    assert "use sources.sec_edgar instead" not in messages


def test_entry_point_duplicate_builtin_source_id_raises_value_error(monkeypatch):
    spec = SourceSpec("rss", lambda settings, cfg: RssSource())
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("rss", spec)])

    with pytest.raises(ValueError, match="duplicate source id"):
        build_sources(Settings.from_env({}))


def test_plugin_source_meta_id_mismatch_uses_existing_guard(monkeypatch):
    spec = SourceSpec("plugin_bad", lambda settings, cfg: _MismatchedPluginSource())
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("plugin_bad", spec)])

    with pytest.raises(
        ValueError,
        match="source spec id 'plugin_bad' built source id 'plugin_news'",
    ):
        build_sources(Settings.from_env({}))


def test_builder_skips_pykrx_when_optional_package_missing(monkeypatch, caplog):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)

    with caplog.at_level(logging.WARNING):
        sources = build_sources(Settings.from_env({}))

    assert "pykrx" not in {s.meta.id for s in sources}
    assert "skipping source 'pykrx'" in " ".join(r.message for r in caplog.records)


def test_builder_includes_pykrx_when_optional_package_is_available(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: object())

    sources = build_sources(Settings.from_env({}))

    assert "pykrx" in {s.meta.id for s in sources}


def test_builder_warns_when_sec_user_agent_has_no_contact_email(caplog):
    with caplog.at_level(logging.WARNING):
        build_sources(Settings.from_env({"MIMIR_SEC_USER_AGENT": "Mimir"}))

    assert "SEC EDGAR may return 403" in " ".join(r.message for r in caplog.records)


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


def test_build_sources_resolves_rss_catalog_feeds(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    cfg = SourcesConfig(rss_catalogs=[RssCatalogSelection(id="sec_press_releases")])

    sources = build_sources(Settings.from_env({}), cfg)
    rss = _by_id(sources)["rss"]

    assert isinstance(rss, RssSource)
    assert rss._feeds == [
        RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        )
    ]


def test_build_sources_resolves_sec_company_filing_feeds(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    cfg = SourcesConfig(
        rss_sec_company_filings=[
            SecCompanyFilingFeed(cik="320193", symbol="AAPL", forms=["10-K/A"])
        ]
    )

    sources = build_sources(
        Settings.from_env({"MIMIR_SEC_USER_AGENT": "Mimir Test test@example.com"}),
        cfg,
    )
    rss = _by_id(sources)["rss"]

    assert isinstance(rss, RssSource)
    assert rss._feeds == [
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=0000320193&type=10-K%2FA&owner=exclude&count=40&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        )
    ]
    assert rss._headers == {"User-Agent": "Mimir Test test@example.com"}


def test_build_sources_resolves_sec_company_filing_feeds_with_ticker(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    cfg = SourcesConfig(
        rss_sec_company_filings=[
            SecCompanyFilingFeed(ticker="aapl", symbol="AAPL", forms=["10-K"])
        ]
    )

    sources = build_sources(
        Settings.from_env({"MIMIR_SEC_USER_AGENT": "Mimir Test test@example.com"}),
        cfg,
    )
    rss = _by_id(sources)["rss"]

    assert isinstance(rss, RssSource)
    assert rss._feeds == [
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=AAPL&type=10-K&owner=exclude&count=40&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        )
    ]
    assert rss._headers == {"User-Agent": "Mimir Test test@example.com"}


def test_build_sources_resolves_sec_company_filing_ticker_with_map(monkeypatch, tmp_path):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    mapping_path = tmp_path / "company_tickers.json"
    mapping_path.write_text(
        '{"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}',
        encoding="utf-8",
    )
    cfg = SourcesConfig(
        rss_sec_ticker_cik_map_path=mapping_path,
        rss_sec_company_filings=[
            SecCompanyFilingFeed(ticker="aapl", symbol="AAPL", forms=["10-K"])
        ],
    )

    sources = build_sources(
        Settings.from_env({"MIMIR_SEC_USER_AGENT": "Mimir Test test@example.com"}),
        cfg,
    )
    rss = _by_id(sources)["rss"]

    assert isinstance(rss, RssSource)
    assert rss._feeds == [
        RssFeed(
            url=(
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=0000320193&type=10-K&owner=exclude&count=40&output=atom"
            ),
            publisher="SEC",
            market="US",
            symbol="AAPL",
        )
    ]


def test_build_sources_combines_rss_catalog_and_manual_feeds(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    manual = RssFeed(
        url="https://example.com/aapl.rss",
        publisher="Example",
        market="US",
        symbol="AAPL",
    )
    cfg = SourcesConfig(
        rss_catalogs=[RssCatalogSelection(id="sec_press_releases")],
        rss_feeds=[manual],
    )

    sources = build_sources(Settings.from_env({}), cfg)
    rss = _by_id(sources)["rss"]

    assert isinstance(rss, RssSource)
    assert rss._feeds == [
        RssFeed(
            url="https://www.sec.gov/news/pressreleases.rss",
            publisher="SEC",
            market="US",
        ),
        manual,
    ]


def test_build_sources_combines_catalog_sec_and_manual_feeds(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    manual = RssFeed(
        url="https://example.com/aapl.rss",
        publisher="Example",
        market="US",
        symbol="AAPL",
    )
    cfg = SourcesConfig(
        rss_catalogs=[RssCatalogSelection(id="sec_press_releases")],
        rss_sec_company_filings=[SecCompanyFilingFeed(cik="320193", symbol="AAPL")],
        rss_feeds=[manual],
    )

    sources = build_sources(Settings.from_env({}), cfg)
    rss = _by_id(sources)["rss"]

    assert [feed.url for feed in rss._feeds] == [
        "https://www.sec.gov/news/pressreleases.rss",
        (
            "https://www.sec.gov/cgi-bin/browse-edgar?"
            "action=getcompany&CIK=0000320193&owner=exclude&count=40&output=atom"
        ),
        "https://example.com/aapl.rss",
    ]


def test_build_sources_rejects_duplicate_rss_catalog_and_manual_feed(monkeypatch):
    monkeypatch.setattr("mimir.core.builder.importlib.util.find_spec", lambda name: None)
    manual = RssFeed(
        url="https://www.sec.gov/news/pressreleases.rss",
        publisher="SEC",
        market="US",
    )
    cfg = SourcesConfig(
        rss_catalogs=[RssCatalogSelection(id="sec_press_releases")],
        rss_feeds=[manual],
    )

    with pytest.raises(ValueError, match="duplicate RSS feed"):
        build_sources(Settings.from_env({}), cfg)
