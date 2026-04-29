"""Store + price domain — vision §9 Supermarket."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Store:
    """A supermarket the user shops at."""

    id: UUID
    name: str
    location: str | None = None
    is_primary: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must be non-empty")


@dataclass(frozen=True, slots=True)
class SupermarketPrice:
    """A single packaged-good price at one store, for one component."""

    id: UUID
    store_id: UUID
    component_id: UUID
    pack_size: float
    pack_price: float
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.pack_size <= 0:
            raise ValueError("pack_size must be > 0")
        if self.pack_price < 0:
            raise ValueError("pack_price must be >= 0")
