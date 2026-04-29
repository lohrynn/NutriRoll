"""Pantry CRUD endpoints, mounted at /v1/pantry."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.pantry import (
    PantryItemCreate,
    PantryItemRead,
    PantryList,
)
from nutriroll.db.repositories.components import ComponentRepository
from nutriroll.db.repositories.pantry import PantryRepository
from nutriroll.db.session import get_session
from nutriroll.domain.pantry import PantryItem

router = APIRouter(prefix="/v1/pantry", tags=["pantry"])


def _to_domain(payload: PantryItemCreate, *, item_id: UUID) -> PantryItem:
    return PantryItem(
        id=item_id,
        component_id=payload.component_id,
        quantity=payload.quantity,
        unit=payload.unit,
        opened=payload.opened,
        expires_at=payload.expires_at,
    )


async def _ensure_component_exists(session: AsyncSession, component_id: UUID) -> None:
    """Foreign key enforcement varies by dialect; we surface a 404 ourselves
    so the client gets a stable error shape regardless of backend."""
    found = await ComponentRepository(session).get(component_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "component_not_found", "component_id": str(component_id)},
        )


@router.get("", response_model=PantryList, summary="List pantry items")
async def list_items(
    session: AsyncSession = Depends(get_session),
) -> PantryList:
    repo = PantryRepository(session)
    items = await repo.list()
    return PantryList(
        items=[PantryItemRead.from_domain(i) for i in items],
        total=len(items),
    )


@router.post(
    "",
    response_model=PantryItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a pantry item",
)
async def create_item(
    payload: PantryItemCreate,
    session: AsyncSession = Depends(get_session),
) -> PantryItemRead:
    await _ensure_component_exists(session, payload.component_id)
    repo = PantryRepository(session)
    created = await repo.create(_to_domain(payload, item_id=uuid4()))
    return PantryItemRead.from_domain(created)


@router.put(
    "/{item_id}",
    response_model=PantryItemRead,
    summary="Replace a pantry item",
)
async def update_item(
    item_id: UUID,
    payload: PantryItemCreate,
    session: AsyncSession = Depends(get_session),
) -> PantryItemRead:
    await _ensure_component_exists(session, payload.component_id)
    repo = PantryRepository(session)
    updated = await repo.update(_to_domain(payload, item_id=item_id))
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return PantryItemRead.from_domain(updated)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a pantry item",
)
async def delete_item(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    repo = PantryRepository(session)
    deleted = await repo.delete(item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
