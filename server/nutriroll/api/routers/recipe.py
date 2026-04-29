"""Recipe endpoints, mounted at /v1/recipe.

Pure recipe construction over the chosen components of a rolled bowl.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.recipe import (
    BuildRecipeRequestSchema,
    RecipeSchema,
)
from nutriroll.db.repositories.components import ComponentRepository
from nutriroll.db.session import get_session
from nutriroll.domain.component import Component
from nutriroll.domain.recipe import (
    IncompatibleForcedMethodError,
    build_recipe,
)

router = APIRouter(prefix="/v1/recipe", tags=["recipe"])


@router.post(
    "",
    response_model=RecipeSchema,
    summary="Build a recipe from chosen components",
)
async def build_recipe_endpoint(
    payload: BuildRecipeRequestSchema,
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
    return RecipeSchema.from_domain(recipe)


__all__ = ["router"]
