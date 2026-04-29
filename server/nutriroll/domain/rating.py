"""Rating domain — vision §3 Rate a Meal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Rating:
    """A user rating, scoped to a bowl and optionally one component within it.

    Per-component rating > meal-level rating when both exist (vision
    §"Recommendation learning"). Both shapes are stored side-by-side; the
    consumer decides how to weight them.
    """

    id: UUID
    bowl_id: UUID
    """Client-generated id correlating ratings to a particular rolled bowl."""
    component_id: UUID | None
    score: int
    comment: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.score <= 5:
            raise ValueError(f"score must be in 1..5, got {self.score}")
