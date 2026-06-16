import logging

import pytest

from mimir.core.builder import (
    BUILTIN_SOURCE_SPECS,
    SourceSpec,
    _build_sources_from_specs,
    _validate_unique_source_ids,
    build_sources,
)
from mimir.settings import Settings
from mimir.sources.config import SourcesConfig
from mimir.sources.ecos import DEFAULT_SERIES as ECOS_DEFAULT_SERIES
from mimir.sources.ecos import EcosSource
from mimir.sources.fred import DEFAULT_SERIES as FRED_DEFAULT_SERIES
from mimir.sources.fred import FredSource
from mimir.sources.rss import DEFAULT_FEEDS as RSS_DEFAULT_FEEDS
from mimir.sources.rss import RssFeed, RssSource
from mimir.sources.sec_edgar import SecEdgarSource


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
