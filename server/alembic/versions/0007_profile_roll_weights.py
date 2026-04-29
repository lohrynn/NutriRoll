"""add roll_weights JSONB column to user_profile

Revision ID: 0007_profile_roll_weights
Revises: 0006_components_macros_jsonb
Create Date: 2026-05-05

Adds a nullable ``roll_weights`` JSONB column to ``user_profile`` so that
per-user algorithm weight overrides can be persisted server-side rather than
being stored only in the browser's localStorage. NULL = use server defaults.
See ``docs/modularity-audit.md`` M6 / M10 for context.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_profile_roll_weights"
down_revision: str = "0006_components_macros_jsonb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_profile",
        sa.Column("roll_weights", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_profile", "roll_weights")
