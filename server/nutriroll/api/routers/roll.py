"""Roll endpoints, mounted at /v1/roll.

Loads the entire component pool (small in v1, ~80 rows) from the DB and
runs the framework-free `nutriroll.domain.roll.roll` against it.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.problem import ProblemDetail
from nutriroll.api.schemas.roll import (
    RerollSlotRequestSchema,
    RolledBowlSchema,
    RolledSlotSchema,
    RollRequestSchema,
    SlotSpecSchema,
)
from nutriroll.db.repositories.components import ComponentRepository
from nutriroll.db.repositories.pantry import PantryRepository
from nutriroll.db.repositories.profile import UserProfileRepository
from nutriroll.db.session import get_session
from nutriroll.domain.category_meta import EXPIRY_WARNING_DAYS
from nutriroll.domain.component import ALLOWED_METHODS, Component
from nutriroll.domain.direction import CUISINE_BOOSTS
from nutriroll.domain.roll import MacroTarget, MacroTargets
from nutriroll.domain.roll import (
    EmptyCandidatePoolError,
    RollRequest,
    SlotSpec,
    roll,
)
from nutriroll.domain.roll_prompt_parser import (
    PromptParseError,
    RollConstraints,
    RollPromptParser,
)
from nutriroll.domain.llm_config import LLMFeatureDisabledError, resolve_runtime_llm_config

router = APIRouter(prefix="/v1/roll", tags=["roll"])

# `EXPIRY_WARNING_DAYS` is imported from `nutriroll.domain.category_meta` and
# exposed by `GET /v1/meta/components`. Do not redefine it here (M9).


def _problem(
    *,
    request: Request,
    status_code: int,
    code: str,
    title: str,
    detail: str,
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
        content=payload.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


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


def _clip_boost(value: float) -> float:
    return max(-1.0, min(1.0, round(value, 4)))


def _parsed_tag_boosts(constraints: RollConstraints) -> dict[str, float]:
    boosts = dict(constraints.flavor_boosts)
    for cuisine, weight in constraints.cuisine_weights.items():
        for tag, boost in CUISINE_BOOSTS[cuisine].items():
            boosts[tag] = _clip_boost(boosts.get(tag, 0.0) + (boost * weight))
    return boosts


def _parsed_macro_targets(constraints: RollConstraints) -> MacroTargets | None:
    bounds = constraints.macro_bounds
    if bounds is None:
        return None
    mapping: dict[str, MacroTarget] = {}
    if bounds.min_protein is not None:
        mapping["protein_g"] = MacroTarget(value=bounds.min_protein, mode="min")
    if bounds.max_kcal is not None:
        mapping["kcal"] = MacroTarget(value=bounds.max_kcal, mode="max")
    if bounds.min_fiber is not None:
        mapping["fiber_g"] = MacroTarget(value=bounds.min_fiber, mode="min")
    if bounds.max_sodium is not None:
        mapping["sodium_mg"] = MacroTarget(value=bounds.max_sodium, mode="max")
    if not mapping:
        return None
    return MacroTargets.from_mapping(mapping)


def _merge_macro_targets(
    explicit: MacroTargets | None, parsed: MacroTargets | None
) -> MacroTargets | None:
    if parsed is None:
        return explicit
    if explicit is None:
        return parsed
    merged = parsed.as_mapping()
    merged.update(explicit.as_mapping())
    return MacroTargets.from_mapping(merged)


def _merge_prompt_constraints(
    base: RollRequest,
    constraints: RollConstraints,
    *,
    pool: list[Component],
    pantry_ids: frozenset[UUID],
) -> RollRequest:
    parsed_boosts = _parsed_tag_boosts(constraints)
    merged_boosts = parsed_boosts
    if base.tag_boosts:
        merged_boosts = dict(parsed_boosts)
        for tag, boost in base.tag_boosts.items():
            merged_boosts[tag] = _clip_boost(boost)

    blacklisted_ids = set(base.blacklisted_ids)
    blacklisted_ids.update(constraints.hard_exclusion_ids)
    if constraints.pantry_only:
        blacklisted_ids.update(component.id for component in pool if component.id not in pantry_ids)

    forced_methods = dict(base.forced_methods)
    parsed_method = constraints.cooking_method_constraint
    if parsed_method is not None:
        seen_categories = {slot.category for slot in base.slots}
        for category in seen_categories:
            if category in forced_methods:
                continue
            if parsed_method in ALLOWED_METHODS[category]:
                forced_methods[category] = parsed_method

    return RollRequest(
        slots=base.slots,
        dietary_mode=base.dietary_mode,
        allergens_excluded=base.allergens_excluded | constraints.allergen_exclusions,
        blacklisted_ids=frozenset(blacklisted_ids),
        time_budget_min=(
            base.time_budget_min
            if base.time_budget_min is not None
            else constraints.time_budget_minutes
        ),
        forced_methods=forced_methods,
        recent_component_ids=base.recent_component_ids,
        weights=base.weights,
        tag_boosts=merged_boosts,
        macro_targets=_merge_macro_targets(base.macro_targets, _parsed_macro_targets(constraints)),
        portions=base.portions,
        available_equipment=base.available_equipment,
        pantry_component_ids=base.pantry_component_ids,
        expiring_component_ids=base.expiring_component_ids,
        temperature=base.temperature,
        seed=base.seed,
    )


async def _parse_prompt_constraints(
    prompt: str | None,
    session: AsyncSession,
) -> RollConstraints:
    if prompt is None or prompt.strip() == "":
        return RollConstraints()
    profile_repo = UserProfileRepository(session)
    profile = await profile_repo.get_or_create()
    stored_llm = await profile_repo.get_stored_llm_config()
    parser = RollPromptParser(runtime_config=resolve_runtime_llm_config(stored_llm))
    return await run_in_threadpool(parser.parse_prompt, prompt, profile)


async def _build_domain_request(
    payload: RollRequestSchema,
    session: AsyncSession,
    *,
    pool: list[Component],
    pantry_ids: frozenset[UUID],
) -> RollRequest:
    base_request = payload.to_domain()
    constraints = await _parse_prompt_constraints(payload.prompt, session)
    if constraints.is_empty():
        return base_request
    return _merge_prompt_constraints(base_request, constraints, pool=pool, pantry_ids=pantry_ids)


@router.post(
    "",
    response_model=RolledBowlSchema,
    summary="Roll a bowl",
    responses={400: {"model": ProblemDetail}},
)
async def roll_bowl(
    payload: RollRequestSchema,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> RolledBowlSchema | JSONResponse:
    pantry_ids, expiring_ids = await _collect_pantry_context(session)
    pool = await _load_pool(session)
    try:
        domain_request = await _build_domain_request(
            payload,
            session,
            pool=pool,
            pantry_ids=pantry_ids,
        )
    except LLMFeatureDisabledError as exc:
        return _problem(
            request=request,
            status_code=status.HTTP_403_FORBIDDEN,
            code="LLM_FEATURE_DISABLED",
            title="AI feature disabled",
            detail=f"{exc.feature.replace('_', ' ').title()} is disabled in AI settings.",
        )
    except PromptParseError as exc:
        return _problem(
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="PROMPT_PARSE_FAILED",
            title="Prompt could not be parsed",
            detail=str(exc),
        )
    domain_request = _with_pantry(domain_request, pantry_ids, expiring_ids)
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
    responses={400: {"model": ProblemDetail}},
)
async def reroll_one_slot(
    payload: RerollSlotRequestSchema,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> RolledSlotSchema | JSONResponse:
    pantry_ids, expiring_ids = await _collect_pantry_context(session)
    pool = await _load_pool(session)
    try:
        base = await _build_domain_request(
            payload.request,
            session,
            pool=pool,
            pantry_ids=pantry_ids,
        )
    except LLMFeatureDisabledError as exc:
        return _problem(
            request=request,
            status_code=status.HTTP_403_FORBIDDEN,
            code="LLM_FEATURE_DISABLED",
            title="AI feature disabled",
            detail=f"{exc.feature.replace('_', ' ').title()} is disabled in AI settings.",
        )
    except PromptParseError as exc:
        return _problem(
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="PROMPT_PARSE_FAILED",
            title="Prompt could not be parsed",
            detail=str(exc),
        )
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
