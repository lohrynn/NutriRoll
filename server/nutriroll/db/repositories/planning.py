"""Repositories for saved meals + planned meals."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.db.models.planning import PlannedMealRow, SavedMealRow
from nutriroll.domain.planning import MealSlot, PlannedMeal, PlannedStatus, SavedMeal


def _saved_to_domain(row: SavedMealRow) -> SavedMeal:
    return SavedMeal(
        id=row.id,
        name=row.name,
        bowl_snapshot=dict(row.bowl_snapshot) if row.bowl_snapshot else {},
        notes=row.notes,
        created_at=row.created_at,
    )


def _planned_to_domain(row: PlannedMealRow) -> PlannedMeal:
    return PlannedMeal(
        id=row.id,
        planned_for=row.planned_for,
        slot=MealSlot(row.slot),
        bowl_snapshot=dict(row.bowl_snapshot) if row.bowl_snapshot else {},
        status=PlannedStatus(row.status),
        notes=row.notes,
        portions_total=row.portions_total,
        portions_remaining=row.portions_remaining,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SavedMealRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[SavedMeal]:
        stmt = select(SavedMealRow).order_by(SavedMealRow.created_at.desc())
        result = await self._session.execute(stmt)
        return [_saved_to_domain(r) for r in result.scalars().all()]

    async def get(self, meal_id: UUID) -> SavedMeal | None:
        row = await self._session.get(SavedMealRow, meal_id)
        return _saved_to_domain(row) if row else None

    async def create(self, meal: SavedMeal) -> SavedMeal:
        row = SavedMealRow(
            id=meal.id,
            name=meal.name,
            bowl_snapshot=meal.bowl_snapshot,
            notes=meal.notes,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _saved_to_domain(row)

    async def delete(self, meal_id: UUID) -> bool:
        row = await self._session.get(SavedMealRow, meal_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True


class PlannedMealRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, *, start: date | None = None, end: date | None = None
    ) -> list[PlannedMeal]:
        stmt = select(PlannedMealRow).order_by(
            PlannedMealRow.planned_for.asc(), PlannedMealRow.slot.asc()
        )
        if start is not None:
            stmt = stmt.where(PlannedMealRow.planned_for >= start)
        if end is not None:
            stmt = stmt.where(PlannedMealRow.planned_for <= end)
        result = await self._session.execute(stmt)
        return [_planned_to_domain(r) for r in result.scalars().all()]

    async def get(self, meal_id: UUID) -> PlannedMeal | None:
        row = await self._session.get(PlannedMealRow, meal_id)
        return _planned_to_domain(row) if row else None

    async def create(self, meal: PlannedMeal) -> PlannedMeal:
        row = PlannedMealRow(
            id=meal.id,
            planned_for=meal.planned_for,
            slot=meal.slot.value,
            bowl_snapshot=meal.bowl_snapshot,
            status=meal.status.value,
            notes=meal.notes,
            portions_total=meal.portions_total,
            portions_remaining=meal.portions_remaining,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _planned_to_domain(row)

    async def update(
        self,
        meal_id: UUID,
        *,
        planned_for: date | None = None,
        slot: MealSlot | None = None,
        status: PlannedStatus | None = None,
        notes: str | None = None,
    ) -> PlannedMeal | None:
        row = await self._session.get(PlannedMealRow, meal_id)
        if row is None:
            return None
        if planned_for is not None:
            row.planned_for = planned_for
        if slot is not None:
            row.slot = slot.value
        if status is not None:
            row.status = status.value
        if notes is not None:
            row.notes = notes
        await self._session.commit()
        await self._session.refresh(row)
        return _planned_to_domain(row)

    async def delete(self, meal_id: UUID) -> bool:
        row = await self._session.get(PlannedMealRow, meal_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def mark_eaten(self, meal_id: UUID) -> PlannedMeal | None:
        """Phase 12. Decrement ``portions_remaining`` by 1; when it hits 0,
        flip ``status`` to ``cooked`` so the planner UI can stop showing the
        entry as actionable. No-op (returns current state) if already 0.
        """
        row = await self._session.get(PlannedMealRow, meal_id)
        if row is None:
            return None
        if row.portions_remaining > 0:
            row.portions_remaining -= 1
        if row.portions_remaining == 0 and row.status != PlannedStatus.COOKED.value:
            row.status = PlannedStatus.COOKED.value
        await self._session.commit()
        await self._session.refresh(row)
        return _planned_to_domain(row)
