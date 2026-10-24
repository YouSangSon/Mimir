"""Explicit synthetic evidence for executable test sources, never real usage approval."""
from datetime import date

from mimir.core.provenance import UsageRights


def synthetic_rights(target: str) -> UsageRights:
    return UsageRights(
        target=target, author="Synthetic fixture author", rights_holder="Synthetic fixture owner",
        source_url="https://example.test/fixture", terms_urls=("https://example.test/terms",),
        checked_on=date(2026, 1, 1),
        permissions=("store", "analyze", "commercial", "redistribute", "publish_derived"),
        basis="Synthetic fixture permission; no permission for any real publisher is asserted.",
        attribution="Source: synthetic test fixture, not observed investment data.",
    )
