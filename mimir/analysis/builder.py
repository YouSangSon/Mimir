from __future__ import annotations

from mimir.analysis.signals.base import Signal
from mimir.analysis.signals.filing_event import FilingEventSignal
from mimir.analysis.signals.macro_regime import MacroRegimeSignal
from mimir.analysis.signals.news_volume import NewsVolumeSignal
from mimir.analysis.signals.price_momentum import PriceMomentumSignal


def build_signals() -> list[Signal]:
    return [
        FilingEventSignal(),
        NewsVolumeSignal(),
        PriceMomentumSignal(),
        MacroRegimeSignal(),
    ]
