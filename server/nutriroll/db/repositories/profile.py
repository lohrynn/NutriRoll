"""Singleton user profile repository."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.db.models.profile import UserProfileRow
from nutriroll.domain.profile import UserProfile

PROFILE_ID = 1


def _to_domain(row: UserProfileRow) -> UserProfile:
    raw_allergens = row.allergens or []
    return UserProfile(
        dietary_mode=row.dietary_mode,
        allergens=tuple(str(a) for a in raw_allergens),
        default_time_budget_min=row.default_time_budget_min,
        goal=row.goal,
        locale=row.locale,
        onboarded=row.onboarded,
    )


class UserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> UserProfile:
        row = await self._session.get(UserProfileRow, PROFILE_ID)
        if row is None:
            row = UserProfileRow(id=PROFILE_ID, allergens=[])
            self._session.add(row)
            await self._session.commit()
            await self._session.refresh(row)
        return _to_domain(row)

    async def update(self, profile: UserProfile) -> UserProfile:
        row = await self._session.get(UserProfileRow, PROFILE_ID)
        if row is None:
            row = UserProfileRow(id=PROFILE_ID)
            self._session.add(row)
        row.dietary_mode = profile.dietary_mode
        row.allergens = list(profile.allergens)
        row.default_time_budget_min = profile.default_time_budget_min
        row.goal = profile.goal
        row.locale = profile.locale
        row.onboarded = profile.onboarded
        await self._session.commit()
        await self._session.refresh(row)
        return _to_domain(row)
