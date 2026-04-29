"""add equipment JSONB column to user_profile

Revision ID: 0010_profile_equipment
Revises: 0009_planned_meal_portions
Create Date: 2026-05-13

Phase 13. Stores the user's owned hardware so the roll algorithm can drop
components whose every cooking method requires unavailable equipment. JSONB
on Postgres; the ORM uses plain ``JSON`` so the column type also works on
SQLite for the test suite (mirrors ``roll_weights`` and
``default_macro_targets``).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_profile_equipment"
down_revision: str = "0009_planned_meal_portions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_profile",
        sa.Column(
            "equipment",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_profile", "equipment")
