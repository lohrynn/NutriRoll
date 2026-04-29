"""Declarative base for SQLAlchemy models. Models are added in Phase 1+."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


__all__ = ["Base"]
