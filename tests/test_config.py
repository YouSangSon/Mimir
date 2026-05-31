from pathlib import Path

from mimir.config import load_sources_config, load_watchlist, load_yaml


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


def test_load_yaml_missing_returns_empty(tmp_path: Path):
    assert load_yaml(tmp_path / "nope.yaml") == {}
