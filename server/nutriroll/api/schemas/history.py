"""Pydantic schemas for the History API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nutriroll.domain.history import HistoryEvent, HistoryEventKind


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


__all__ = [
    "HistoryEventBase",
    "HistoryEventCreate",
    "HistoryEventRead",
    "HistoryList",
]
