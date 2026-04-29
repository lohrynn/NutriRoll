"""Pydantic v2 schemas for the Roll HTTP API.

Mirrors `nutriroll.domain.roll` types over the wire. Keeps the domain
layer framework-free; conversions happen at the boundary.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.api.schemas.component import ComponentRead
from nutriroll.domain.component import Category, CookingMethod
from nutriroll.domain.roll import (
    ChosenComponent,
    FeatureWeights,
    RolledBowl,
    RollRequest,
    SlotSpec,
)


class SlotSpecSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    count: Annotated[int, Field(ge=0, le=8)] = 1


class FeatureWeightsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taste_match: float = Field(default=0.30, ge=0)
    novelty: float = Field(default=0.20, ge=0)
    price_fit: float = Field(default=0.20, ge=0)
    nutrition_fit: float = Field(default=0.15, ge=0)
    time_fit: float = Field(default=0.10, ge=0)
    pantry_bonus: float = Field(default=0.05, ge=0)


class RollRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slots: list[SlotSpecSchema] = Field(min_length=1, max_length=8)
    dietary_mode: str | None = Field(default=None, max_length=32)
    allergens_excluded: list[str] = Field(default_factory=list, max_length=32)
    blacklisted_ids: list[UUID] = Field(default_factory=list[UUID])
    time_budget_min: int | None = Field(default=None, ge=0, le=600)
    forced_methods: dict[Category, CookingMethod] = Field(
        default_factory=dict[Category, CookingMethod]
    )
    recent_component_ids: list[UUID] = Field(default_factory=list[UUID])
    weights: FeatureWeightsSchema = Field(default_factory=FeatureWeightsSchema)
    temperature: float = Field(default=0.5, gt=0, le=5)
    seed: int | None = None

    def to_domain(self) -> RollRequest:
        return RollRequest(
            slots=tuple(
                SlotSpec(category=s.category, count=s.count) for s in self.slots
            ),
            dietary_mode=self.dietary_mode,
            allergens_excluded=frozenset(self.allergens_excluded),
            blacklisted_ids=frozenset(self.blacklisted_ids),
            time_budget_min=self.time_budget_min,
            forced_methods=dict(self.forced_methods),
            recent_component_ids=frozenset(self.recent_component_ids),
            weights=FeatureWeights(
                taste_match=self.weights.taste_match,
                novelty=self.weights.novelty,
                price_fit=self.weights.price_fit,
                nutrition_fit=self.weights.nutrition_fit,
                time_fit=self.weights.time_fit,
                pantry_bonus=self.weights.pantry_bonus,
            ),
            temperature=self.temperature,
            seed=self.seed,
        )


class RolledSlotSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component: ComponentRead
    score: float
    reasons: list[str]

    @classmethod
    def from_domain(cls, choice: ChosenComponent) -> RolledSlotSchema:
        return cls(
            component=ComponentRead.from_domain(choice.component),
            score=choice.score,
            reasons=list(choice.reasons),
        )


class RolledBowlSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slots: list[RolledSlotSchema]

    @classmethod
    def from_domain(cls, bowl: RolledBowl) -> RolledBowlSchema:
        return cls(slots=[RolledSlotSchema.from_domain(s) for s in bowl.slots])


class RerollSlotRequestSchema(BaseModel):
    """Re-roll a single slot. The client keeps the rest of the bowl
    locally and splices in the returned slot. Server stays stateless.
    """

    model_config = ConfigDict(extra="forbid")

    request: RollRequestSchema
    slot_category: Category
    exclude_component_ids: list[UUID] = Field(default_factory=list[UUID])


__all__ = [
    "FeatureWeightsSchema",
    "RerollSlotRequestSchema",
    "RollRequestSchema",
    "RolledBowlSchema",
    "RolledSlotSchema",
    "SlotSpecSchema",
]
