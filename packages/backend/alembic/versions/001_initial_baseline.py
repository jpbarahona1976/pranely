"""Initial baseline: PRANELY core entities.

Revision ID: 001_initial_baseline
Revises: 
Create Date: 2026-04-24 18:00:00

PRANELY - Sistema Documental Maestro
Migration: 001_initial_baseline

Tables created:
- organizations (multi-tenant root)
- users (authentication)
- memberships (org-user relationship)
- employers (waste generators)
- transporters (waste carriers)
- residues (tracked waste)
- employer_transporter_links (N:M relationship)
- audit_logs (NOM-151 compliance)
- billing_plans (subscription plans)
- subscriptions (org-billing link)
- usage_cycles (monthly usage tracking)
- legal_alerts (regulatory compliance)
- waste_movements (NOM-052 manifests)

Multi-tenancy: All entities with organization_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all PRANELY tables."""
    
    # ========================================================================
    # ORGANIZATIONS (multi-tenant root entity)
    # ========================================================================
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("segment", sa.String(100), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id")
    )
    
    # ========================================================================
    # USERS (authentication entity)
    # ========================================================================
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("locale", sa.String(10), nullable=False, default="es"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email")
    )
    op.create_index("ix_users_email", "users", ["email"])
    
    # ========================================================================
    # MEMBERSHIPS (user-organization relationship with role)
    # ========================================================================
    op.create_table(
        "memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org")
    )
    
    # ========================================================================
    # EMPLOYERS (waste generator companies)
    # ========================================================================
    op.create_table(
        "employers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rfc", sa.String(13), nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "rfc", name="uq_employer_org_rfc")
    )
    op.create_index("ix_employer_org_status", "employers", ["organization_id", "status"])
    op.create_index("ix_employers_archived_at", "employers", ["archived_at"])
    
    # ========================================================================
    # TRANSPORTERS (waste carrier companies)
    # ========================================================================
    op.create_table(
        "transporters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rfc", sa.String(13), nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("license_number", sa.String(100), nullable=True),
        sa.Column("vehicle_plate", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "rfc", name="uq_transporter_org_rfc")
    )
    op.create_index("ix_transporter_org_status", "transporters", ["organization_id", "status"])
    op.create_index("ix_transporters_archived_at", "transporters", ["archived_at"])
    
    # ========================================================================
    # RESIDUES (tracked waste entities)
    # ========================================================================
    op.create_table(
        "residues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("employer_id", sa.Integer(), nullable=False),
        sa.Column("transporter_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("waste_type", sa.String(20), nullable=False),
        sa.Column("un_code", sa.String(20), nullable=True),
        sa.Column("hs_code", sa.String(20), nullable=True),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("volume_m3", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employer_id"], ["employers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transporter_id"], ["transporters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_residue_org_employer", "residues", ["organization_id", "employer_id"])
    op.create_index("ix_residue_org_status", "residues", ["organization_id", "status"])
    
    # ========================================================================
    # EMPLOYER_TRANSPORTER_LINKS (N:M relationship)
    # ========================================================================
    op.create_table(
        "employer_transporter_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("employer_id", sa.Integer(), nullable=False),
        sa.Column("transporter_id", sa.Integer(), nullable=False),
        sa.Column("is_authorized", sa.Boolean(), nullable=True, default=True),
        sa.Column("authorization_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employer_id"], ["employers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transporter_id"], ["transporters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "employer_id", "transporter_id", name="uq_link_org_employer_transporter")
    )
    op.create_index("ix_link_org", "employer_transporter_links", ["organization_id"])
    
    # ========================================================================
    # AUDIT_LOGS (NOM-151 compliance)
    # ========================================================================
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("result", sa.String(20), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", name="uq_audit_log_id")
    )
    op.create_index("ix_audit_log_org_timestamp", "audit_logs", ["organization_id", "timestamp"])
    op.create_index("ix_audit_log_user_timestamp", "audit_logs", ["user_id", "timestamp"])
    op.create_index("ix_audit_log_resource", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    
    # ========================================================================
    # BILLING_PLANS (subscription plans - global, not tenant-specific)
    # ========================================================================
    op.create_table(
        "billing_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("price_usd_cents", sa.Integer(), nullable=True, default=0),
        sa.Column("doc_limit", sa.Integer(), nullable=True, default=100),
        sa.Column("doc_limit_period", sa.String(20), nullable=True, default="monthly"),
        sa.Column("features_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code")
    )
    
    # ========================================================================
    # SUBSCRIPTIONS (organization-billing plan link)
    # ========================================================================
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("stripe_sub_id", sa.String(255), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["billing_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_subscription_org")
    )
    op.create_index("ix_subscription_status", "subscriptions", ["status"])
    
    # ========================================================================
    # USAGE_CYCLES (monthly usage tracking per subscription)
    # ========================================================================
    op.create_table(
        "usage_cycles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("month_year", sa.String(7), nullable=False),
        sa.Column("docs_used", sa.Integer(), nullable=True, default=0),
        sa.Column("docs_limit", sa.Integer(), nullable=True, default=100),
        sa.Column("is_locked", sa.Boolean(), nullable=False, default=False),
        sa.Column("overage_docs", sa.Integer(), nullable=True, default=0),
        sa.Column("overage_charged_cents", sa.Integer(), nullable=True, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subscription_id", "month_year", name="uq_usage_cycle_sub_month")
    )
    op.create_index("ix_usage_cycle_month", "usage_cycles", ["month_year"])
    
    # ========================================================================
    # LEGAL_ALERTS (regulatory compliance alerts)
    # ========================================================================
    op.create_table(
        "legal_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("norma", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("related_resource_type", sa.String(50), nullable=True),
        sa.Column("related_resource_id", sa.String(100), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.String(1000), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_legal_alert_org_status", "legal_alerts", ["organization_id", "status"])
    op.create_index("ix_legal_alert_severity", "legal_alerts", ["severity"])
    
    # ========================================================================
    # WASTE_MOVEMENTS (NOM-052 compliance manifests)
    # ========================================================================
    op.create_table(
        "waste_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("manifest_number", sa.String(100), nullable=False),
        sa.Column("movement_type", sa.String(50), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_immutable", sa.Boolean(), nullable=False, default=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("orig_filename", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_waste_movement_org_timestamp", "waste_movements", ["organization_id", "created_at"])
    op.create_index("ix_waste_movement_manifest", "waste_movements", ["manifest_number"])


def downgrade() -> None:
    """Drop all PRANELY tables (in reverse order of creation)."""
    # Drop tables in reverse dependency order
    op.drop_table("waste_movements")
    op.drop_table("legal_alerts")
    op.drop_table("usage_cycles")
    op.drop_table("subscriptions")
    op.drop_table("billing_plans")
    op.drop_table("audit_logs")
    op.drop_table("employer_transporter_links")
    op.drop_table("residues")
    op.drop_table("transporters")
    op.drop_table("employers")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("organizations")