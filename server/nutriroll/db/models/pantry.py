"""SQLAlchemy ORM model for pantry_items."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from nutriroll.db.base import Base


class PantryItemRow(Base):
    __tablename__ = "pantry_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    component_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(8), nullable=False)
    opened: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
