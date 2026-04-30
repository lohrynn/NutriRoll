"""Pydantic v2 schemas for the Roll HTTP API.

Mirrors `nutriroll.domain.roll` types over the wire. Keeps the domain
layer framework-free; conversions happen at the boundary.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.api.schemas.component import ComponentRead
from nutriroll.domain.component import Category, CookingMethod
from nutriroll.domain.direction import (
    CUISINE_BOOSTS,
    MOOD_BOOSTS,
    Direction,
    FlavorAxes,
    translate,
)
from nutriroll.domain.equipment import Equipment
from nutriroll.domain.roll import (
    ChosenComponent,
    FeatureWeights,
    MacroTarget,
    MacroTargets,
    RolledBowl,
    RollRequest,
    SlotSpec,
)


class SlotSpecSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    count: Annotated[int, Field(ge=0, le=8)] = 1


def _collect_extra_weights(weights: FeatureWeightsSchema) -> dict[str, float]:
    """Coerce `model_extra` into a numeric dict for ``FeatureWeights.extra_weights``."""
    out: dict[str, float] = {}
    for key, raw in (weights.model_extra or {}).items():
        try:
            out[key] = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"extra weight {key!r} must be numeric") from exc
    return out


class FeatureWeightsSchema(BaseModel):
    # ``extra="allow"`` lets clients send forward-compat scoring weights
    # (e.g. ``seasonal_bonus``, ``eco_score``) ahead of the algorithm gaining
    # a feature for them. Unknown keys flow through to
    # ``FeatureWeights.extra_weights`` and are silently ignored by
    # ``score_component()`` until a matching feature lands. See
    # modularity-audit M6.
    model_config = ConfigDict(extra="allow")

    taste_match: float = Field(default=0.30, ge=0)
    novelty: float = Field(default=0.20, ge=0)
    price_fit: float = Field(default=0.20, ge=0)
    nutrition_fit: float = Field(default=0.15, ge=0)
    time_fit: float = Field(default=0.10, ge=0)
    pantry_bonus: float = Field(default=0.05, ge=0)
    direction_match: float = Field(default=0.25, ge=0)
    macro_target_fit: float = Field(default=0.5, ge=0)


class FlavorAxesSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bold_to_mild: float = Field(default=0.0, ge=-1, le=1)
    heavy_to_light: float = Field(default=0.0, ge=-1, le=1)


class MacroTargetSchema(BaseModel):
    """A single per-portion macro target (Phase 11)."""

    model_config = ConfigDict(extra="forbid")

    value: float = Field(ge=0)
    mode: Literal["target", "min", "max"] = "target"

    def to_domain(self) -> MacroTarget:
        return MacroTarget(value=self.value, mode=self.mode)

    @classmethod
    def from_domain(cls, t: MacroTarget) -> MacroTargetSchema:
        return cls(value=t.value, mode=t.mode)


class MacroTargetsSchema(BaseModel):
    """Per-portion macro targets (Phase 11).

    All fields optional. ``extra="allow"`` lets forward-compat macros
    (e.g. ``sodium_mg``) round-trip without a schema bump — mirrors the
    pattern on :class:`MacrosSchema` (modularity-audit M1).
    """

    model_config = ConfigDict(extra="allow")

    kcal: MacroTargetSchema | None = None
    protein_g: MacroTargetSchema | None = None
    carbs_g: MacroTargetSchema | None = None
    fat_g: MacroTargetSchema | None = None
    fiber_g: MacroTargetSchema | None = None

    def to_domain(self) -> MacroTargets:
        mapping: dict[str, MacroTarget] = {}
        for key in MacroTargets.WELL_KNOWN_KEYS:
            v: MacroTargetSchema | None = getattr(self, key)
            if v is not None:
                mapping[key] = v.to_domain()
        for key, raw in (self.model_extra or {}).items():
            if raw is None:
                continue
            try:
                parsed = MacroTargetSchema.model_validate(raw)
            except Exception as exc:
                raise ValueError(f"extra macro target {key!r} is invalid") from exc
            mapping[key] = parsed.to_domain()
        return MacroTargets.from_mapping(mapping)

    @classmethod
    def from_domain(cls, t: MacroTargets) -> MacroTargetsSchema:
        kwargs: dict[str, MacroTargetSchema | None] = {
            k: None for k in MacroTargets.WELL_KNOWN_KEYS
        }
        extras: dict[str, MacroTargetSchema] = {}
        for key, target in t.as_mapping().items():
            if key in MacroTargets.WELL_KNOWN_KEYS:
                kwargs[key] = MacroTargetSchema.from_domain(target)
            else:
                extras[key] = MacroTargetSchema.from_domain(target)
        return cls(**kwargs, **extras)


class DirectionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cuisines: list[str] = Field(default_factory=list, max_length=8)
    moods: list[str] = Field(default_factory=list, max_length=8)
    axes: FlavorAxesSchema = Field(default_factory=FlavorAxesSchema)

    def to_domain(self) -> Direction:
        for c in self.cuisines:
            if c not in CUISINE_BOOSTS:
                raise ValueError(f"unknown cuisine: {c}")
        for m in self.moods:
            if m not in MOOD_BOOSTS:
                raise ValueError(f"unknown mood: {m}")
        return Direction(
            cuisines=tuple(self.cuisines),
            moods=tuple(self.moods),
            axes=FlavorAxes(
                bold_to_mild=self.axes.bold_to_mild,
                heavy_to_light=self.axes.heavy_to_light,
            ),
        )


class RollRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slots: list[SlotSpecSchema] = Field(min_length=1, max_length=8)
    prompt: str | None = Field(default=None, max_length=512)
    dietary_mode: str | None = Field(default=None, max_length=32)
    allergens_excluded: list[str] = Field(default_factory=list, max_length=32)
    blacklisted_ids: list[UUID] = Field(default_factory=list[UUID])
    time_budget_min: int | None = Field(default=None, ge=0, le=600)
    forced_methods: dict[Category, CookingMethod] = Field(
        default_factory=dict[Category, CookingMethod]
    )
    recent_component_ids: list[UUID] = Field(default_factory=list[UUID])
    weights: FeatureWeightsSchema = Field(default_factory=FeatureWeightsSchema)
    direction: DirectionSchema = Field(default_factory=DirectionSchema)
    tag_boosts: dict[str, float] = Field(default_factory=dict[str, float])
    macro_targets: MacroTargetsSchema | None = None
    portions: int = Field(default=1, ge=1, le=14)
    available_equipment: list[Equipment] = Field(default_factory=list[Equipment], max_length=32)
    """Phase 13 — the user's owned hardware (e.g. ``["oven", "stovetop"]``).
    Empty = "all available" (back-compat). Validated against the
    :class:`Equipment` enum during ``to_domain()``."""
    temperature: float = Field(default=0.5, gt=0, le=5)
    seed: int | None = None

    def to_domain(self) -> RollRequest:
        # Direction translates into per-tag boosts, then user-provided
        # explicit `tag_boosts` (rare, mostly tests) layer on top.
        boosts = translate(self.direction.to_domain())
        for tag, boost in self.tag_boosts.items():
            boosts[tag] = boosts.get(tag, 0.0) + boost
        return RollRequest(
            slots=tuple(SlotSpec(category=s.category, count=s.count) for s in self.slots),
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
                direction_match=self.weights.direction_match,
                macro_target_fit=self.weights.macro_target_fit,
                extra_weights=_collect_extra_weights(self.weights),
            ),
            tag_boosts=boosts,
            macro_targets=self.macro_targets.to_domain() if self.macro_targets else None,
            portions=self.portions,
            available_equipment=frozenset(self.available_equipment),
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
    "DirectionSchema",
    "FeatureWeightsSchema",
    "FlavorAxesSchema",
    "MacroTargetSchema",
    "MacroTargetsSchema",
    "RerollSlotRequestSchema",
    "RollRequestSchema",
    "RolledBowlSchema",
    "RolledSlotSchema",
    "SlotSpecSchema",
]
