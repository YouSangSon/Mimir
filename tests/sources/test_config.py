import pytest
from pydantic import ValidationError

from mimir.sources.config import SourcesConfig, parse_sources_config
from mimir.sources.ecos import EcosSeries
from mimir.sources.rss import RssFeed


def test_empty_dict_yields_all_none():
    cfg = parse_sources_config({})
    assert cfg == SourcesConfig()
    assert cfg.fred_series is None
    assert cfg.ecos_series is None
    assert cfg.rss_feeds is None


def test_absent_sources_block_yields_all_none():
    # The full config dict (gray_enabled/disabled_ids/lang) but no `sources:` block.
    cfg = parse_sources_config({"gray_enabled": True, "disabled_ids": [], "lang": "en"})
    assert cfg == SourcesConfig()


def test_full_block_parses_typed_models():
    raw = {
        "sources": {
            "fred": {"series": ["DGS10", "FEDFUNDS"]},
            "ecos": {"series": [{"stat_code": "722Y001", "cycle": "M", "item_code": "0101000"}]},
            "rss": {"feeds": [{"url": "https://x/feed.rss", "publisher": "SEC", "market": "US"}]},
        }
    }
    cfg = parse_sources_config(raw)
    assert cfg.fred_series == ["DGS10", "FEDFUNDS"]
    assert cfg.ecos_series == [EcosSeries(stat_code="722Y001", cycle="M", item_code="0101000")]
    assert cfg.rss_feeds == [RssFeed(url="https://x/feed.rss", publisher="SEC", market="US")]


def test_partial_block_only_configures_present_source():
    cfg = parse_sources_config({"sources": {"fred": {"series": ["X"]}}})
    assert cfg.fred_series == ["X"]
    assert cfg.ecos_series is None  # absent block -> None -> code default
    assert cfg.rss_feeds is None


def test_explicit_empty_list_is_distinct_from_none_at_parse_layer():
    # At the model layer, `[]` (a deliberate "zero series" choice) stays distinct
    # from None ("not configured"). NOTE: this distinction is only preserved up to
    # SourcesConfig; the source constructors do `series or list(DEFAULT_*)`, so an
    # empty list collapses to the code default end-to-end. Honoring `[]` through the
    # constructor is out of scope for the config-wiring task (it touches fetch code).
    cfg = parse_sources_config({"sources": {"fred": {"series": []}}})
    assert cfg.fred_series == []
    assert cfg.fred_series is not None


def test_fred_series_not_a_list_raises():
    with pytest.raises(ValidationError):
        parse_sources_config({"sources": {"fred": {"series": "DGS10"}}})


def test_ecos_series_item_missing_stat_code_raises():
    raw = {"sources": {"ecos": {"series": [{"cycle": "M", "item_code": "0101"}]}}}
    with pytest.raises(ValidationError):
        parse_sources_config(raw)


def test_non_dict_source_block_raises_validation_error():
    # `fred: "DGS10"` (a string where a {series: [...]} mapping is expected) must
    # fail fast with a clear ValidationError, never a raw AttributeError.
    with pytest.raises(ValidationError):
        parse_sources_config({"sources": {"fred": "x"}})


def test_non_dict_sources_block_raises_validation_error():
    # `sources: "x"` (a string where a mapping is expected) is malformed config.
    with pytest.raises(ValidationError):
        parse_sources_config({"sources": "x"})


def test_typo_in_source_field_key_raises_validation_error():
    # `sources.fred.serie` (typo for `series`) must not be silently ignored.
    with pytest.raises(ValidationError):
        parse_sources_config({"sources": {"fred": {"serie": ["X"]}}})


def test_typo_in_source_block_name_raises_validation_error():
    # `sources.fed` (typo for `fred`) must not be silently ignored.
    with pytest.raises(ValidationError):
        parse_sources_config({"sources": {"fed": {}}})


@pytest.mark.parametrize("bad", [0, False, [], ""])
def test_falsy_non_mapping_sources_block_raises(bad: object):
    # A falsy-but-present `sources:` (0/false/[]/"") is malformed and must raise —
    # it must NOT collapse to defaults the way an absent/None block does.
    with pytest.raises(ValidationError):
        parse_sources_config({"sources": bad})


def test_none_sources_block_yields_all_none():
    # `sources:` with no value (YAML null) is absent -> defaults preserved.
    cfg = parse_sources_config({"sources": None})
    assert cfg.fred_series is None
    assert cfg.ecos_series is None
    assert cfg.rss_feeds is None


def test_llm_sentiment_defaults_off():
    # INC5: the paid LLM signal is off by default and capped at 50 headlines.
    cfg = parse_sources_config({})
    assert cfg.llm_sentiment_enabled is False
    assert cfg.llm_sentiment_max_headlines == 50


def test_llm_sentiment_toggle_parsed_from_top_level_keys():
    raw = {"llm_sentiment_enabled": True, "llm_sentiment_max_headlines": 10}
    cfg = parse_sources_config(raw)
    assert cfg.llm_sentiment_enabled is True
    assert cfg.llm_sentiment_max_headlines == 10
