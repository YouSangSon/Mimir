import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from mimir.sources.config import SourcesConfig, parse_sources_config
from mimir.sources.ecos import EcosSeries
from mimir.sources.rss import RssFeed
from mimir.sources.rss_catalog import RssCatalogSelection, SecCompanyFilingFeed


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


def test_rss_feed_symbol_parses_from_config():
    raw = {
        "sources": {
            "rss": {
                "feeds": [
                    {
                        "url": "https://x/feed.rss",
                        "publisher": "Example",
                        "market": "US",
                        "symbol": " AAPL ",
                    }
                ]
            }
        }
    }

    cfg = parse_sources_config(raw)

    assert cfg.rss_feeds == [
        RssFeed(url="https://x/feed.rss", publisher="Example", market="US", symbol="AAPL")
    ]
    assert cfg.rss_feeds[0].symbol == "AAPL"


def test_rss_feed_blank_symbol_raises_validation_error():
    raw = {
        "sources": {
            "rss": {
                "feeds": [
                    {
                        "url": "https://x/feed.rss",
                        "publisher": "Example",
                        "market": "US",
                        "symbol": "   ",
                    }
                ]
            }
        }
    }

    with pytest.raises(ValidationError):
        parse_sources_config(raw)


def test_rss_feed_typo_field_raises_validation_error():
    raw = {
        "sources": {
            "rss": {
                "feeds": [
                    {
                        "url": "https://x/feed.rss",
                        "publisher": "Example",
                        "market": "US",
                        "symbl": "AAPL",
                    }
                ]
            }
        }
    }

    with pytest.raises(ValidationError):
        parse_sources_config(raw)


def test_rss_catalogs_parse_from_config():
    cfg = parse_sources_config(
        {"sources": {"rss": {"catalogs": [{"id": "sec_press_releases"}]}}}
    )

    assert cfg.rss_catalogs == [RssCatalogSelection(id="sec_press_releases")]
    assert cfg.rss_feeds is None


def test_rss_catalog_typo_field_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config(
            {"sources": {"rss": {"catalogs": [{"idd": "sec_press_releases"}]}}}
        )


def test_rss_sec_company_filings_parse_from_config():
    cfg = parse_sources_config(
        {
            "sources": {
                "rss": {
                    "sec": {
                        "company_filings": [
                            {
                                "cik": "320193",
                                "symbol": " AAPL ",
                                "forms": ["10-K", "10-K/A"],
                                "count": 20,
                                "owner": "include",
                            }
                        ]
                    }
                }
            }
        }
    )

    assert cfg.rss_sec_company_filings == [
        SecCompanyFilingFeed(
            cik="0000320193",
            symbol="AAPL",
            forms=["10-K", "10-K/A"],
            count=20,
            owner="include",
        )
    ]


def test_rss_sec_company_filings_ticker_parses_from_config():
    cfg = parse_sources_config(
        {
            "sources": {
                "rss": {
                    "sec": {
                        "company_filings": [
                            {
                                "ticker": " aapl ",
                                "symbol": " AAPL ",
                                "forms": ["10-K"],
                            }
                        ]
                    }
                }
            }
        }
    )

    assert cfg.rss_sec_company_filings == [
        SecCompanyFilingFeed(ticker="AAPL", symbol="AAPL", forms=["10-K"])
    ]


def test_rss_sec_ticker_cik_map_path_parses_from_config():
    cfg = parse_sources_config(
        {
            "sources": {
                "rss": {
                    "sec": {
                        "ticker_cik_map_path": "company_tickers.json",
                        "company_filings": [{"ticker": "AAPL"}],
                    }
                }
            }
        }
    )

    assert str(cfg.rss_sec_ticker_cik_map_path) == "company_tickers.json"


def test_rss_sec_ticker_cik_map_path_rejects_blank_value():
    with pytest.raises(ValidationError):
        parse_sources_config(
            {"sources": {"rss": {"sec": {"ticker_cik_map_path": " "}}}}
        )


def test_rss_sec_company_filings_accept_unquoted_numeric_cik():
    cfg = parse_sources_config(
        {"sources": {"rss": {"sec": {"company_filings": [{"cik": 320193}]}}}}
    )

    assert cfg.rss_sec_company_filings == [
        SecCompanyFilingFeed(cik="0000320193")
    ]


def test_rss_sec_company_filings_typo_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config(
            {"sources": {"rss": {"sec": {"company_filingz": [{"cik": "320193"}]}}}}
        )


def test_rss_sec_company_filings_bad_owner_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config(
            {
                "sources": {
                    "rss": {
                        "sec": {
                            "company_filings": [
                                {"cik": "320193", "owner": "everything"}
                            ]
                        }
                    }
                }
            }
        )


@pytest.mark.parametrize("bad_count", [9, 101])
def test_rss_sec_company_filings_bad_count_raises_validation_error(bad_count: int):
    with pytest.raises(ValidationError):
        parse_sources_config(
            {
                "sources": {
                    "rss": {
                        "sec": {
                            "company_filings": [
                                {"cik": "320193", "count": bad_count}
                            ]
                        }
                    }
                }
            }
        )


def test_partial_block_only_configures_present_source():
    cfg = parse_sources_config({"sources": {"fred": {"series": ["X"]}}})
    assert cfg.fred_series == ["X"]
    assert cfg.ecos_series is None  # absent block -> None -> code default
    assert cfg.rss_feeds is None


def test_sources_plugins_namespace_parses_mapping():
    cfg = parse_sources_config(
        {
            "sources": {
                "plugins": {
                    "acme_news": {
                        "base_url": "https://x",
                        "limit": 10,
                    }
                }
            }
        }
    )

    assert cfg.plugin_settings == {"acme_news": {"base_url": "https://x", "limit": 10}}


def test_sources_plugins_namespace_rejects_non_mapping_plugin_config():
    with pytest.raises(ValidationError):
        parse_sources_config({"sources": {"plugins": {"acme_news": "https://x"}}})


def test_plugin_config_returns_copy_and_empty_default():
    cfg = SourcesConfig(plugin_settings={"acme_news": {"limit": 10}})

    plugin_cfg = cfg.plugin_config("acme_news")
    plugin_cfg["limit"] = 99

    assert cfg.plugin_config("acme_news") == {"limit": 10}
    assert cfg.plugin_config("missing") == {}


def test_parse_plugin_config_validates_with_pydantic_model():
    class AcmeConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")
        base_url: str
        limit: int

    cfg = SourcesConfig(plugin_settings={"acme_news": {"base_url": "https://x", "limit": 10}})

    parsed = cfg.parse_plugin_config("acme_news", AcmeConfig)

    assert parsed == AcmeConfig(base_url="https://x", limit=10)


def test_parse_plugin_config_rejects_plugin_schema_drift():
    class AcmeConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")
        base_url: str

    cfg = SourcesConfig(
        plugin_settings={"acme_news": {"base_url": "https://x", "base_urll": "typo"}}
    )

    with pytest.raises(ValidationError):
        cfg.parse_plugin_config("acme_news", AcmeConfig)


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


def test_llm_sentiment_quoted_false_parses_as_false():
    cfg = parse_sources_config({"llm_sentiment_enabled": "false"})
    assert cfg.llm_sentiment_enabled is False


def test_llm_sentiment_bad_headline_cap_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config({"llm_sentiment_max_headlines": "nope"})


@pytest.mark.parametrize("bad_cap", [0, -1, 51])
def test_llm_sentiment_max_headlines_rejects_unsafe_bounds(bad_cap: int):
    with pytest.raises(ValidationError):
        parse_sources_config({"llm_sentiment_max_headlines": bad_cap})


@pytest.mark.parametrize("good_cap", [1, 50])
def test_llm_sentiment_max_headlines_accepts_safe_bounds(good_cap: int):
    cfg = parse_sources_config({"llm_sentiment_max_headlines": good_cap})

    assert cfg.llm_sentiment_max_headlines == good_cap


def test_sources_config_direct_model_rejects_unsafe_llm_cap():
    with pytest.raises(ValidationError):
        SourcesConfig(llm_sentiment_max_headlines=0)


def test_analysis_macro_regime_rate_series_parses_from_config():
    cfg = parse_sources_config({"analysis": {"macro_regime": {"rate_series": ["T10Y2Y"]}}})
    assert cfg.macro_regime_rate_series == ["T10Y2Y"]


def test_analysis_macro_regime_typo_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config({"analysis": {"macro_regime": {"rate_seriez": ["T10Y2Y"]}}})


def test_analysis_news_aliases_parse_from_config():
    cfg = parse_sources_config(
        {"analysis": {"news": {"aliases": {"AAPL": ["Apple", "Apple Inc."]}}}}
    )
    assert cfg.news_aliases == {"AAPL": ["Apple", "Apple Inc."]}


def test_analysis_news_use_default_aliases_parse_from_config():
    cfg = parse_sources_config({"analysis": {"news": {"use_default_aliases": False}}})

    assert cfg.use_default_news_aliases is False


def test_analysis_news_use_default_aliases_quoted_false_parses_as_false():
    cfg = parse_sources_config({"analysis": {"news": {"use_default_aliases": "false"}}})

    assert cfg.use_default_news_aliases is False


def test_analysis_news_use_default_aliases_typo_raises():
    with pytest.raises(ValidationError):
        parse_sources_config({"analysis": {"news": {"use_defaults_aliases": False}}})


def test_analysis_news_alias_typo_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config({"analysis": {"news": {"aliasez": {"AAPL": ["Apple"]}}}})


def test_analysis_news_alias_value_must_be_list():
    with pytest.raises(ValidationError):
        parse_sources_config({"analysis": {"news": {"aliases": {"AAPL": "Apple"}}}})


def test_analysis_top_level_typo_raises_validation_error():
    with pytest.raises(ValidationError):
        parse_sources_config({"analysys": {"macro_regime": {"rate_series": ["T10Y2Y"]}}})
