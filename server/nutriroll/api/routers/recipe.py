"""Recipe endpoints, mounted at /v1/recipe.

Pure recipe construction over the chosen components of a rolled bowl.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.recipe import (
    BuildRecipeRequestSchema,
    RecipeSchema,
)
from nutriroll.db.repositories.components import ComponentRepository
from nutriroll.db.repositories.profile import UserProfileRepository
from nutriroll.db.session import get_session
from nutriroll.domain.component import Component
from nutriroll.domain.recipe import (
    IncompatibleForcedMethodError,
    Recipe,
    RecipeBlock,
    RecipeStep,
    build_recipe,
)
from nutriroll.domain.recipe_step_polish import RecipeStepPolish
from nutriroll.domain.llm_config import LLMFeatureDisabledError, resolve_runtime_llm_config

router = APIRouter(prefix="/v1/recipe", tags=["recipe"])

PolishTone = Literal["concise", "enthusiastic", "calm", "professional"]


def _flatten_steps(recipe: Recipe) -> list[RecipeStep]:
    return [step for block in recipe.blocks for step in block.steps]


def _with_polished_steps(recipe: Recipe, polished_steps: list[RecipeStep]) -> Recipe:
    if not polished_steps:
        return recipe

    next_index = 0
    blocks: list[RecipeBlock] = []
    for block in recipe.blocks:
        block_count = len(block.steps)
        next_steps = tuple(polished_steps[next_index : next_index + block_count])
        blocks.append(replace(block, steps=next_steps))
        next_index += block_count
    return replace(recipe, blocks=tuple(blocks))


@router.post(
    "",
    response_model=RecipeSchema,
    summary="Build a recipe from chosen components",
)
async def build_recipe_endpoint(
    payload: BuildRecipeRequestSchema,
    polish: PolishTone | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> RecipeSchema:
    repo = ComponentRepository(session)
    components: list[Component] = []
    for component_id in payload.component_ids:
        component = await repo.get(component_id)
        if component is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "component_not_found",
                    "component_id": str(component_id),
                },
            )
        components.append(component)
    try:
        recipe = build_recipe(components, payload.forced_methods or None)
    except IncompatibleForcedMethodError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "incompatible_forced_method",
                "component_id": str(exc.component.id),
                "method": exc.method.value,
            },
        ) from exc
    polished = False
    if polish is not None:
        stored_llm = await UserProfileRepository(session).get_stored_llm_config()
        step_polisher = RecipeStepPolish(runtime_config=resolve_runtime_llm_config(stored_llm))
        raw_steps = _flatten_steps(recipe)
        try:
            polished_steps = await step_polisher.polish_steps(raw_steps, tone=polish)
        except LLMFeatureDisabledError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "LLM_FEATURE_DISABLED", "feature": exc.feature},
            ) from exc
        if step_polisher.last_applied:
            recipe = _with_polished_steps(recipe, polished_steps)
            polished = True
    return RecipeSchema.from_domain(recipe, polished=polished)


__all__ = ["router"]
