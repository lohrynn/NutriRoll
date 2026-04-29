"""Pydantic schemas for the shopping-list endpoint."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.api.schemas.component import ComponentRead
from nutriroll.domain.shopping import ShoppingList, ShoppingListItem


class BuildShoppingListRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_ids: list[UUID] = Field(min_length=1)
    portions: int = Field(ge=1, le=20)
    store_id: UUID | None = None
    use_pantry: bool = True


class ShoppingListItemRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component: ComponentRead
    quantity_needed: float
    quantity_available_in_pantry: float
    quantity_to_buy: float
    pack_size: float | None = None
    pack_price: float | None = None
    packs_to_buy: int | None = None
    line_price: float | None = None

    @classmethod
    def from_domain(cls, item: ShoppingListItem) -> ShoppingListItemRead:
        return cls(
            component=ComponentRead.from_domain(item.component),
            quantity_needed=item.quantity_needed,
            quantity_available_in_pantry=item.quantity_available_in_pantry,
            quantity_to_buy=item.quantity_to_buy,
            pack_size=item.pack_size,
            pack_price=item.pack_price,
            packs_to_buy=item.packs_to_buy,
            line_price=item.line_price,
        )


class ShoppingListRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ShoppingListItemRead]
    portions: int
    total_price: float
    has_missing_prices: bool

    @classmethod
    def from_domain(cls, sl: ShoppingList) -> ShoppingListRead:
        return cls(
            items=[ShoppingListItemRead.from_domain(i) for i in sl.items],
            portions=sl.portions,
            total_price=sl.total_price,
            has_missing_prices=sl.has_missing_prices,
        )


__all__ = [
    "BuildShoppingListRequest",
    "ShoppingListItemRead",
    "ShoppingListRead",
]
