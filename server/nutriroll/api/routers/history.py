"""History endpoints, mounted at /v1/history."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.history import (
    HistoryEventCreate,
    HistoryEventRead,
    HistoryRecapResponse,
    HistoryList,
    RecapSchema,
)
from nutriroll.db.repositories.history import HistoryRepository
from nutriroll.db.repositories.profile import UserProfileRepository
from nutriroll.db.session import get_session
from nutriroll.domain.history import HistoryEvent, HistoryEventKind
from nutriroll.domain.weekly_recap import Recap, WeeklyRecapGenerator

router = APIRouter(prefix="/v1/history", tags=["history"])
_RECAP_CACHE_TTL = timedelta(hours=1)
_recap_cache: dict[tuple[str, date], tuple[datetime, Recap]] = {}


def _history_identity(request: Request) -> str:
    for cookie_key in ("nutriroll-device-token", "device_token"):
        cookie_value = request.cookies.get(cookie_key)
        if cookie_value and cookie_value.strip():
            return cookie_value.strip()
    header_value = request.headers.get("x-device-id")
    if header_value and header_value.strip():
        return header_value.strip()
    client = request.client
    if client is not None:
        return client.host
    return "anonymous"


def _get_cached_recap(user_id: str, week_start: date) -> Recap | None:
    now = datetime.now(UTC)
    expired = [key for key, value in _recap_cache.items() if value[0] <= now]
    for key in expired:
        _recap_cache.pop(key, None)
    cached = _recap_cache.get((user_id, week_start))
    if cached is None:
        return None
    return cached[1]


def _store_cached_recap(user_id: str, week_start: date, recap: Recap) -> None:
    _recap_cache[(user_id, week_start)] = (datetime.now(UTC) + _RECAP_CACHE_TTL, recap)


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


@router.get("/recap", response_model=HistoryRecapResponse, summary="Get a weekly recap")
async def get_weekly_recap(
    request: Request,
    week_start: date = Query(...),
    generate: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> HistoryRecapResponse:
    user_id = _history_identity(request)
    cached = _get_cached_recap(user_id, week_start)
    if cached is not None:
        return HistoryRecapResponse(
            week_start=week_start,
            recap=RecapSchema.from_domain(cached),
            cached=True,
        )

    profile = await UserProfileRepository(session).get_or_create()
    if not generate or not profile.llm_weekly_recap_enabled:
        return HistoryRecapResponse(week_start=week_start, recap=None, cached=False)

    recap = await WeeklyRecapGenerator(session).generate_recap(user_id, week_start)
    _store_cached_recap(user_id, week_start, recap)
    return HistoryRecapResponse(
        week_start=week_start,
        recap=RecapSchema.from_domain(recap),
        cached=False,
    )


__all__ = ["router"]
