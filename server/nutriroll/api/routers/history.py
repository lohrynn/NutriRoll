"""History endpoints, mounted at /v1/history."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.history import (
    HistoryEventCreate,
    HistoryEventRead,
    HistoryList,
)
from nutriroll.db.repositories.history import HistoryRepository
from nutriroll.db.session import get_session
from nutriroll.domain.history import HistoryEvent, HistoryEventKind

router = APIRouter(prefix="/v1/history", tags=["history"])


@router.get("", response_model=HistoryList, summary="List history events")
async def list_events(
    kind: HistoryEventKind | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> HistoryList:
    repo = HistoryRepository(session)
    items = await repo.list(kind=kind, limit=limit)
    return HistoryList(items=[HistoryEventRead.from_domain(e) for e in items], total=len(items))


@router.post(
    "",
    response_model=HistoryEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Append a history event",
)
async def create_event(
    payload: HistoryEventCreate, session: AsyncSession = Depends(get_session)
) -> HistoryEventRead:
    repo = HistoryRepository(session)
    event = HistoryEvent(
        id=uuid4(),
        kind=payload.kind,
        bowl_id=payload.bowl_id,
        payload=dict(payload.payload),
    )
    saved = await repo.create(event)
    return HistoryEventRead.from_domain(saved)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a history event",
)
async def delete_event(event_id: UUID, session: AsyncSession = Depends(get_session)) -> Response:
    repo = HistoryRepository(session)
    if not await repo.delete(event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
