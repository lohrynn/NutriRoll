"""create singleton user_profile

Revision ID: 0004_user_profile
Revises: 0003_planning
Create Date: 2026-06-15

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_user_profile"
down_revision: str | None = "0003_planning"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_profile",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("dietary_mode", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "allergens",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("default_time_budget_min", sa.Integer(), nullable=True),
        sa.Column("goal", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column(
            "onboarded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_profile")
