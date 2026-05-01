"""Pydantic schemas for the History API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.domain.history import HistoryEvent, HistoryEventKind
from nutriroll.domain.weekly_recap import Recap, RecapStats


class HistoryEventBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: HistoryEventKind
    bowl_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class HistoryEventCreate(HistoryEventBase):
    pass


class HistoryEventRead(HistoryEventBase):
    id: UUID
    created_at: datetime | None = None

    @classmethod
    def from_domain(cls, e: HistoryEvent) -> HistoryEventRead:
        return cls(
            id=e.id,
            kind=e.kind,
            bowl_id=e.bowl_id,
            payload=dict(e.payload),
            created_at=e.created_at,
        )


class HistoryList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[HistoryEventRead]
    total: int


class RecapStatsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meals_cooked: int
    spent_eur: float
    avg_kcal: float | None
    top_components: list[str]
    longest_streak: int
    new_foods_tried: int

    @classmethod
    def from_domain(cls, stats: RecapStats) -> RecapStatsSchema:
        return cls(
            meals_cooked=stats.meals_cooked,
            spent_eur=stats.spent_eur,
            avg_kcal=stats.avg_kcal,
            top_components=list(stats.top_components),
            longest_streak=stats.longest_streak,
            new_foods_tried=stats.new_foods_tried,
        )


class RecapSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_text: str
    stats: RecapStatsSchema
    suggestions: list[str]

    @classmethod
    def from_domain(cls, recap: Recap) -> RecapSchema:
        return cls(
            summary_text=recap.summary_text,
            stats=RecapStatsSchema.from_domain(recap.stats),
            suggestions=list(recap.suggestions),
        )


class HistoryRecapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    week_start: date
    recap: RecapSchema | None
    cached: bool = False


__all__ = [
    "HistoryEventBase",
    "HistoryEventCreate",
    "HistoryEventRead",
    "HistoryList",
    "HistoryRecapResponse",
    "RecapSchema",
    "RecapStatsSchema",
]
