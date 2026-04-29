"""create pantry, stores, supermarket_prices, ratings, history_events

Revision ID: 0002_pantry_stores_history
Revises: 0001_components
Create Date: 2026-05-15

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_pantry_stores_history"
down_revision: str | None = "0001_components"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # pantry_items
    op.create_table(
        "pantry_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "component_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("components.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=8), nullable=False),
        sa.Column(
            "opened", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("expires_at", sa.Date(), nullable=True),
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
    )
    op.create_index(
        "ix_pantry_items_component_id", "pantry_items", ["component_id"]
    )

    # stores
    op.create_table(
        "stores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=400), nullable=True),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default=sa.false()
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
        sa.UniqueConstraint("name", name="uq_stores_name"),
    )

    # supermarket_prices
    op.create_table(
        "supermarket_prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "store_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "component_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("components.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pack_size", sa.Float(), nullable=False),
        sa.Column("pack_price", sa.Float(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "store_id", "component_id", name="uq_price_store_component"
        ),
    )
    op.create_index(
        "ix_supermarket_prices_store_id", "supermarket_prices", ["store_id"]
    )
    op.create_index(
        "ix_supermarket_prices_component_id",
        "supermarket_prices",
        ["component_id"],
    )

    # ratings
    op.create_table(
        "ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bowl_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "component_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("components.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("score BETWEEN 1 AND 5", name="ck_ratings_score_range"),
    )
    op.create_index("ix_ratings_bowl_id", "ratings", ["bowl_id"])
    op.create_index("ix_ratings_component_id", "ratings", ["component_id"])

    # history_events
    op.create_table(
        "history_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("bowl_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_history_events_kind", "history_events", ["kind"])
    op.create_index("ix_history_events_bowl_id", "history_events", ["bowl_id"])
    op.create_index(
        "ix_history_events_created_at", "history_events", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_history_events_created_at", table_name="history_events")
    op.drop_index("ix_history_events_bowl_id", table_name="history_events")
    op.drop_index("ix_history_events_kind", table_name="history_events")
    op.drop_table("history_events")

    op.drop_index("ix_ratings_component_id", table_name="ratings")
    op.drop_index("ix_ratings_bowl_id", table_name="ratings")
    op.drop_table("ratings")

    op.drop_index(
        "ix_supermarket_prices_component_id", table_name="supermarket_prices"
    )
    op.drop_index(
        "ix_supermarket_prices_store_id", table_name="supermarket_prices"
    )
    op.drop_table("supermarket_prices")

    op.drop_table("stores")

    op.drop_index("ix_pantry_items_component_id", table_name="pantry_items")
    op.drop_table("pantry_items")
