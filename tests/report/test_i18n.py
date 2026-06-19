import string

from mimir.report.i18n import DEFAULT_LANG, LANGS, STRINGS, t


def _placeholders(template: str) -> set[str]:
    return {field for _, field, _, _ in string.Formatter().parse(template) if field}


def test_i18n_all_langs_have_identical_keys():
    # A key present in `en` but missing in `ko`/`zh` would silently fall back to
    # English, quietly breaking the trilingual report contract with no error.
    en_keys = set(STRINGS[DEFAULT_LANG])
    for lang in LANGS:
        assert set(STRINGS[lang]) == en_keys, f"{lang} key set differs from {DEFAULT_LANG}"


def test_i18n_format_placeholders_match_across_langs():
    # Each translation of a key must use the same {placeholders} as English, or
    # `t(key, lang, **fmt)` would drop a value or raise KeyError at render time.
    for key, en_text in STRINGS[DEFAULT_LANG].items():
        expected = _placeholders(en_text)
        for lang in LANGS:
            got = _placeholders(STRINGS[lang][key])
            assert got == expected, f"{lang}/{key} placeholders {got} != {expected}"


def test_t_falls_back_to_english_then_to_key():
    # The documented fallback contract: unknown lang -> English, unknown key -> the
    # key itself. Guards against a silent empty/None render for missing strings.
    assert t("direction_bullish", "fr") == STRINGS[DEFAULT_LANG]["direction_bullish"]
    assert t("nonexistent_key_xyz", "en") == "nonexistent_key_xyz"
