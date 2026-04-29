"""SQLAlchemy ORM model for the components table."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from nutriroll.db.base import Base


class ComponentRow(Base):
    """Persistence row for a Component.

    Cross-database friendly: arrays and the cooking-methods spec are stored as
    JSON (works on Postgres JSONB and SQLite JSON1). SQLAlchemy's `Uuid` type
    handles native UUIDs on Postgres and CHAR(32) on SQLite transparently.
    """

    __tablename__ = "components"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    default_portion_value: Mapped[float] = mapped_column(Float, nullable=False)
    default_portion_unit: Mapped[str] = mapped_column(String(8), nullable=False)

    kcal_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fiber_per_100g: Mapped[float] = mapped_column(Float, nullable=False)

    default_cooking_method: Mapped[str] = mapped_column(String(32), nullable=False)
    cooking_methods: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)

    flavor_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    dietary_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allergens: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blacklisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
