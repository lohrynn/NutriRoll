"""add seasonal_availability to components

Revision ID: 0005_component_seasonal_availability
Revises: 0004_user_profile
Create Date: 2026-04-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_component_seasonal_availability"
down_revision: str | None = "0004_user_profile"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "components",
        sa.Column("seasonal_availability", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("components", "seasonal_availability")
