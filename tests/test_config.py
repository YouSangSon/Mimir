from pathlib import Path

import pytest
from pydantic import ValidationError

from mimir.config import (
    WatchlistConfigError,
    load_sources_config,
    load_validated_sources_config,
    load_watchlist,
    load_yaml,
)


def test_load_watchlist_returns_lists(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text("us:\n  - ' AAPL '\nkr: []\n", encoding="utf-8")
    assert load_watchlist(tmp_path) == {"us": ["AAPL"], "kr": []}


def test_load_watchlist_rejects_scalar_market_value(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text("us: AAPL\nkr: []\n", encoding="utf-8")

    with pytest.raises(WatchlistConfigError) as exc_info:
        load_watchlist(tmp_path)

    message = str(exc_info.value)
    assert "watchlist.yaml" in message
    assert "us" in message


def test_load_watchlist_rejects_non_mapping_top_level(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text("- AAPL\n", encoding="utf-8")

    with pytest.raises(WatchlistConfigError) as exc_info:
        load_watchlist(tmp_path)

    assert "watchlist.yaml" in str(exc_info.value)


def test_load_watchlist_rejects_non_string_symbol(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text("us: [123]\nkr: []\n", encoding="utf-8")

    with pytest.raises(WatchlistConfigError) as exc_info:
        load_watchlist(tmp_path)

    assert "watchlist.yaml" in str(exc_info.value)


def test_load_watchlist_strips_symbols_and_rejects_blank_symbol(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text(
        "us:\n  - ' AAPL '\nkr:\n  - '   '\n",
        encoding="utf-8",
    )

    with pytest.raises(WatchlistConfigError) as exc_info:
        load_watchlist(tmp_path)

    assert "watchlist.yaml" in str(exc_info.value)


def test_load_watchlist_missing_file_falls_back(tmp_path: Path):
    assert load_watchlist(tmp_path) == {"us": [], "kr": []}


def test_load_sources_config(tmp_path: Path):
    (tmp_path / "sources.yaml").write_text(
        "gray_enabled: false\ndisabled_ids: [dart]\n", encoding="utf-8"
    )
    cfg = load_sources_config(tmp_path)
    assert cfg["gray_enabled"] is False
    assert cfg["disabled_ids"] == ["dart"]


def test_load_validated_sources_config_resolves_relative_sec_map_path(tmp_path: Path):
    (tmp_path / "sources.yaml").write_text(
        """
        sources:
          rss:
            sec:
              ticker_cik_map_path: company_tickers.json
              company_filings:
                - { ticker: AAPL }
        """,
        encoding="utf-8",
    )

    raw, cfg = load_validated_sources_config(tmp_path)

    expected = tmp_path / "company_tickers.json"
    assert raw["sources"]["rss"]["sec"]["ticker_cik_map_path"] == str(expected)
    assert cfg.rss_sec_ticker_cik_map_path == expected


def test_load_validated_sources_config_preserves_absolute_sec_map_path(tmp_path: Path):
    abs_map = tmp_path / "abs" / "company_tickers.json"
    (tmp_path / "sources.yaml").write_text(
        f"""
        sources:
          rss:
            sec:
              ticker_cik_map_path: {abs_map}
              company_filings:
                - {{ ticker: AAPL }}
        """,
        encoding="utf-8",
    )

    raw, cfg = load_validated_sources_config(tmp_path)

    # An absolute path must pass through unchanged, never re-rooted under config_dir.
    assert raw["sources"]["rss"]["sec"]["ticker_cik_map_path"] == str(abs_map)
    assert cfg.rss_sec_ticker_cik_map_path == abs_map


def test_load_validated_sources_config_bad_sec_map_path_raises_validation_error(
    tmp_path: Path,
):
    (tmp_path / "sources.yaml").write_text(
        """
        sources:
          rss:
            sec:
              ticker_cik_map_path: []
              company_filings:
                - { ticker: AAPL }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_validated_sources_config(tmp_path)


def test_load_validated_sources_config_rejects_non_mapping_top_level_yaml(
    tmp_path: Path,
):
    (tmp_path / "sources.yaml").write_text("- not-a-mapping\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_validated_sources_config(tmp_path)


def test_load_yaml_missing_returns_empty(tmp_path: Path):
    assert load_yaml(tmp_path / "nope.yaml") == {}
