"""Pantry domain — value objects for items the user has at home.

Framework-free; conversion happens at the schema/repository boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from nutriroll.domain.component import PortionUnit


@dataclass(frozen=True, slots=True)
class PantryItem:
    """A quantity of one component the user has on hand."""

    id: UUID
    component_id: UUID
    quantity: float
    unit: PortionUnit
    opened: bool = False
    expires_at: date | None = None

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError(f"quantity must be >= 0, got {self.quantity}")
