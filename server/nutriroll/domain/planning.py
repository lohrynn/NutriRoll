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
    created_at: datetime | None = None
    updated_at: datetime | None = None
