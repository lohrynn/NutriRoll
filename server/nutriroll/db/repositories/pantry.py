"""Pantry repository — async CRUD over PantryItemRow."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.db.models.pantry import PantryItemRow
from nutriroll.domain.component import PortionUnit
from nutriroll.domain.pantry import PantryItem


def _row_to_domain(row: PantryItemRow) -> PantryItem:
    return PantryItem(
        id=row.id,
        component_id=row.component_id,
        quantity=row.quantity,
        unit=PortionUnit(row.unit),
        opened=row.opened,
        expires_at=row.expires_at,
    )


class PantryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[PantryItem]:
        stmt = select(PantryItemRow).order_by(PantryItemRow.created_at.desc())
        result = await self._session.execute(stmt)
        return [_row_to_domain(r) for r in result.scalars().all()]

    async def get(self, item_id: UUID) -> PantryItem | None:
        row = await self._session.get(PantryItemRow, item_id)
        return _row_to_domain(row) if row is not None else None

    async def create(self, item: PantryItem) -> PantryItem:
        row = PantryItemRow(
            id=item.id,
            component_id=item.component_id,
            quantity=item.quantity,
            unit=item.unit.value,
            opened=item.opened,
            expires_at=item.expires_at,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _row_to_domain(row)

    async def update(self, item: PantryItem) -> PantryItem | None:
        row = await self._session.get(PantryItemRow, item.id)
        if row is None:
            return None
        row.component_id = item.component_id
        row.quantity = item.quantity
        row.unit = item.unit.value
        row.opened = item.opened
        row.expires_at = item.expires_at
        await self._session.commit()
        await self._session.refresh(row)
        return _row_to_domain(row)

    async def delete(self, item_id: UUID) -> bool:
        row = await self._session.get(PantryItemRow, item_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True
