"""Pydantic schemas for the singleton user profile."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.api.schemas.roll import MacroTargetSchema
from nutriroll.domain.llm_config import KNOWN_FEATURES, KNOWN_PROVIDERS, LLMConfig
from nutriroll.domain.equipment import Equipment
from nutriroll.domain.profile import UserProfile
from nutriroll.domain.roll import MacroMode, MacroTargets

DietaryMode = Literal["", "vegan", "vegetarian", "pescatarian"]
LLMProviderSchema = Literal["openai", "anthropic", "google", "ollama", "custom"]
LLMFeatureSchema = Literal[
    "component_creation",
    "prompt_rolls",
    "recipe_polish",
    "weekly_recaps",
]


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
    equipment: list[Equipment]
    """Phase 13. Hardware the user owns (e.g. ``["oven", "stovetop"]``).
    Empty = "all available" (back-compat)."""
    llm_weekly_recap_enabled: bool = False
    """Phase 15. Whether AI-generated weekly recap copy is enabled."""

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
            equipment=list(p.equipment),
            llm_weekly_recap_enabled=p.llm_weekly_recap_enabled,
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
    equipment: list[Equipment] = Field(default_factory=list[Equipment], max_length=32)
    """Phase 13. Hardware the user owns. Validated via the Equipment enum."""
    llm_weekly_recap_enabled: bool = False
    """Phase 15. Opt-in for AI-generated weekly recap copy."""

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
            equipment=tuple(self.equipment),
            llm_weekly_recap_enabled=self.llm_weekly_recap_enabled,
        )


class LLMConfigRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled_features: list[LLMFeatureSchema] = Field(default_factory=list)
    provider: LLMProviderSchema = "openai"
    model: str = "gpt-4o-mini"
    api_key_set: bool = False

    @classmethod
    def from_domain(cls, config: LLMConfig) -> "LLMConfigRead":
        return cls(
            enabled_features=config.enabled_features,  # type: ignore[arg-type]
            provider=config.provider,  # type: ignore[arg-type]
            model=config.model,
            api_key_set=config.api_key_set,
        )


class LLMConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled_features: list[LLMFeatureSchema] | None = None
    provider: LLMProviderSchema | None = None
    model: str | None = Field(default=None, max_length=256)
    api_key: str | None = Field(default=None, max_length=4096)

    def to_partial(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        if self.enabled_features is not None:
            payload["enabled_features"] = list(self.enabled_features)
        if self.provider is not None:
            payload["provider"] = self.provider
        if self.model is not None:
            payload["model"] = self.model.strip()
        if self.api_key is not None:
            payload["api_key"] = self.api_key
        return payload


__all__ = [
    "DietaryMode",
    "KNOWN_FEATURES",
    "KNOWN_PROVIDERS",
    "LLMConfigRead",
    "LLMConfigUpdate",
    "UserProfileRead",
    "UserProfileUpdate",
]
