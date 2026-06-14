from __future__ import annotations

from mimir.core.source import Cadence, Dataset

# §4.1 — explicit expected coverage. NEVER derive this from build_sources(): its
# if-ladder drops sources when API keys are absent, which would make the doctor
# silently skip the very gap it exists to catch (a missing dataset is a finding,
# not a row to skip). HISTORICAL is excluded from freshness (backfill / irregular).
EXPECTED_DATASETS: dict[Dataset, Cadence] = {
    Dataset.PRICES: Cadence.DAILY,
    Dataset.FILINGS: Cadence.DAILY,  # business-day filing flow
    Dataset.MACRO: Cadence.DAILY,  # dataset floor; per-series overrides below (§4.4)
    Dataset.NEWS: Cadence.DAILY,
    Dataset.INSIGHTS: Cadence.DAILY,  # pipeline emits every run
}

# §4.4 — macro freshness is PER-SERIES, not per-dataset. FRED emits DGS10 (daily)
# AND CPIAUCSL (monthly) into the same `macro` dataset, so a single dataset-level
# rule false-alarms CPI daily. Never use SourceMeta.cadence as the basis.
MACRO_SERIES_CADENCE: dict[str, Cadence] = {
    "DGS10": Cadence.DAILY,
    "FEDFUNDS": Cadence.MONTHLY,  # monthly average release
    "CPIAUCSL": Cadence.MONTHLY,  # would false-alarm daily if treated as DAILY
    "722Y001.0101000": Cadence.MONTHLY,  # BOK base rate (ECOS symbol format)
}
# Unregistered macro series fall back to the loosest cadence (silence over false alarm).
DEFAULT_MACRO_CADENCE = Cadence.MONTHLY

# NB: EXPECTED_PAYLOAD_KEYS / check_payload_schema were removed in INC2 (A4): payload
# schema drift is now caught at the storage boundary by the typed Record.payload
# union, so a shallow key-existence check here would be dead code (a drifted payload
# can no longer be stored or read).
