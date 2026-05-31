import logging

from mimir.core.builder import build_sources
from mimir.settings import Settings


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
