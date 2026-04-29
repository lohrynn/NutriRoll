"""History event domain — vision §8 History / Meal log.

Append-only log of typed events. Scope-narrow on purpose: stores the
``payload`` as a structured JSON dict so callers can attach the bowl
snapshot, rating values, etc. without forcing one shape per event kind.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class HistoryEventKind(StrEnum):
    ROLLED = "rolled"
    COOKED = "cooked"
    SAVED = "saved"
    RATED = "rated"
    DISCARDED = "discarded"


@dataclass(frozen=True, slots=True)
class HistoryEvent:
    id: UUID
    kind: HistoryEventKind
    bowl_id: UUID | None
    """Optional correlation id; all events for the same bowl share this."""
    payload: dict[str, Any] = field(default_factory=dict[str, Any])
    created_at: datetime | None = None
