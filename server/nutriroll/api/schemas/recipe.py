"""Pydantic v2 schemas for the Recipe HTTP API."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.api.schemas.component import ComponentRead
from nutriroll.domain.component import Category, CookingMethod
from nutriroll.domain.recipe import Recipe, RecipeBlock, RecipeStep


class RecipeStepSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    offset_min: int = 0
    duration_min: int | None = None

    @classmethod
    def from_domain(cls, step: RecipeStep) -> RecipeStepSchema:
        return cls(
            text=step.text,
            offset_min=step.offset_min,
            duration_min=step.duration_min,
        )


class RecipeBlockSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    title: str
    method: CookingMethod
    components: list[ComponentRead]
    total_minutes: int
    can_cook_with_others: bool
    steps: list[RecipeStepSchema]

    @classmethod
    def from_domain(cls, block: RecipeBlock) -> RecipeBlockSchema:
        return cls(
            category=block.category,
            title=block.title,
            method=block.method,
            components=[ComponentRead.from_domain(c) for c in block.components],
            total_minutes=block.total_minutes,
            can_cook_with_others=block.can_cook_with_others,
            steps=[RecipeStepSchema.from_domain(s) for s in block.steps],
        )


class RecipeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocks: list[RecipeBlockSchema]
    total_minutes: int
    polished: bool = False

    @classmethod
    def from_domain(cls, recipe: Recipe, *, polished: bool = False) -> RecipeSchema:
        return cls(
            blocks=[RecipeBlockSchema.from_domain(b) for b in recipe.blocks],
            total_minutes=recipe.total_minutes,
            polished=polished,
        )


class BuildRecipeRequestSchema(BaseModel):
    """Build a Recipe from a list of chosen component ids.

    The server reloads the components by id (cheap — pool is small) so
    the client doesn't have to round-trip the entire bowl payload.
    """

    model_config = ConfigDict(extra="forbid")

    component_ids: list[UUID] = Field(min_length=1, max_length=16)
    forced_methods: dict[Category, CookingMethod] = Field(
        default_factory=dict[Category, CookingMethod]
    )


__all__ = [
    "BuildRecipeRequestSchema",
    "RecipeBlockSchema",
    "RecipeSchema",
    "RecipeStepSchema",
]
