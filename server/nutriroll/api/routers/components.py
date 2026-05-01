"""CRUD endpoints for components, mounted at /v1/components."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.component import (
    ComponentCreate,
    ComponentGenerateRequest,
    ComponentGenerateResponse,
    ComponentList,
    ComponentRead,
)
from nutriroll.api.schemas.problem import ProblemDetail
from nutriroll.db.repositories.components import (
    ComponentNameTakenError,
    ComponentRepository,
)
from nutriroll.db.repositories.profile import UserProfileRepository
from nutriroll.db.session import get_session
from nutriroll.domain.component import Category, Component
from nutriroll.domain.llm_component_builder import LLMBuildError, LLMComponentBuilder
from nutriroll.domain.llm_config import LLMFeatureDisabledError, resolve_runtime_llm_config
from nutriroll.logging import get_logger

router = APIRouter(prefix="/v1/components", tags=["components"])
log = get_logger("nutriroll.api.components")
_GENERATE_RATE_LIMIT = timedelta(seconds=10)
_generate_rate_limit_cache: dict[str, datetime] = {}


def _to_domain(payload: ComponentCreate, *, component_id: UUID) -> Component:
    return Component(
        id=component_id,
        category=payload.category,
        name=payload.name.strip(),
        macros_per_100g=payload.macros_per_100g.to_domain(),
        default_portion=payload.default_portion.to_domain(),
        default_cooking_method=payload.default_cooking_method,
        cooking_methods=tuple(s.to_domain() for s in payload.cooking_methods),
        flavor_tags=tuple(payload.flavor_tags),
        dietary_tags=tuple(payload.dietary_tags),
        allergens=tuple(payload.allergens),
        image_url=payload.image_url,
        shelf_life_days=payload.shelf_life_days,
        seasonal_availability=payload.seasonal_availability,
        blacklisted=payload.blacklisted,
    )


def _problem(
    *,
    request: Request,
    status_code: int,
    title: str,
    detail: str,
    code: str | None = None,
) -> JSONResponse:
    payload = ProblemDetail(
        code=code,
        title=title,
        status=status_code,
        detail=detail,
        instance=str(request.url.path),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
        media_type="application/problem+json",
    )


def _device_key(request: Request) -> str:
    device_id = request.headers.get("x-device-id")
    if device_id:
        return device_id.strip()
    client = request.client
    if client is not None:
        return client.host
    return "anonymous"


def _is_rate_limited(device_key: str, now: datetime) -> bool:
    deadline = _generate_rate_limit_cache.get(device_key)
    if deadline is not None and deadline > now:
        return True
    _generate_rate_limit_cache[device_key] = now + _GENERATE_RATE_LIMIT
    expired = [key for key, value in _generate_rate_limit_cache.items() if value <= now]
    for key in expired:
        _generate_rate_limit_cache.pop(key, None)
    return False


@router.get("", response_model=ComponentList, summary="List components")
async def list_components(
    session: AsyncSession = Depends(get_session),
    category: Category | None = Query(default=None),
    include_blacklisted: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ComponentList:
    repo = ComponentRepository(session)
    items = await repo.list(
        category=category,
        include_blacklisted=include_blacklisted,
        limit=limit,
        offset=offset,
    )
    return ComponentList(
        items=[ComponentRead.from_domain(c) for c in items],
        total=len(items),
    )


@router.post(
    "",
    response_model=ComponentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a component",
)
async def create_component(
    payload: ComponentCreate,
    session: AsyncSession = Depends(get_session),
) -> ComponentRead:
    repo = ComponentRepository(session)
    component = _to_domain(payload, component_id=uuid4())
    try:
        created = await repo.create(component)
    except ComponentNameTakenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"component name already exists: {exc!s}",
        ) from exc
    return ComponentRead.from_domain(created)


@router.post(
    "/generate",
    response_model=ComponentGenerateResponse,
    summary="Generate a component from a natural-language prompt",
    responses={
        400: {"model": ProblemDetail},
        429: {"model": ProblemDetail},
        503: {"model": ProblemDetail},
    },
)
async def generate_component(
    payload: ComponentGenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ComponentGenerateResponse | JSONResponse:
    now = datetime.now(UTC)
    device_key = _device_key(request)
    if _is_rate_limited(device_key, now):
        return _problem(
            request=request,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            title="Rate limit exceeded",
            detail="Please wait 10 seconds before generating another component.",
        )

    profile = payload.profile.to_domain() if payload.profile is not None else None
    stored_llm = await UserProfileRepository(session).get_stored_llm_config()
    builder = LLMComponentBuilder(runtime_config=resolve_runtime_llm_config(stored_llm))
    log.info("component_generate_requested", model=builder.model)
    try:
        generated = await run_in_threadpool(builder.build_from_prompt, payload.prompt, profile)
    except LLMFeatureDisabledError:
        return _problem(
            request=request,
            status_code=status.HTTP_403_FORBIDDEN,
            code="LLM_FEATURE_DISABLED",
            title="AI feature disabled",
            detail="Component creation is disabled in AI settings.",
        )
    except LLMBuildError as exc:
        return _problem(
            request=request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_BUILD_FAILED",
            title="Component generation failed",
            detail=str(exc),
        )

    return ComponentGenerateResponse(
        component=ComponentCreate.from_domain(generated.component),
        raw_llm_output=generated.raw_llm_output,
        confidence=generated.confidence,
    )


@router.get(
    "/{component_id}",
    response_model=ComponentRead,
    summary="Get a component by id",
)
async def get_component(
    component_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ComponentRead:
    repo = ComponentRepository(session)
    found = await repo.get(component_id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return ComponentRead.from_domain(found)


@router.put(
    "/{component_id}",
    response_model=ComponentRead,
    summary="Replace a component",
)
async def update_component(
    component_id: UUID,
    payload: ComponentCreate,
    session: AsyncSession = Depends(get_session),
) -> ComponentRead:
    repo = ComponentRepository(session)
    component = _to_domain(payload, component_id=component_id)
    try:
        updated = await repo.update(component)
    except ComponentNameTakenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"component name already exists: {exc!s}",
        ) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return ComponentRead.from_domain(updated)


@router.delete(
    "/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a component",
)
async def delete_component(
    component_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    repo = ComponentRepository(session)
    deleted = await repo.delete(component_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
