"""Pydantic schemas for the Ratings API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.domain.rating import Rating


class RatingBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bowl_id: UUID
    component_id: UUID | None = None
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class RatingCreate(RatingBase):
    pass


class RatingRead(RatingBase):
    id: UUID
    created_at: datetime | None = None

    @classmethod
    def from_domain(cls, r: Rating) -> RatingRead:
        return cls(
            id=r.id,
            bowl_id=r.bowl_id,
            component_id=r.component_id,
            score=r.score,
            comment=r.comment,
            created_at=r.created_at,
        )


class RatingList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RatingRead]
    total: int


__all__ = ["RatingBase", "RatingCreate", "RatingList", "RatingRead"]
