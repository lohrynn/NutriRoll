"""add default_macro_targets JSONB column to user_profile

Revision ID: 0008_profile_default_macro_targets
Revises: 0007_profile_roll_weights
Create Date: 2026-04-29

Phase 11. Adds the user's default per-portion macro targets (e.g. always
``protein_g >= 50``) so the Roll page form starts with the user's preferred
targets instead of blank. JSONB on Postgres; the ORM uses plain ``JSON`` so
the column type also works on SQLite for the test suite (mirrors
``roll_weights`` from migration 0007).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_profile_default_macro_targets"
down_revision: str = "0007_profile_roll_weights"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_profile",
        sa.Column(
            "default_macro_targets",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_profile", "default_macro_targets")
