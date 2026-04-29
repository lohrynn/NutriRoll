"""create components table

Revision ID: 0001_components
Revises:
Create Date: 2026-04-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_components"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("default_portion_value", sa.Float(), nullable=False),
        sa.Column("default_portion_unit", sa.String(length=8), nullable=False),
        sa.Column("kcal_per_100g", sa.Float(), nullable=False),
        sa.Column("carbs_per_100g", sa.Float(), nullable=False),
        sa.Column("protein_per_100g", sa.Float(), nullable=False),
        sa.Column("fat_per_100g", sa.Float(), nullable=False),
        sa.Column("fiber_per_100g", sa.Float(), nullable=False),
        sa.Column("default_cooking_method", sa.String(length=32), nullable=False),
        sa.Column(
            "cooking_methods",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "flavor_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "dietary_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "allergens", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("shelf_life_days", sa.Integer(), nullable=True),
        sa.Column(
            "blacklisted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("name", name="uq_components_name"),
    )
    op.create_index("ix_components_category", "components", ["category"])


def downgrade() -> None:
    op.drop_index("ix_components_category", table_name="components")
    op.drop_table("components")
