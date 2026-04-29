"""Stores + supermarket prices, mounted at /v1/stores."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.store import (
    PriceList,
    PriceRead,
    PriceUpsert,
    StoreCreate,
    StoreList,
    StoreRead,
)
from nutriroll.db.repositories.components import ComponentRepository
from nutriroll.db.repositories.stores import StoresRepository
from nutriroll.db.session import get_session
from nutriroll.domain.store import Store, SupermarketPrice

router = APIRouter(prefix="/v1/stores", tags=["stores"])


async def _ensure_component(session: AsyncSession, component_id: UUID) -> None:
    found = await ComponentRepository(session).get(component_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "component_not_found", "component_id": str(component_id)},
        )


@router.get("", response_model=StoreList, summary="List stores")
async def list_stores(session: AsyncSession = Depends(get_session)) -> StoreList:
    repo = StoresRepository(session)
    items = await repo.list_stores()
    return StoreList(items=[StoreRead.from_domain(s) for s in items], total=len(items))


@router.post(
    "",
    response_model=StoreRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a store",
)
async def create_store(
    payload: StoreCreate, session: AsyncSession = Depends(get_session)
) -> StoreRead:
    repo = StoresRepository(session)
    store = Store(
        id=uuid4(),
        name=payload.name.strip(),
        location=payload.location,
        is_primary=payload.is_primary,
    )
    try:
        created = await repo.create_store(store)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "store_name_taken", "name": store.name},
        ) from exc
    return StoreRead.from_domain(created)


@router.put(
    "/{store_id}",
    response_model=StoreRead,
    summary="Replace a store",
)
async def update_store(
    store_id: UUID,
    payload: StoreCreate,
    session: AsyncSession = Depends(get_session),
) -> StoreRead:
    repo = StoresRepository(session)
    store = Store(
        id=store_id,
        name=payload.name.strip(),
        location=payload.location,
        is_primary=payload.is_primary,
    )
    updated = await repo.update_store(store)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return StoreRead.from_domain(updated)


@router.delete(
    "/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a store and its prices",
)
async def delete_store(store_id: UUID, session: AsyncSession = Depends(get_session)) -> Response:
    repo = StoresRepository(session)
    deleted = await repo.delete_store(store_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{store_id}/prices",
    response_model=PriceList,
    summary="List prices for a store",
)
async def list_prices(store_id: UUID, session: AsyncSession = Depends(get_session)) -> PriceList:
    repo = StoresRepository(session)
    if await repo.get_store(store_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    items = await repo.list_prices(store_id)
    return PriceList(items=[PriceRead.from_domain(p) for p in items], total=len(items))


@router.put(
    "/{store_id}/prices",
    response_model=PriceRead,
    summary="Upsert a price (one per (store, component))",
)
async def upsert_price(
    store_id: UUID,
    payload: PriceUpsert,
    session: AsyncSession = Depends(get_session),
) -> PriceRead:
    repo = StoresRepository(session)
    if await repo.get_store(store_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await _ensure_component(session, payload.component_id)
    price = SupermarketPrice(
        id=uuid4(),
        store_id=store_id,
        component_id=payload.component_id,
        pack_size=payload.pack_size,
        pack_price=payload.pack_price,
    )
    saved = await repo.upsert_price(price)
    return PriceRead.from_domain(saved)


@router.delete(
    "/{store_id}/prices/{price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a price",
)
async def delete_price(
    store_id: UUID,
    price_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    repo = StoresRepository(session)
    if await repo.get_store(store_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    deleted = await repo.delete_price(price_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
