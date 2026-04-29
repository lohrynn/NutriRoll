"""add portions_total + portions_remaining to planned_meals (Phase 12)

Revision ID: 0009_planned_meal_portions
Revises: 0008_profile_default_macro_targets
Create Date: 2026-04-29

Phase 12 — meal-prep mode. Tracks how many portions a planned entry was
batched for (``portions_total``) and how many are still left to eat
(``portions_remaining``). When ``portions_remaining`` reaches 0 the planner
flips the row's status to ``cooked``. Existing rows default to 1/1 (single
meal), which preserves current behaviour.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_planned_meal_portions"
down_revision: str = "0008_profile_default_macro_targets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "planned_meals",
        sa.Column("portions_total", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "planned_meals",
        sa.Column("portions_remaining", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("planned_meals", "portions_remaining")
    op.drop_column("planned_meals", "portions_total")
