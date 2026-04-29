"""Pydantic schemas for the singleton user profile."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.domain.profile import UserProfile

DietaryMode = Literal["", "vegan", "vegetarian", "pescatarian"]


class UserProfileRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dietary_mode: DietaryMode
    allergens: list[str]
    default_time_budget_min: int | None
    goal: str
    locale: str
    onboarded: bool

    @classmethod
    def from_domain(cls, p: UserProfile) -> UserProfileRead:
        return cls(
            dietary_mode=p.dietary_mode,  # type: ignore[arg-type]
            allergens=list(p.allergens),
            default_time_budget_min=p.default_time_budget_min,
            goal=p.goal,
            locale=p.locale,
            onboarded=p.onboarded,
        )


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dietary_mode: DietaryMode = ""
    allergens: list[str] = Field(default_factory=list)
    default_time_budget_min: int | None = Field(default=None, gt=0)
    goal: str = Field(default="", max_length=256)
    locale: str = Field(default="en", max_length=8)
    onboarded: bool = False

    def to_domain(self) -> UserProfile:
        return UserProfile(
            dietary_mode=self.dietary_mode,
            allergens=tuple(self.allergens),
            default_time_budget_min=self.default_time_budget_min,
            goal=self.goal,
            locale=self.locale,
            onboarded=self.onboarded,
        )


__all__ = ["DietaryMode", "UserProfileRead", "UserProfileUpdate"]
