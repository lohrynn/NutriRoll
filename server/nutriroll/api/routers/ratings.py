"""Ratings endpoints, mounted at /v1/ratings."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.rating import RatingCreate, RatingList, RatingRead
from nutriroll.db.repositories.components import ComponentRepository
from nutriroll.db.repositories.ratings import RatingsRepository
from nutriroll.db.session import get_session
from nutriroll.domain.rating import Rating

router = APIRouter(prefix="/v1/ratings", tags=["ratings"])


@router.get("", response_model=RatingList, summary="List ratings (optionally per bowl)")
async def list_ratings(
    bowl_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> RatingList:
    repo = RatingsRepository(session)
    items = await repo.list(bowl_id=bowl_id)
    return RatingList(items=[RatingRead.from_domain(r) for r in items], total=len(items))


@router.post(
    "",
    response_model=RatingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a rating",
)
async def create_rating(
    payload: RatingCreate, session: AsyncSession = Depends(get_session)
) -> RatingRead:
    if payload.component_id is not None:
        found = await ComponentRepository(session).get(payload.component_id)
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "component_not_found",
                    "component_id": str(payload.component_id),
                },
            )
    repo = RatingsRepository(session)
    rating = Rating(
        id=uuid4(),
        bowl_id=payload.bowl_id,
        component_id=payload.component_id,
        score=payload.score,
        comment=payload.comment,
    )
    saved = await repo.create(rating)
    return RatingRead.from_domain(saved)


__all__ = ["router"]
