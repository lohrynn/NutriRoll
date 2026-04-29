"""CRUD endpoints for components, mounted at /v1/components."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.component import (
    ComponentCreate,
    ComponentList,
    ComponentRead,
)
from nutriroll.db.repositories.components import (
    ComponentNameTakenError,
    ComponentRepository,
)
from nutriroll.db.session import get_session
from nutriroll.domain.component import Category, Component

router = APIRouter(prefix="/v1/components", tags=["components"])


def _to_domain(payload: ComponentCreate, *, component_id: UUID) -> Component:
    return Component(
        id=component_id,
        category=payload.category,
        name=payload.name.strip(),
        macros_per_100g=payload.macros_per_100g.to_domain(),
        default_portion=payload.default_portion.to_domain(),
        default_cooking_method=payload.default_cooking_method,
        cooking_methods=tuple(s.to_domain() for s in payload.cooking_methods),
        flavor_tags=tuple(payload.flavor_tags),
        dietary_tags=tuple(payload.dietary_tags),
        allergens=tuple(payload.allergens),
        image_url=payload.image_url,
        shelf_life_days=payload.shelf_life_days,
        blacklisted=payload.blacklisted,
    )


@router.get("", response_model=ComponentList, summary="List components")
async def list_components(
    session: AsyncSession = Depends(get_session),
    category: Category | None = Query(default=None),
    include_blacklisted: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ComponentList:
    repo = ComponentRepository(session)
    items = await repo.list(
        category=category,
        include_blacklisted=include_blacklisted,
        limit=limit,
        offset=offset,
    )
    return ComponentList(
        items=[ComponentRead.from_domain(c) for c in items],
        total=len(items),
    )


@router.post(
    "",
    response_model=ComponentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a component",
)
async def create_component(
    payload: ComponentCreate,
    session: AsyncSession = Depends(get_session),
) -> ComponentRead:
    repo = ComponentRepository(session)
    component = _to_domain(payload, component_id=uuid4())
    try:
        created = await repo.create(component)
    except ComponentNameTakenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"component name already exists: {exc!s}",
        ) from exc
    return ComponentRead.from_domain(created)


@router.get(
    "/{component_id}",
    response_model=ComponentRead,
    summary="Get a component by id",
)
async def get_component(
    component_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ComponentRead:
    repo = ComponentRepository(session)
    found = await repo.get(component_id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return ComponentRead.from_domain(found)


@router.put(
    "/{component_id}",
    response_model=ComponentRead,
    summary="Replace a component",
)
async def update_component(
    component_id: UUID,
    payload: ComponentCreate,
    session: AsyncSession = Depends(get_session),
) -> ComponentRead:
    repo = ComponentRepository(session)
    component = _to_domain(payload, component_id=component_id)
    try:
        updated = await repo.update(component)
    except ComponentNameTakenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"component name already exists: {exc!s}",
        ) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return ComponentRead.from_domain(updated)


@router.delete(
    "/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a component",
)
async def delete_component(
    component_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    repo = ComponentRepository(session)
    deleted = await repo.delete(component_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
