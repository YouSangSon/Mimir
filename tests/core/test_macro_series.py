from mimir.analysis.signals.macro_regime import RATE_SERIES
from mimir.core.macro_series import (
    DEFAULT_MACRO_RATE_SERIES,
    default_ecos_series_specs,
    default_macro_rate_series,
    macro_series_cadences,
)
from mimir.core.source import Cadence
from mimir.doctor.expectations import MACRO_SERIES_CADENCE
from mimir.sources.ecos import DEFAULT_SERIES as ECOS_DEFAULT_SERIES


def test_default_ecos_series_comes_from_macro_metadata():
    assert [(s.stat_code, s.cycle, s.item_code) for s in ECOS_DEFAULT_SERIES] == [
        (s.stat_code, s.cycle, s.item_code) for s in default_ecos_series_specs()
    ]


def test_doctor_cadence_comes_from_macro_metadata():
    assert MACRO_SERIES_CADENCE == macro_series_cadences()
    assert MACRO_SERIES_CADENCE["722Y001.0101000"] is Cadence.MONTHLY


def test_default_rate_series_excludes_non_rate_macro_series():
    assert default_macro_rate_series() == ["722Y001.0101000"]
    rate_series = set(default_macro_rate_series())
    assert RATE_SERIES is DEFAULT_MACRO_RATE_SERIES
    assert set(RATE_SERIES) == rate_series
    assert rate_series == {"722Y001.0101000"}
