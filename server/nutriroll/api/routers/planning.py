"""Saved meals + planned meals endpoints."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.planning import (
    PlannedMealCreate,
    PlannedMealList,
    PlannedMealRead,
    PlannedMealUpdate,
    SavedMealCreate,
    SavedMealList,
    SavedMealRead,
)
from nutriroll.db.repositories.planning import (
    PlannedMealRepository,
    SavedMealRepository,
)
from nutriroll.db.session import get_session
from nutriroll.domain.planning import PlannedMeal, SavedMeal

saved_router = APIRouter(prefix="/v1/saved", tags=["saved-meals"])
planned_router = APIRouter(prefix="/v1/planned", tags=["planned-meals"])


@saved_router.get("", response_model=SavedMealList, summary="List saved meals")
async def list_saved(session: AsyncSession = Depends(get_session)) -> SavedMealList:
    repo = SavedMealRepository(session)
    items = await repo.list()
    return SavedMealList(items=[SavedMealRead.from_domain(m) for m in items], total=len(items))


@saved_router.post(
    "",
    response_model=SavedMealRead,
    status_code=status.HTTP_201_CREATED,
    summary="Save a bowl snapshot",
)
async def create_saved(
    payload: SavedMealCreate, session: AsyncSession = Depends(get_session)
) -> SavedMealRead:
    repo = SavedMealRepository(session)
    meal = SavedMeal(
        id=uuid4(),
        name=payload.name,
        bowl_snapshot=dict(payload.bowl_snapshot),
        notes=payload.notes,
    )
    saved = await repo.create(meal)
    return SavedMealRead.from_domain(saved)


@saved_router.delete(
    "/{meal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved meal",
)
async def delete_saved(meal_id: UUID, session: AsyncSession = Depends(get_session)) -> Response:
    repo = SavedMealRepository(session)
    if not await repo.delete(meal_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@planned_router.get(
    "", response_model=PlannedMealList, summary="List planned meals (optionally by range)"
)
async def list_planned(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> PlannedMealList:
    repo = PlannedMealRepository(session)
    items = await repo.list(start=start, end=end)
    return PlannedMealList(items=[PlannedMealRead.from_domain(m) for m in items], total=len(items))


@planned_router.post(
    "",
    response_model=PlannedMealRead,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a meal",
)
async def create_planned(
    payload: PlannedMealCreate, session: AsyncSession = Depends(get_session)
) -> PlannedMealRead:
    repo = PlannedMealRepository(session)
    meal = PlannedMeal(
        id=uuid4(),
        planned_for=payload.planned_for,
        slot=payload.slot,
        bowl_snapshot=dict(payload.bowl_snapshot),
        status=payload.status,
        notes=payload.notes,
    )
    saved = await repo.create(meal)
    return PlannedMealRead.from_domain(saved)


@planned_router.patch(
    "/{meal_id}",
    response_model=PlannedMealRead,
    summary="Update a planned meal (move/restatus)",
)
async def update_planned(
    meal_id: UUID,
    payload: PlannedMealUpdate,
    session: AsyncSession = Depends(get_session),
) -> PlannedMealRead:
    repo = PlannedMealRepository(session)
    updated = await repo.update(
        meal_id,
        planned_for=payload.planned_for,
        slot=payload.slot,
        status=payload.status,
        notes=payload.notes,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return PlannedMealRead.from_domain(updated)


@planned_router.delete(
    "/{meal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a planned meal",
)
async def delete_planned(meal_id: UUID, session: AsyncSession = Depends(get_session)) -> Response:
    repo = PlannedMealRepository(session)
    if not await repo.delete(meal_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["planned_router", "saved_router"]
