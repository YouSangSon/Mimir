import logging

from mimir.core.builder import build_sources
from mimir.settings import Settings


def test_builder_includes_sec_edgar_without_any_key():
    # SEC EDGAR needs only a User-Agent, so it is the one source that works
    # out of the box with no secrets configured.
    sources = build_sources(Settings.from_env({}))
    ids = {s.meta.id for s in sources}
    assert "sec_edgar" in ids


def test_builder_skips_key_gated_sources_and_logs(caplog):
    with caplog.at_level(logging.WARNING):
        sources = build_sources(Settings.from_env({}))
    ids = {s.meta.id for s in sources}
    assert "stooq" not in ids
    assert "dart" not in ids
    messages = " ".join(r.message.lower() for r in caplog.records)
    assert "stooq" in messages  # skips are logged, not silent
    assert "dart" in messages


def test_builder_includes_stooq_with_key():
    sources = build_sources(Settings.from_env({"STOOQ_API_KEY": "abc"}))
    assert "stooq" in {s.meta.id for s in sources}


def test_builder_includes_dart_with_key():
    sources = build_sources(Settings.from_env({"DART_API_KEY": "abc"}))
    assert "dart" in {s.meta.id for s in sources}
