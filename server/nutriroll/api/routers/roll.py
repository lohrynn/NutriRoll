"""Roll endpoints, mounted at /v1/roll.

Loads the entire component pool (small in v1, ~80 rows) from the DB and
runs the framework-free `nutriroll.domain.roll.roll` against it.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.roll import (
    RerollSlotRequestSchema,
    RolledBowlSchema,
    RolledSlotSchema,
    RollRequestSchema,
    SlotSpecSchema,
)
from nutriroll.db.repositories.components import ComponentRepository
from nutriroll.db.repositories.pantry import PantryRepository
from nutriroll.db.session import get_session
from nutriroll.domain.category_meta import EXPIRY_WARNING_DAYS
from nutriroll.domain.component import Component
from nutriroll.domain.roll import (
    EmptyCandidatePoolError,
    RollRequest,
    SlotSpec,
    roll,
)

router = APIRouter(prefix="/v1/roll", tags=["roll"])

# `EXPIRY_WARNING_DAYS` is imported from `nutriroll.domain.category_meta` and
# exposed by `GET /v1/meta/components`. Do not redefine it here (M9).


async def _load_pool(session: AsyncSession) -> list[Component]:
    repo = ComponentRepository(session)
    return list(
        await repo.list(
            category=None,
            include_blacklisted=False,
            limit=1000,
            offset=0,
        )
    )


async def _collect_pantry_context(
    session: AsyncSession,
) -> tuple[frozenset[UUID], frozenset[UUID]]:
    """Returns (pantry_component_ids, expiring_component_ids)."""
    items = await PantryRepository(session).list()
    pantry_ids: frozenset[UUID] = frozenset(item.component_id for item in items)
    threshold = date.today() + timedelta(days=EXPIRY_WARNING_DAYS)
    expiring_ids: frozenset[UUID] = frozenset(
        item.component_id
        for item in items
        if item.expires_at is not None and item.expires_at <= threshold
    )
    return pantry_ids, expiring_ids


def _with_pantry(
    base: RollRequest,
    pantry_ids: frozenset[UUID],
    expiring_ids: frozenset[UUID],
) -> RollRequest:
    # Caller-supplied IDs (rare, mostly tests) take precedence so the algorithm
    # remains deterministic when the request explicitly sets them.
    if base.pantry_component_ids or base.expiring_component_ids:
        return base
    return RollRequest(
        slots=base.slots,
        dietary_mode=base.dietary_mode,
        allergens_excluded=base.allergens_excluded,
        blacklisted_ids=base.blacklisted_ids,
        time_budget_min=base.time_budget_min,
        forced_methods=base.forced_methods,
        recent_component_ids=base.recent_component_ids,
        weights=base.weights,
        tag_boosts=base.tag_boosts,
        macro_targets=base.macro_targets,
        portions=base.portions,
        available_equipment=base.available_equipment,
        pantry_component_ids=pantry_ids,
        expiring_component_ids=expiring_ids,
        temperature=base.temperature,
        seed=base.seed,
    )


@router.post(
    "",
    response_model=RolledBowlSchema,
    summary="Roll a bowl",
)
async def roll_bowl(
    payload: RollRequestSchema,
    session: AsyncSession = Depends(get_session),
) -> RolledBowlSchema:
    domain_request = payload.to_domain()
    pantry_ids, expiring_ids = await _collect_pantry_context(session)
    domain_request = _with_pantry(domain_request, pantry_ids, expiring_ids)
    pool = await _load_pool(session)
    try:
        bowl = roll(pool, domain_request)
    except EmptyCandidatePoolError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "empty_candidate_pool",
                "category": exc.category.value,
                "reason": exc.reason,
            },
        ) from exc
    return RolledBowlSchema.from_domain(bowl)


@router.post(
    "/slot",
    response_model=RolledSlotSchema,
    summary="Re-roll a single slot",
)
async def reroll_one_slot(
    payload: RerollSlotRequestSchema,
    session: AsyncSession = Depends(get_session),
) -> RolledSlotSchema:
    base = payload.request.to_domain()
    pantry_ids, expiring_ids = await _collect_pantry_context(session)
    extra_excluded = base.blacklisted_ids | frozenset(payload.exclude_component_ids)
    sub_request = RollRequest(
        slots=(SlotSpec(category=payload.slot_category, count=1),),
        dietary_mode=base.dietary_mode,
        allergens_excluded=base.allergens_excluded,
        blacklisted_ids=extra_excluded,
        time_budget_min=base.time_budget_min,
        forced_methods=base.forced_methods,
        recent_component_ids=base.recent_component_ids,
        weights=base.weights,
        tag_boosts=base.tag_boosts,
        macro_targets=base.macro_targets,
        portions=base.portions,
        available_equipment=base.available_equipment,
        pantry_component_ids=pantry_ids,
        expiring_component_ids=expiring_ids,
        temperature=base.temperature,
        seed=base.seed,
    )
    pool = await _load_pool(session)
    try:
        bowl = roll(pool, sub_request)
    except EmptyCandidatePoolError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "empty_candidate_pool",
                "category": exc.category.value,
                "reason": exc.reason,
            },
        ) from exc
    if not bowl.slots:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "no_slot_returned"},
        )
    return RolledSlotSchema.from_domain(bowl.slots[0])


__all__ = ["SlotSpecSchema", "router"]
