"""Add webhook_events table for Stripe webhook idempotency.

Revision ID: 004_add_webhook_events
Revises: 003_add_org_extra_data
Create Date: 2026-04-29 18:00:00

Purpose:
- Store processed Stripe webhook events for idempotency
- Prevent duplicate processing of same event
- Audit trail for billing operations

Tables modified:
- webhook_events: New table for webhook event storage

Multi-tenancy consideration:
- webhook_events.stripe_customer_id links to organizations.stripe_customer_id
- Some events may not have org context (e.g., platform-level events)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_add_webhook_events"
down_revision: Union[str, None] = "003_add_org_extra_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create webhook_events table for Stripe webhook idempotency."""
    
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("success", sa.Boolean(), nullable=False, default=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "event_type", name="uq_webhook_event_id_type"),
    )
    
    # Index for customer lookups
    op.create_index("ix_webhook_event_stripe_customer", "webhook_events", ["stripe_customer_id"])
    op.create_index("ix_webhook_event_event_id", "webhook_events", ["event_id"])


def downgrade() -> None:
    """Drop webhook_events table."""
    op.drop_index("ix_webhook_event_event_id", "webhook_events")
    op.drop_index("ix_webhook_event_stripe_customer", "webhook_events")
    op.drop_table("webhook_events")