"""collapse macro columns into JSONB

Revision ID: 0006_components_macros_jsonb
Revises: 0005_component_seasonal_availability
Create Date: 2026-04-29

Replaces the five flat ``*_per_100g`` Float columns with a single
``macros`` JSONB column. Existing data is migrated in-place. See
``docs/modularity-audit.md`` M1 for context.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_components_macros_jsonb"
down_revision: str | None = "0005_component_seasonal_availability"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "components",
        sa.Column(
            "macros",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Backfill from the legacy flat columns. ``jsonb_build_object`` keeps
    # numeric typing intact.
    op.execute(
        """
        UPDATE components
        SET macros = jsonb_build_object(
            'kcal', kcal_per_100g,
            'carbs_g', carbs_per_100g,
            'protein_g', protein_per_100g,
            'fat_g', fat_per_100g,
            'fiber_g', fiber_per_100g
        )
        """
    )

    op.alter_column("components", "macros", nullable=False)

    op.drop_column("components", "kcal_per_100g")
    op.drop_column("components", "carbs_per_100g")
    op.drop_column("components", "protein_per_100g")
    op.drop_column("components", "fat_per_100g")
    op.drop_column("components", "fiber_per_100g")


def downgrade() -> None:
    op.add_column(
        "components",
        sa.Column("kcal_per_100g", sa.Float(), nullable=True),
    )
    op.add_column(
        "components",
        sa.Column("carbs_per_100g", sa.Float(), nullable=True),
    )
    op.add_column(
        "components",
        sa.Column("protein_per_100g", sa.Float(), nullable=True),
    )
    op.add_column(
        "components",
        sa.Column("fat_per_100g", sa.Float(), nullable=True),
    )
    op.add_column(
        "components",
        sa.Column("fiber_per_100g", sa.Float(), nullable=True),
    )

    op.execute(
        """
        UPDATE components
        SET kcal_per_100g = COALESCE((macros->>'kcal')::float, 0),
            carbs_per_100g = COALESCE((macros->>'carbs_g')::float, 0),
            protein_per_100g = COALESCE((macros->>'protein_g')::float, 0),
            fat_per_100g = COALESCE((macros->>'fat_g')::float, 0),
            fiber_per_100g = COALESCE((macros->>'fiber_g')::float, 0)
        """
    )

    for col in (
        "kcal_per_100g",
        "carbs_per_100g",
        "protein_per_100g",
        "fat_per_100g",
        "fiber_per_100g",
    ):
        op.alter_column("components", col, nullable=False)

    op.drop_column("components", "macros")
