"""Alembic migration 006 - Extend WasteMovement with review workflow fields

FASE 2 FIX 1: Add confidence, is_immutable, archived_at, review metadata.
Add index on (organization_id, confidence) for AI triage queries.

Revision ID: 006_waste_review_extension
Revises: 005_performance_indexes
Create Date: 2026-05-01 13:45:00.000000 CST
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_waste_review_extension'
down_revision = '005_performance_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add review workflow fields to waste_movements table."""
    
    # Add confidence_score if not exists (may be from earlier)
    # Using batch for safer column operations
    with op.batch_alter_table("waste_movements") as batch_op:
        # confidence_score - AI confidence 0-1 (already exists, ensure index)
        # Add index for AI triage queries (high confidence = auto-approve candidates)
        batch_op.create_index(
            'ix_waste_movement_org_confidence',
            ['organization_id', 'confidence_score'],
            postgresql_where=sa.text('confidence_score IS NOT NULL'),
            if_not_exists=True
        )
        
        # is_immutable - lock validated movements (already exists, add check constraint)
        batch_op.create_check_constraint(
            'ck_waste_movement_immutable_lock',
            None,
            "(is_immutable = false OR status IN ('validated', 'archived'))",
        )
        
        # archived_at - soft delete timestamp (already exists)
        # Add index for filtering archived records
        batch_op.create_index(
            'ix_waste_movement_org_archived',
            ['organization_id'],
            postgresql_where=sa.text('archived_at IS NOT NULL'),
            if_not_exists=True
        )
        
        # Review metadata fields - NEW
        batch_op.add_column(sa.Column('reviewed_by', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.String(1000), nullable=True))
        
        # created_by_user_id for audit trail
        batch_op.add_column(sa.Column('created_by_user_id', sa.Integer(), nullable=True))
        
        # File metadata
        batch_op.add_column(sa.Column('file_hash', sa.String(64), nullable=True))  # SHA-256 for integrity
        batch_op.add_column(sa.Column('file_size_bytes', sa.Integer(), nullable=True))
    
    # Add FK constraint for created_by_user_id
    op.execute("""
        ALTER TABLE waste_movements 
        ADD CONSTRAINT fk_waste_movement_creator
        FOREIGN KEY (created_by_user_id) 
        REFERENCES users(id) 
        ON DELETE SET NULL
        DEFERRABLE INITIALLY DEFERRED
    """)
    
    # Add comment for documentation
    op.execute("COMMENT ON COLUMN waste_movements.confidence_score IS 'AI model confidence 0.0-1.0'")
    op.execute("COMMENT ON COLUMN waste_movements.is_immutable IS 'Once validated, movement cannot be modified'")
    op.execute("COMMENT ON COLUMN waste_movements.reviewed_by IS 'Email of user who approved/rejected'")
    op.execute("COMMENT ON COLUMN waste_movements.rejection_reason IS 'Reason for rejection or requested changes'")
    op.execute("COMMENT ON COLUMN waste_movements.file_hash IS 'SHA-256 hash for document integrity'")
    
    # Create partial index for high-confidence auto-triage
    # Movements with confidence >= 0.85 are candidates for auto-approve
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_waste_movement_high_confidence
        ON waste_movements (organization_id, created_at DESC)
        WHERE confidence_score >= 0.85 AND archived_at IS NULL
    """)


def downgrade() -> None:
    """Remove review workflow fields from waste_movements table."""
    
    # Remove FK constraint first
    op.execute("ALTER TABLE waste_movements DROP CONSTRAINT IF EXISTS fk_waste_movement_creator")
    
    with op.batch_alter_table("waste_movements") as batch_op:
        batch_op.drop_column('created_by_user_id')
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('reviewed_by')
        batch_op.drop_column('file_size_bytes')
        batch_op.drop_column('file_hash')
        batch_op.drop_index('ix_waste_movement_high_confidence', if_exists=True)
    
    # Remove indexes
    op.execute("DROP INDEX IF EXISTS ix_waste_movement_org_confidence")
    op.execute("DROP INDEX IF EXISTS ix_waste_movement_org_archived")
    op.execute("DROP CONSTRAINT IF EXISTS ck_waste_movement_immutable_lock")