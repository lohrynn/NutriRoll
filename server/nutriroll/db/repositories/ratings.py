"""Ratings repository — append + read."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.db.models.rating import RatingRow
from nutriroll.domain.rating import Rating


def _to_domain(row: RatingRow) -> Rating:
    return Rating(
        id=row.id,
        bowl_id=row.bowl_id,
        component_id=row.component_id,
        score=row.score,
        comment=row.comment,
        created_at=row.created_at,
    )


class RatingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, bowl_id: UUID | None = None) -> list[Rating]:
        stmt = select(RatingRow).order_by(RatingRow.created_at.desc())
        if bowl_id is not None:
            stmt = stmt.where(RatingRow.bowl_id == bowl_id)
        result = await self._session.execute(stmt)
        return [_to_domain(r) for r in result.scalars().all()]

    async def create(self, rating: Rating) -> Rating:
        row = RatingRow(
            id=rating.id,
            bowl_id=rating.bowl_id,
            component_id=rating.component_id,
            score=rating.score,
            comment=rating.comment,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_domain(row)
