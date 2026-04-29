"""Pydantic schemas for Stores + Supermarket prices."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.domain.store import Store, SupermarketPrice

NonEmptyStr = Annotated[str, Field(min_length=1, max_length=200)]


class StoreBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NonEmptyStr
    location: str | None = Field(default=None, max_length=400)
    is_primary: bool = False


class StoreCreate(StoreBase):
    pass


class StoreRead(StoreBase):
    id: UUID

    @classmethod
    def from_domain(cls, s: Store) -> StoreRead:
        return cls(id=s.id, name=s.name, location=s.location, is_primary=s.is_primary)


class StoreList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[StoreRead]
    total: int


class PriceBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: UUID
    pack_size: float = Field(gt=0)
    pack_price: float = Field(ge=0)


class PriceUpsert(PriceBase):
    pass


class PriceRead(PriceBase):
    id: UUID
    store_id: UUID
    updated_at: datetime | None = None

    @classmethod
    def from_domain(cls, p: SupermarketPrice) -> PriceRead:
        return cls(
            id=p.id,
            store_id=p.store_id,
            component_id=p.component_id,
            pack_size=p.pack_size,
            pack_price=p.pack_price,
            updated_at=p.updated_at,
        )


class PriceList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PriceRead]
    total: int


__all__ = [
    "PriceBase",
    "PriceList",
    "PriceRead",
    "PriceUpsert",
    "StoreBase",
    "StoreCreate",
    "StoreList",
    "StoreRead",
]
