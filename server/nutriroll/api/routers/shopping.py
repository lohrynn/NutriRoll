"""Shopping list endpoint: POST /v1/shopping-list."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.shopping import (
    BuildShoppingListRequest,
    ShoppingListRead,
)
from nutriroll.db.repositories.components import ComponentRepository
from nutriroll.db.repositories.pantry import PantryRepository
from nutriroll.db.repositories.stores import StoresRepository
from nutriroll.db.session import get_session
from nutriroll.domain.component import Component
from nutriroll.domain.pantry import PantryItem
from nutriroll.domain.shopping import (
    aggregate_demand_for_bowl,
    build_shopping_list,
)
from nutriroll.domain.store import SupermarketPrice

router = APIRouter(prefix="/v1/shopping-list", tags=["shopping"])


@router.post(
    "",
    response_model=ShoppingListRead,
    summary="Build a shopping list from a bowl + portion count",
)
async def build_list(
    payload: BuildShoppingListRequest,
    session: AsyncSession = Depends(get_session),
) -> ShoppingListRead:
    components_repo = ComponentRepository(session)
    components: list[Component] = []
    for cid in payload.component_ids:
        c = await components_repo.get(cid)
        if c is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "component_not_found", "component_id": str(cid)},
            )
        components.append(c)

    demands = aggregate_demand_for_bowl(components, payload.portions)

    prices: dict[UUID, SupermarketPrice] = {}
    if payload.store_id is not None:
        stores_repo = StoresRepository(session)
        if await stores_repo.get_store(payload.store_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "store_not_found", "store_id": str(payload.store_id)},
            )
        for cid in demands:
            price = await stores_repo.get_price(payload.store_id, cid)
            if price is not None:
                prices[cid] = price

    pantry_items: list[PantryItem] = []
    if payload.use_pantry:
        pantry_items = await PantryRepository(session).list()

    sl = build_shopping_list(demands, portions=payload.portions, prices=prices, pantry=pantry_items)
    return ShoppingListRead.from_domain(sl)


__all__ = ["router"]
