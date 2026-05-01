"""Alembic migration 007 - Add extra_data JSONB to Membership

FASE 2.1 FIX 4: Add extra_data JSONB column to memberships table
for storing operator metadata (role info, department, etc.)

Revision ID: 007_membership_extra_data
Revises: 006_waste_review_extension
Create Date: 2026-05-01 15:00:00 CST
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '007_membership_extra_data'
down_revision = '006_waste_review_extension'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add extra_data JSONB column to memberships table."""
    
    # Add extra_data column as JSONB (PostgreSQL native JSON support)
    op.add_column(
        'memberships',
        sa.Column('extra_data', postgresql.JSONB, nullable=True)
    )
    
    # Add index for querying extra_data (GIN index for JSONB)
    op.execute("""
        CREATE INDEX ix_memberships_extra_data 
        ON memberships 
        USING GIN (extra_data)
    """)
    
    # Add comment for documentation
    op.execute("COMMENT ON COLUMN memberships.extra_data IS 'JSONB field for operator metadata (role info, department, shift, etc.)'")


def downgrade() -> None:
    """Remove extra_data column from memberships table."""
    
    # Drop index first
    op.execute("DROP INDEX IF EXISTS ix_memberships_extra_data")
    
    # Drop column
    op.drop_column('memberships', 'extra_data')