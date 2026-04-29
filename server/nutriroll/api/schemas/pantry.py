"""Pydantic schemas for the Pantry HTTP API."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.domain.component import PortionUnit
from nutriroll.domain.pantry import PantryItem


class PantryItemBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: UUID
    quantity: float = Field(ge=0)
    unit: PortionUnit
    opened: bool = False
    expires_at: date | None = None


class PantryItemCreate(PantryItemBase):
    pass


class PantryItemRead(PantryItemBase):
    id: UUID

    @classmethod
    def from_domain(cls, item: PantryItem) -> PantryItemRead:
        return cls(
            id=item.id,
            component_id=item.component_id,
            quantity=item.quantity,
            unit=item.unit,
            opened=item.opened,
            expires_at=item.expires_at,
        )


class PantryList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PantryItemRead]
    total: int


__all__ = ["PantryItemBase", "PantryItemCreate", "PantryItemRead", "PantryList"]
