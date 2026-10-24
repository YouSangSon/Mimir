"""Source evidence snapshots; structural completeness is not legal verification."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Annotated, Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Permission = Literal["store", "analyze", "commercial", "redistribute", "publish_derived"]
REQUIRED_PERMISSIONS: tuple[Permission, ...] = (
    "analyze", "commercial", "publish_derived", "redistribute", "store",
)


class ProvenanceError(ValueError):
    pass


def public_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        raise ValueError("provenance URL is invalid") from None
    sensitive = {"key", "api_key", "apikey", "token", "access_token", "secret", "password"}
    if (
        parsed.scheme not in {"https", "http"} or not parsed.hostname
        or parsed.username or parsed.password
        or any(c.isspace() or c in '<>"\\' for c in value)
        or sensitive.intersection(key.lower() for key in parse_qs(parsed.query))
    ):
        raise ValueError("provenance URLs must be HTTP(S) without credentials")
    return value


class UsageRights(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", revalidate_instances="always")

    target: Text
    author: Text
    rights_holder: Text
    source_url: Text
    terms_urls: tuple[str, ...] = Field(min_length=1)
    checked_on: date
    permissions: tuple[Permission, ...]
    basis: Text
    attribution: Text

    _source_url = field_validator("source_url")(public_url)

    @field_validator("terms_urls")
    @classmethod
    def _terms(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(public_url(value) for value in values)

    @field_validator("permissions")
    @classmethod
    def _permissions(cls, values: tuple[Permission, ...]) -> tuple[Permission, ...]:
        if set(values) != set(REQUIRED_PERMISSIONS):
            raise ValueError("provenance must document all intended storage and output uses")
        return REQUIRED_PERMISSIONS


class SourceProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    target: Text
    publisher: Text
    source_url: Text
    origin: Literal["ecos", "rss_manual", "rss_builtin"]
    route: Text
    rights: UsageRights | None = None

    _source_url = field_validator("source_url")(public_url)

    @model_validator(mode="after")
    def _bound_rights(self) -> SourceProvenance:
        if self.origin == "rss_builtin":
            if self.rights is not None:
                raise ValueError("built-in RSS discovery is not rights approval")
        elif self.rights is None or self.rights.target != self.target:
            raise ValueError("source provenance requires matching rights evidence")
        return self


BOK_BASE_RATE_RIGHTS = UsageRights(
    target="ecos:722Y001:M:0101000",
    author="Bank of Korea", rights_holder="Bank of Korea",
    source_url="https://ecos.bok.or.kr/api/StatisticItemList/sample/json/kr/1/10/722Y001/",
    terms_urls=(
        "https://ecos.bok.or.kr/", "https://ecos.bok.or.kr/api/",
        "https://www.bok.or.kr/portal/main/contents.do?menuNo=200228",
    ),
    checked_on=date(2026, 10, 25), permissions=REQUIRED_PERMISSIONS,
    basis=(
        "Exact monthly policy-rate item identified by ECOS metadata; BOK determines its base rate. "
        "ECOS guideline permits commercial use, processing and redistribution of BOK-authored "
        "statistics with attribution. API terms incorporate the guideline; copyright policy "
        "requires disclosure of processing. This does not cover third-party-authored series."
    ),
    attribution="Source: Bank of Korea ECOS (한국은행 경제통계시스템).",
)


def require_rights(target: str, rights: UsageRights | None) -> UsageRights:
    if rights is None:
        raise ProvenanceError("source provenance requires target-specific usage evidence")
    rights = UsageRights.model_validate(rights)
    if rights.target != target:
        # Never echo operator input: URLs/config can contain secret values.
        raise ProvenanceError("source provenance requires target-specific usage evidence")
    return rights


def ecos_provenance(
    stat_code: str, cycle: str, item_code: str, rights: UsageRights | None,
) -> SourceProvenance:
    target = f"ecos:{stat_code}:{cycle}:{item_code}"
    if rights is None and target == BOK_BASE_RATE_RIGHTS.target:
        rights = BOK_BASE_RATE_RIGHTS
    rights = require_rights(target, rights)
    return SourceProvenance(
        target=target, publisher="Bank of Korea ECOS", source_url=rights.source_url,
        origin="ecos", route="StatisticSearch", rights=rights,
    )


def unique_provenance(items: Iterable[SourceProvenance | None]) -> list[SourceProvenance]:
    return list(dict.fromkeys(item for item in items if item is not None))
