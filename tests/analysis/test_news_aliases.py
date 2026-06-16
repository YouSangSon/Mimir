import pytest

from mimir.analysis.news_aliases import DEFAULT_NEWS_ALIASES, merge_news_aliases


def test_merge_news_aliases_includes_defaults_and_user_aliases():
    aliases = merge_news_aliases({"AAPL": ["Apple", "Cupertino company"]})

    assert aliases["AAPL"] == ("Apple", "Apple Inc.", "Cupertino company")
    assert aliases["MSFT"] == ("Microsoft", "Microsoft Corp.")


def test_merge_news_aliases_can_disable_defaults():
    aliases = merge_news_aliases(
        {"AAPL": ["Cupertino company"]},
        include_defaults=False,
    )

    assert aliases == {"AAPL": ("Cupertino company",)}


def test_default_news_alias_dataset_is_conservative():
    all_terms = {term.casefold() for terms in DEFAULT_NEWS_ALIASES.values() for term in terms}

    assert "a" not in all_terms
    assert "on" not in all_terms
    assert "meta" not in all_terms


def test_merge_news_aliases_deduplicates_case_insensitively_and_drops_blanks():
    aliases = merge_news_aliases({"MSFT": ["microsoft", "", "Azure", "azure"]})

    assert aliases["MSFT"] == ("Microsoft", "Microsoft Corp.", "Azure")


def test_merge_news_aliases_rejects_scalar_string_alias_values():
    with pytest.raises(TypeError, match="must be an iterable of strings"):
        merge_news_aliases({"AAPL": "Apple"})
