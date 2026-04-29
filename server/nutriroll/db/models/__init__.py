"""SQLAlchemy ORM models. Importing this package registers them on Base.metadata."""

from nutriroll.db.models.component import ComponentRow

__all__ = ["ComponentRow"]
