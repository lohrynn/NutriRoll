"""Pydantic schemas for the singleton user profile."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.api.schemas.roll import MacroTargetSchema
from nutriroll.domain.profile import UserProfile
from nutriroll.domain.roll import MacroMode, MacroTargets

DietaryMode = Literal["", "vegan", "vegetarian", "pescatarian"]


class UserProfileRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dietary_mode: DietaryMode
    allergens: list[str]
    default_time_budget_min: int | None
    goal: str
    locale: str
    onboarded: bool
    roll_weights: dict[str, float]
    """Per-user scoring weight overrides. Empty dict = use server defaults."""
    default_macro_targets: dict[str, MacroTargetSchema]
    """Phase 11. Per-portion macro targets the user wants by default. Empty
    dict = no preference; the Roll page form starts blank."""

    @classmethod
    def from_domain(cls, p: UserProfile) -> UserProfileRead:
        targets = p.macro_targets()
        targets_dict: dict[str, MacroTargetSchema] = {}
        if targets is not None:
            for key, target in targets.as_mapping().items():
                targets_dict[key] = MacroTargetSchema.from_domain(target)
        return cls(
            dietary_mode=p.dietary_mode,  # type: ignore[arg-type]
            allergens=list(p.allergens),
            default_time_budget_min=p.default_time_budget_min,
            goal=p.goal,
            locale=p.locale,
            onboarded=p.onboarded,
            roll_weights=dict(p.roll_weights),
            default_macro_targets=targets_dict,
        )


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dietary_mode: DietaryMode = ""
    allergens: list[str] = Field(default_factory=list)
    default_time_budget_min: int | None = Field(default=None, gt=0)
    goal: str = Field(default="", max_length=256)
    locale: str = Field(default="en", max_length=8)
    onboarded: bool = False
    roll_weights: dict[str, float] = Field(default_factory=dict)
    """Per-user scoring weight overrides sent from the Settings UI."""
    default_macro_targets: dict[str, MacroTargetSchema] = Field(default_factory=dict)
    """Phase 11. Per-portion macro targets the user wants by default."""

    def to_domain(self) -> UserProfile:
        # Validate macro targets via the domain helper to keep the rules in
        # one place; then flatten to the (name, value, mode) tuple form the
        # frozen dataclass needs.
        if self.default_macro_targets:
            mapping = {k: v.to_domain() for k, v in self.default_macro_targets.items()}
            domain_targets = MacroTargets.from_mapping(mapping)
            target_triples: tuple[tuple[str, float, MacroMode], ...] = tuple(
                (key, target.value, target.mode)
                for key, target in domain_targets.as_mapping().items()
            )
        else:
            target_triples = ()
        return UserProfile(
            dietary_mode=self.dietary_mode,
            allergens=tuple(self.allergens),
            default_time_budget_min=self.default_time_budget_min,
            goal=self.goal,
            locale=self.locale,
            onboarded=self.onboarded,
            roll_weights=tuple(self.roll_weights.items()),
            default_macro_targets=target_triples,
        )


__all__ = ["DietaryMode", "UserProfileRead", "UserProfileUpdate"]
