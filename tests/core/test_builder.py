import logging

from mimir.core.builder import build_sources
from mimir.settings import Settings


def test_builder_includes_keyless_sources():
    sources = build_sources(Settings.from_env({}))
    ids = {s.meta.id for s in sources}
    assert "stooq" in ids
    assert "sec_edgar" in ids


def test_builder_skips_dart_without_key(caplog):
    with caplog.at_level(logging.WARNING):
        sources = build_sources(Settings.from_env({}))
    assert "dart" not in {s.meta.id for s in sources}
    assert any("dart" in r.message.lower() for r in caplog.records)  # skip is logged, not silent


def test_builder_includes_dart_with_key():
    sources = build_sources(Settings.from_env({"DART_API_KEY": "abc"}))
    assert "dart" in {s.meta.id for s in sources}
