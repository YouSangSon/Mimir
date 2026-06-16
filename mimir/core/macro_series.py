from __future__ import annotations

from dataclasses import dataclass

from mimir.core.source import Cadence


@dataclass(frozen=True)
class EcosSeriesSpec:
    stat_code: str
    cycle: str
    item_code: str

    @property
    def symbol(self) -> str:
        return f"{self.stat_code}.{self.item_code}"


@dataclass(frozen=True)
class MacroSeriesMeta:
    symbol: str
    cadence: Cadence
    is_rate_series: bool = False


_FRED_SERIES: tuple[MacroSeriesMeta, ...] = (
    MacroSeriesMeta("DGS10", Cadence.DAILY, is_rate_series=True),
    MacroSeriesMeta("FEDFUNDS", Cadence.MONTHLY, is_rate_series=True),
    MacroSeriesMeta("CPIAUCSL", Cadence.MONTHLY),
)

_ECOS_SERIES: tuple[EcosSeriesSpec, ...] = (
    EcosSeriesSpec(stat_code="722Y001", cycle="M", item_code="0101000"),
)

_ECOS_SERIES_META: tuple[MacroSeriesMeta, ...] = (
    MacroSeriesMeta(_ECOS_SERIES[0].symbol, Cadence.MONTHLY, is_rate_series=True),
)

DEFAULT_MACRO_RATE_SERIES: frozenset[str] = frozenset(
    series.symbol
    for series in (*_FRED_SERIES, *_ECOS_SERIES_META)
    if series.is_rate_series
)


def default_fred_series() -> list[str]:
    return [series.symbol for series in _FRED_SERIES]


def default_ecos_series_specs() -> list[EcosSeriesSpec]:
    return list(_ECOS_SERIES)


def default_macro_rate_series() -> list[str]:
    return [
        series.symbol
        for series in (*_FRED_SERIES, *_ECOS_SERIES_META)
        if series.is_rate_series
    ]


def macro_series_cadences() -> dict[str, Cadence]:
    return {series.symbol: series.cadence for series in (*_FRED_SERIES, *_ECOS_SERIES_META)}
