"""
Add unique constraint to waste_movements table.

Revision ID: 002_add_waste_movement_unique_constraint
Revises: 001_initial_baseline
Create Date: 2026-04-27

This migration adds a unique constraint on waste_movements to prevent
duplicate manifest entries per organization and date.

Constraint: (organization_id, manifest_number, date)
- Same manifest number is allowed for different dates
- Same manifest number on same date is only allowed per organization
- Allows cross-organization duplicates (different tenants can have same manifest)

Note: If the table has existing duplicates, this migration will fail.
Run the verification query first to identify duplicates before applying.

Verification query (run manually if needed):
    SELECT organization_id, manifest_number, date, COUNT(*) as cnt
    FROM waste_movements
    WHERE date IS NOT NULL
    GROUP BY organization_id, manifest_number, date
    HAVING COUNT(*) > 1;
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_add_waste_movement_unique_constraint"
down_revision: Union[str, None] = "001_initial_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add unique constraint on waste_movements.
    
    The constraint prevents duplicate manifest entries per organization and date.
    NULL date values are excluded from the unique constraint (SQL standard behavior).
    
    Creates:
    - UniqueConstraint: uq_waste_movement_org_manifest_date
    - Index: ix_waste_movement_org_status (for efficient queries)
    """
    # Add unique constraint for (organization_id, manifest_number, date)
    # Note: date is nullable, NULL values don't participate in unique constraint
    op.create_unique_constraint(
        "uq_waste_movement_org_manifest_date",
        "waste_movements",
        ["organization_id", "manifest_number", "date"],
        schema=None,
    )
    
    # Add index for status queries (composite index for common queries)
    op.create_index(
        "ix_waste_movement_org_status",
        "waste_movements",
        ["organization_id", "status"],
        unique=False,
        schema=None,
    )


def downgrade() -> None:
    """
    Remove unique constraint and index from waste_movements.
    
    WARNING: This removes data integrity protection. Only downgrade if absolutely necessary.
    """
    # Drop the unique constraint
    op.drop_constraint(
        "uq_waste_movement_org_manifest_date",
        "waste_movements",
        type_="unique",
        schema=None,
    )
    
    # Drop the status index (if it wasn't there before)
    op.drop_index(
        "ix_waste_movement_org_status",
        table_name="waste_movements",
        schema=None,
    )
