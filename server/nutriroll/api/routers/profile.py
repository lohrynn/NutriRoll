"""Singleton profile endpoints, mounted at /v1/me/profile."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.profile import UserProfileRead, UserProfileUpdate
from nutriroll.db.repositories.profile import UserProfileRepository
from nutriroll.db.session import get_session

router = APIRouter(prefix="/v1/me", tags=["profile"])


@router.get("/profile", response_model=UserProfileRead, summary="Get user profile")
async def get_profile(session: AsyncSession = Depends(get_session)) -> UserProfileRead:
    repo = UserProfileRepository(session)
    profile = await repo.get_or_create()
    return UserProfileRead.from_domain(profile)


@router.put("/profile", response_model=UserProfileRead, summary="Update user profile")
async def update_profile(
    payload: UserProfileUpdate, session: AsyncSession = Depends(get_session)
) -> UserProfileRead:
    repo = UserProfileRepository(session)
    saved = await repo.update(payload.to_domain())
    return UserProfileRead.from_domain(saved)


__all__ = ["router"]
