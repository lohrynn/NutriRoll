"""History repository — append-only event log."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.db.models.history import HistoryEventRow
from nutriroll.domain.history import HistoryEvent, HistoryEventKind


def _to_domain(row: HistoryEventRow) -> HistoryEvent:
    return HistoryEvent(
        id=row.id,
        kind=HistoryEventKind(row.kind),
        bowl_id=row.bowl_id,
        payload=dict(row.payload) if row.payload else {},
        created_at=row.created_at,
    )


class HistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, *, kind: HistoryEventKind | None = None, limit: int = 100
    ) -> list[HistoryEvent]:
        stmt = select(HistoryEventRow).order_by(HistoryEventRow.created_at.desc())
        if kind is not None:
            stmt = stmt.where(HistoryEventRow.kind == kind.value)
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return [_to_domain(r) for r in result.scalars().all()]

    async def create(self, event: HistoryEvent) -> HistoryEvent:
        row = HistoryEventRow(
            id=event.id,
            kind=event.kind.value,
            bowl_id=event.bowl_id,
            payload=event.payload,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_domain(row)

    async def delete(self, event_id: UUID) -> bool:
        row = await self._session.get(HistoryEventRow, event_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def clear(self) -> int:
        result = await self._session.execute(delete(HistoryEventRow))
        await self._session.commit()
        rowcount: int = getattr(result, "rowcount", 0) or 0
        return rowcount
