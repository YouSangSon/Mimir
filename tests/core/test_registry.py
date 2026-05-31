from mimir.core.registry import Registry
from mimir.core.source import Cadence, Dataset, LegalStatus, Market, RateLimit, SourceMeta


class _FakeSource:
    def __init__(self, meta: SourceMeta) -> None:
        self.meta = meta

    def fetch(self, ctx):
        return []


def _meta(id_: str, cadence: Cadence, legal: LegalStatus) -> SourceMeta:
    return SourceMeta(
        id=id_,
        market=Market.US,
        dataset=Dataset.PRICES,
        cadence=cadence,
        legal_status=legal,
        rate_limit=RateLimit(),
    )


def test_due_filters_by_cadence():
    daily = _FakeSource(_meta("a", Cadence.DAILY, LegalStatus.OFFICIAL))
    weekly = _FakeSource(_meta("b", Cadence.WEEKLY, LegalStatus.OFFICIAL))
    reg = Registry([daily, weekly])
    assert [s.meta.id for s in reg.due(Cadence.DAILY)] == ["a"]


def test_gray_source_excluded_when_disabled():
    official = _FakeSource(_meta("a", Cadence.DAILY, LegalStatus.OFFICIAL))
    gray = _FakeSource(_meta("pykrx", Cadence.DAILY, LegalStatus.GRAY))
    reg = Registry([official, gray], gray_enabled=False)
    assert [s.meta.id for s in reg.due(Cadence.DAILY)] == ["a"]


def test_explicitly_disabled_id_excluded():
    a = _FakeSource(_meta("a", Cadence.DAILY, LegalStatus.OFFICIAL))
    b = _FakeSource(_meta("b", Cadence.DAILY, LegalStatus.OFFICIAL))
    reg = Registry([a, b], disabled_ids={"b"})
    assert [s.meta.id for s in reg.due(Cadence.DAILY)] == ["a"]
