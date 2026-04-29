"""Pydantic schemas for the saved + planned meals APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nutriroll.domain.planning import MealSlot, PlannedMeal, PlannedStatus, SavedMeal


class SavedMealCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    bowl_snapshot: dict[str, Any] = Field(default_factory=dict)
    notes: str = Field(default="", max_length=1024)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v


class SavedMealRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    bowl_snapshot: dict[str, Any]
    notes: str
    created_at: datetime | None = None

    @classmethod
    def from_domain(cls, m: SavedMeal) -> SavedMealRead:
        return cls(
            id=m.id,
            name=m.name,
            bowl_snapshot=dict(m.bowl_snapshot),
            notes=m.notes,
            created_at=m.created_at,
        )


class SavedMealList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SavedMealRead]
    total: int


class PlannedMealCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planned_for: date
    slot: MealSlot
    bowl_snapshot: dict[str, Any] = Field(default_factory=dict)
    status: PlannedStatus = PlannedStatus.PLANNED
    notes: str = Field(default="", max_length=1024)
    portions_total: int = Field(default=1, ge=1, le=14)
    """Phase 12. ``1`` = single meal; >1 = meal-prep batch."""


class PlannedMealUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planned_for: date | None = None
    slot: MealSlot | None = None
    status: PlannedStatus | None = None
    notes: str | None = Field(default=None, max_length=1024)


class PlannedMealRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    planned_for: date
    slot: MealSlot
    bowl_snapshot: dict[str, Any]
    status: PlannedStatus
    notes: str
    portions_total: int
    portions_remaining: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_domain(cls, m: PlannedMeal) -> PlannedMealRead:
        return cls(
            id=m.id,
            planned_for=m.planned_for,
            slot=m.slot,
            bowl_snapshot=dict(m.bowl_snapshot),
            status=m.status,
            notes=m.notes,
            portions_total=m.portions_total,
            portions_remaining=m.portions_remaining,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


class PlannedMealList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PlannedMealRead]
    total: int


__all__ = [
    "PlannedMealCreate",
    "PlannedMealList",
    "PlannedMealRead",
    "PlannedMealUpdate",
    "SavedMealCreate",
    "SavedMealList",
    "SavedMealRead",
]
