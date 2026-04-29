"""SQLAlchemy ORM model for the singleton user profile."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from nutriroll.db.base import Base


class UserProfileRow(Base):
    """Singleton table — always exactly one row, with ``id == 1``."""

    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    dietary_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    allergens: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    default_time_budget_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goal: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    locale: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    onboarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    roll_weights: Mapped[dict[Any, Any] | None] = mapped_column(JSON, nullable=True, default=None)
    """JSON map of weight name → float. NULL = user hasn't set custom weights.
    Stored as JSONB on Postgres (see migration 0007); JSON here for SQLite test compat."""
    default_macro_targets: Mapped[dict[Any, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    """JSON map of macro name → ``{value, mode}``. NULL = user hasn't set defaults.
    Stored as JSONB on Postgres (see migration 0008); JSON here for SQLite test compat."""
