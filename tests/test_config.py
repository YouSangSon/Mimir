from pathlib import Path

import pytest
from pydantic import ValidationError

from mimir.config import (
    load_sources_config,
    load_validated_sources_config,
    load_watchlist,
    load_yaml,
)


def test_load_watchlist_returns_lists(tmp_path: Path):
    (tmp_path / "watchlist.yaml").write_text("us:\n  - AAPL\nkr: []\n", encoding="utf-8")
    assert load_watchlist(tmp_path) == {"us": ["AAPL"], "kr": []}


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


def test_load_yaml_missing_returns_empty(tmp_path: Path):
    assert load_yaml(tmp_path / "nope.yaml") == {}
