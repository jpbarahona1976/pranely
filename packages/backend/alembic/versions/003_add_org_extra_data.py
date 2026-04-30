"""Add extra_data JSON column to organizations for feature flags persistence.

Revision ID: 003_add_org_extra_data
Revises: 002_add_waste_movement_unique_constraint
Create Date: 2026-04-29 00:00:00

FIX 8B: Feature Flags persistence issue - flags were stored in-memory only.

PROBLEM:
- Feature flags were stored in memory (process memory)
- On app restart, flags reverted to defaults
- Multi-tenant isolation of flags was not guaranteed

SOLUTION:
- Add extra_data JSON column to organizations table
- Store feature flags in org.extra_data["feature_flags"]
- Feature flags now persist across restarts/reboots

Tables affected:
- organizations: added extra_data JSON column

Multi-tenancy: Column is per-organization, tenant-isolated by design.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_add_org_extra_data"
down_revision: Union[str, None] = "002_add_waste_movement_unique_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add extra_data JSON column to organizations table.
    
    This column enables per-tenant storage of:
    - feature_flags: Feature toggles for the organization
    - other future per-tenant configurations
    
    Default value is NULL (no custom settings).
    Feature flags code falls back to system defaults if NULL.
    
    IMPORTANT: This migration is safe because:
    1. Existing organizations will have NULL (defaults used)
    2. New organizations can have extra_data set
    3. No data loss or schema conflicts
    """
    op.add_column(
        "organizations",
        sa.Column("extra_data", sa.JSON(), nullable=True, server_default=None)
    )
    
    # Add comment for documentation
    op.execute("COMMENT ON COLUMN organizations.extra_data IS 'Per-tenant JSON storage for feature flags and other settings'")


def downgrade() -> None:
    """Remove extra_data column from organizations.
    
    WARNING: This will remove all feature flag configurations.
    Ensure to export data before downgrade if needed.
    """
    op.drop_column("organizations", "extra_data")
