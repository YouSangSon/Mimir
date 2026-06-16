from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RssCatalogSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
