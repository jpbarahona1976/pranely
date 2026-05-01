"""Phase 9C: Add performance indexes for waste_movements.

Revision ID: 005_performance_indexes
Revises: 004_add_webhook_events
Create Date: 2026-04-30

FASE 9C PERFORMANCE: Add missing indexes to optimize query performance.
- Composite index for waste_movements queries (org_id, status, archived_at)
- Index for manifest_number lookups
- Index for membership queries (user_id, organization_id)

Target: p95 < 500ms SLO
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "005_performance_indexes"
down_revision: Union[str, None] = "004_add_webhook_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add performance indexes for waste_movements and memberships.
    
    Optimization targets:
    1. Waste movements: (organization_id, status, archived_at) for stats queries
    2. Waste movements: (organization_id, created_at DESC) for listing
    3. Memberships: (user_id, organization_id) for membership validation
    """
    
    # ========================================================================
    # 9C.1: Composite index for waste_movements stats queries
    # ========================================================================
    # Supports: GET /api/v1/waste/stats
    # Current: 7 separate COUNT queries
    # Target: Single query with GROUP BY
    op.create_index(
        "ix_waste_movement_org_status_archived",
        "waste_movements",
        ["organization_id", "status", "archived_at"],
        unique=False
    )
    
    # ========================================================================
    # 9C.2: Index for waste movements listing (ordered by created_at)
    # ========================================================================
    # Supports: GET /api/v1/waste with pagination
    op.create_index(
        "ix_waste_movement_org_created_at",
        "waste_movements",
        ["organization_id", "created_at"],
        unique=False
    )
    
    # ========================================================================
    # 9C.3: Index for membership validation queries
    # ========================================================================
    # Supports: validate_membership_and_role() in waste endpoints
    # Called on every write operation - was N+1 pattern
    op.create_index(
        "ix_membership_user_org",
        "memberships",
        ["user_id", "organization_id"],
        unique=False
    )
    
    # ========================================================================
    # 9C.4: Index for audit_logs organization queries
    # ========================================================================
    # Supports: Audit trail queries by organization
    op.create_index(
        "ix_audit_log_org",
        "audit_logs",
        ["organization_id"],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index("ix_waste_movement_org_status_archived", "waste_movements")
    op.drop_index("ix_waste_movement_org_created_at", "waste_movements")
    op.drop_index("ix_membership_user_org", "memberships")
    op.drop_index("ix_audit_log_org", "audit_logs")