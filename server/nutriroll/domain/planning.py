"""Saved meals + Planned meals — vision §2 / §10 / §11.

A *SavedMeal* is a snapshot of a rolled bowl that the user wants to keep
in their personal collection (favorites). A *PlannedMeal* schedules a
bowl for a specific day and slot (breakfast/lunch/dinner/snack). The full
bowl is stored as a JSON snapshot so future component edits do not retro-
actively mutate the planning history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class MealSlot(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class PlannedStatus(StrEnum):
    PLANNED = "planned"
    SHOPPED = "shopped"
    COOKED = "cooked"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class SavedMeal:
    id: UUID
    name: str
    bowl_snapshot: dict[str, Any] = field(default_factory=dict[str, Any])
    notes: str = ""
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("SavedMeal.name must be non-empty")


@dataclass(frozen=True, slots=True)
class PlannedMeal:
    id: UUID
    planned_for: date
    slot: MealSlot
    bowl_snapshot: dict[str, Any] = field(default_factory=dict[str, Any])
    status: PlannedStatus = PlannedStatus.PLANNED
    notes: str = ""
    portions_total: int = 1
    """Phase 12. How many portions this entry was prepped for. ``1`` for a
    classic single-meal plan; >1 for a meal-prep batch (e.g. cook 4 lunches at
    once). Constant across the lifetime of the row."""
    portions_remaining: int = 1
    """Phase 12. Decrements by 1 each time the user marks a portion eaten.
    When it reaches 0 the planner UI moves the entry to ``cooked``."""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.portions_total < 1 or self.portions_total > 14:
            raise ValueError(f"portions_total must be in [1, 14], got {self.portions_total}")
        if self.portions_remaining < 0 or self.portions_remaining > self.portions_total:
            raise ValueError(
                "portions_remaining must be in [0, portions_total], "
                f"got {self.portions_remaining}/{self.portions_total}"
            )
