"""Singleton user profile repository."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.db.models.profile import UserProfileRow
from nutriroll.domain.profile import UserProfile

PROFILE_ID = 1


def _to_domain(row: UserProfileRow) -> UserProfile:
    raw_allergens = row.allergens or []
    raw_weights: dict[str, float] = (
        {k: float(v) for k, v in (row.roll_weights or {}).items()}
    )
    return UserProfile(
        dietary_mode=row.dietary_mode,
        allergens=tuple(str(a) for a in raw_allergens),
        default_time_budget_min=row.default_time_budget_min,
        goal=row.goal,
        locale=row.locale,
        onboarded=row.onboarded,
        roll_weights=tuple(raw_weights.items()),
    )


class UserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> UserProfile:
        stmt = (
            pg_insert(UserProfileRow)
            .values(id=PROFILE_ID, allergens=[])
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await self._session.execute(stmt)
        await self._session.commit()
        row = await self._session.get(UserProfileRow, PROFILE_ID)
        assert row is not None
        return _to_domain(row)

    async def update(self, profile: UserProfile) -> UserProfile:
        weights_json: dict[str, float] | None = (
            dict(profile.roll_weights) if profile.roll_weights else None
        )
        stmt = (
            pg_insert(UserProfileRow)
            .values(
                id=PROFILE_ID,
                dietary_mode=profile.dietary_mode,
                allergens=list(profile.allergens),
                default_time_budget_min=profile.default_time_budget_min,
                goal=profile.goal,
                locale=profile.locale,
                onboarded=profile.onboarded,
                roll_weights=weights_json,
            )
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "dietary_mode": profile.dietary_mode,
                    "allergens": list(profile.allergens),
                    "default_time_budget_min": profile.default_time_budget_min,
                    "goal": profile.goal,
                    "locale": profile.locale,
                    "onboarded": profile.onboarded,
                    "roll_weights": weights_json,
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        row = await self._session.get(UserProfileRow, PROFILE_ID)
        assert row is not None
        return _to_domain(row)
