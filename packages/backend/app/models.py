"""SQLAlchemy models for PRANELY core entities."""
from datetime import datetime, timezone
from typing import List, Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, Text
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow():
    """Return timezone-aware UTC datetime (Python 3.12+ compliant)."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class UserRole(PyEnum):
    """User roles within an organization."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class EntityStatus(PyEnum):
    """Generic status for entities."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class WasteType(PyEnum):
    """Types of waste according to NOM-052."""
    PELIGROSO = "peligroso"        # Hazardous
    ESPECIAL = "especial"          # Special
    INERTE = "inerte"              # Inert
    ORGANICO = "organico"          # Organic
    RECICLABLE = "reciclable"      # Recyclable


class WasteStatus(PyEnum):
    """Status for waste movements."""
    PENDING = "pending"
    ACTIVE = "active"
    DISPOSED = "disposed"
    ARCHIVED = "archived"


# Enums adicionales para nuevas entidades (moved up to be available for WasteMovement)
class MovementStatus(PyEnum):
    """Status for waste movements (NOM-052 compliance)."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    VALIDATED = "validated"
    REJECTED = "rejected"
    EXCEPTION = "exception"


class AlertSeverity(PyEnum):
    """Severity levels for legal alerts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(PyEnum):
    """Status for legal alerts."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class SubscriptionStatus(PyEnum):
    """Subscription status for billing."""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class BillingPlanCode(PyEnum):
    """Billing plan codes."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class AuditLogResult(PyEnum):
    """Result of audited operations."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class Organization(Base):
    """
    Organization entity (Tenant).
    
    All system data is partitioned by organization_id.
    """
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    segment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # generator, gestor
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )

    # Relationships
    memberships: Mapped[List["Membership"]] = relationship(
        "Membership", back_populates="organization", cascade="all, delete-orphan"
    )
    employers: Mapped[List["Employer"]] = relationship(
        "Employer", back_populates="organization", cascade="all, delete-orphan"
    )
    transporters: Mapped[List["Transporter"]] = relationship(
        "Transporter", back_populates="organization", cascade="all, delete-orphan"
    )
    residues: Mapped[List["Residue"]] = relationship(
        "Residue", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}')>"


class User(Base):
    """
    User entity for authentication.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    locale: Mapped[str] = mapped_column(String(10), default="es")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )

    # Relationships
    memberships: Mapped[List["Membership"]] = relationship(
        "Membership", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"


class Membership(Base):
    """
    Link between User and Organization with a specific role.
    """
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    role: Mapped["UserRole"] = mapped_column(
        Enum(UserRole), default=UserRole.MEMBER, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memberships")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<Membership(user={self.user_id}, org={self.organization_id}, role={self.role.value})>"


# =============================================================================
# FASE 1B: Modelos de dominio - Employer, Residue, Transporter
# =============================================================================
# FASE 1B: Modelos de dominio - Employer, Residue, Transporter
# =============================================================================


class Employer(Base):
    """
    Employer/Company entity that generates waste.
    
    An Employer belongs to an Organization (tenant) and can have
    multiple Residues and relationships with Transporters.
    
    Attributes:
        rfc: Tax identification number (Mexico)
        industry: Industry sector
    
    Multi-tenancy: organization_id filter REQUIRED on all queries.
    """
    __tablename__ = "employers"
    __table_args__ = (
        # A1: RFC único por tenant (organization_id + rfc)
        UniqueConstraint("organization_id", "rfc", name="uq_employer_org_rfc"),
        # A2: Índice para queries por org + status
        Index("ix_employer_org_status", "organization_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rfc: Mapped[str] = mapped_column(String(13), nullable=False)  # Tax ID (Mexico) - 12 o 13 chars
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Metadata
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Status & timestamps
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus), default=EntityStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )
    # H2: Soft delete via archived_at (indexed for filtering archived entities)
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    # extra_data: JSON field for additional metadata (SQLAlchemy reserved: metadata)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="employers"
    )
    residues: Mapped[List["Residue"]] = relationship(
        "Residue", back_populates="employer", cascade="all, delete-orphan"
    )
    # Many-to-many with Transporter via employer_transporter_links
    transporter_links: Mapped[List["EmployerTransporterLink"]] = relationship(
        "EmployerTransporterLink", back_populates="employer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Employer(id={self.id}, name='{self.name}', rfc='{self.rfc}')>"


class Transporter(Base):
    """
    Transporter entity that moves waste from employers to disposal sites.
    
    Attributes:
        license_number: Transport license/permit number
        vehicle_plate: Primary vehicle plate
    
    Multi-tenancy: organization_id filter REQUIRED on all queries.
    """
    __tablename__ = "transporters"
    __table_args__ = (
        # A1: RFC único por tenant
        UniqueConstraint("organization_id", "rfc", name="uq_transporter_org_rfc"),
        # A2: Índice para queries por org + status
        Index("ix_transporter_org_status", "organization_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rfc: Mapped[str] = mapped_column(String(13), nullable=False)  # Tax ID (México)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # License info
    license_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    vehicle_plate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Status & timestamps
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus), default=EntityStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    # C3 FIX: updated_at era String, ahora es DateTime(timezone=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )
    # H2: Soft delete via archived_at (indexed for filtering archived entities)
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    # extra_data: JSON field for additional metadata (SQLAlchemy reserved: metadata)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="transporters"
    )
    residues: Mapped[List["Residue"]] = relationship(
        "Residue", back_populates="transporter"
    )
    # Many-to-many with Employer
    employer_links: Mapped[List["EmployerTransporterLink"]] = relationship(
        "EmployerTransporterLink", back_populates="transporter", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Transporter(id={self.id}, name='{self.name}', license='{self.license_number}')>"


class Residue(Base):
    """
    Residue/Waste entity tracked for compliance.
    
    A Residue belongs to an Employer and can be transported by a Transporter.
    Tracks waste type, quantity, and status for NOM-052/055 compliance.
    
    Attributes:
        waste_type: Classification per NOM-052 (peligroso, especial, inerte, organico, reciclable)
        un_code: UN number for dangerous goods
        hs_code: Harmonized System code
    
    Multi-tenancy: organization_id filter REQUIRED on all queries.
    """
    __tablename__ = "residues"
    __table_args__ = (
        # A2: Índice para queries por org + employer_id
        Index("ix_residue_org_employer", "organization_id", "employer_id"),
        # A2: Índice para queries por org + status
        Index("ix_residue_org_status", "organization_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    # Foreign keys
    employer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employers.id"), nullable=False
    )
    transporter_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("transporters.id"), nullable=True
    )
    # Waste details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    waste_type: Mapped[WasteType] = mapped_column(Enum(WasteType), nullable=False)
    un_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # UN number
    hs_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # HS code
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    # Quantity
    weight_kg: Mapped[Optional[float]] = mapped_column(nullable=True)
    volume_m3: Mapped[Optional[float]] = mapped_column(nullable=True)
    # Status & timestamps
    status: Mapped[WasteStatus] = mapped_column(
        Enum(WasteStatus), default=WasteStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )
    # extra_data: JSON field for additional metadata (SQLAlchemy reserved: metadata)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    # C4 FIX: back_populates="organization" añadida
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="residues"
    )
    employer: Mapped["Employer"] = relationship("Employer", back_populates="residues")
    transporter: Mapped[Optional["Transporter"]] = relationship(
        "Transporter", back_populates="residues"
    )

    def __repr__(self) -> str:
        return f"<Residue(id={self.id}, name='{self.name}', type={self.waste_type.value})>"


class EmployerTransporterLink(Base):
    """
    Many-to-many association between Employer and Transporter.
    
    Records the relationship and authorization status between
    an employer and their authorized transporters.
    
    Multi-tenancy: organization_id REQUIRED for proper tenant isolation.
    """
    __tablename__ = "employer_transporter_links"
    __table_args__ = (
        # C1 FIX: Añadido organization_id para multi-tenancy
        UniqueConstraint("organization_id", "employer_id", "transporter_id", name="uq_link_org_employer_transporter"),
        # A2: Índice para queries por org
        Index("ix_link_org", "organization_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # C1 FIX: organization_id FK añadida
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    employer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employers.id"), nullable=False
    )
    transporter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transporters.id"), nullable=False
    )
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=True)
    authorization_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    employer: Mapped["Employer"] = relationship(
        "Employer", back_populates="transporter_links"
    )
    transporter: Mapped["Transporter"] = relationship(
        "Transporter", back_populates="employer_links"
    )

    def __repr__(self) -> str:
        return f"<EmployerTransporterLink(org={self.organization_id}, employer={self.employer_id}, transporter={self.transporter_id})>"


# =============================================================================
# Legacy back_populates (moved to Organization class above)
# =============================================================================
# Note: Organization relationships are now defined directly in the Organization class
# for better clarity and to avoid class attribute reassignment issues.


# =============================================================================
# FASE 4A: Modelo de Datos - Waste/Audit/Billing
# =============================================================================


# =============================================================================
# AuditLog Model
# =============================================================================


class AuditLog(Base):
    """
    Audit log for regulatory compliance (NOM-151).
    
    Stores audit events with PII redaction support and 5-year retention.
    This is a simplified version for quick queries; detailed audit is in AuditTrail.
    
    Multi-tenancy: organization_id REQUIRED for all queries.
    LFPDPPP: PII should be redacted in payload_json.
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_log_org_timestamp", "organization_id", "timestamp"),
        Index("ix_audit_log_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
        UniqueConstraint("id", name="uq_audit_log_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    result: Mapped[AuditLogResult] = mapped_column(
        Enum(AuditLogResult), default=AuditLogResult.SUCCESS
    )
    # PII-redacted payload (use PIIRedactor before storing)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Retention: 5 years for NOM-151 compliance
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action='{self.action}', org={self.organization_id})>"


# =============================================================================
# BillingPlan Model
# =============================================================================


class BillingPlan(Base):
    """
    Billing plan definition.
    
    Defines available subscription plans with pricing and limits.
    Plans are global (not tenant-specific).
    """
    __tablename__ = "billing_plans"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[BillingPlanCode] = mapped_column(
        Enum(BillingPlanCode), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Pricing (USD cents for precision)
    price_usd_cents: Mapped[int] = mapped_column(Integer, default=0)
    # Document limits
    doc_limit: Mapped[int] = mapped_column(Integer, default=100)  # 0 = unlimited
    doc_limit_period: Mapped[str] = mapped_column(String(20), default="monthly")
    # Feature flags
    features_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )
    
    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="plan"
    )
    
    def __repr__(self) -> str:
        return f"<BillingPlan(code='{self.code.value}', name='{self.name}')>"


# =============================================================================
# Subscription Model
# =============================================================================


class Subscription(Base):
    """
    Organization subscription to a billing plan.
    
    Links an organization to a billing plan with Stripe integration.
    
    Multi-tenancy: organization_id REQUIRED.
    """
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_subscription_org"),
        Index("ix_subscription_status", "status"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False, unique=True
    )
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("billing_plans.id"), nullable=False
    )
    # Stripe integration
    stripe_sub_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Subscription status
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE
    )
    # Billing dates
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="subscription"
    )
    plan: Mapped["BillingPlan"] = relationship(
        "BillingPlan", back_populates="subscriptions"
    )
    usage_cycles: Mapped[List["UsageCycle"]] = relationship(
        "UsageCycle", back_populates="subscription", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Subscription(org={self.organization_id}, plan={self.plan_id}, status={self.status.value})>"


# =============================================================================
# UsageCycle Model
# =============================================================================


class UsageCycle(Base):
    """
    Monthly usage tracking for subscription billing.
    
    Tracks document usage per billing cycle to enforce plan limits.
    
    Multi-tenancy: organization_id via subscription relationship.
    """
    __tablename__ = "usage_cycles"
    __table_args__ = (
        UniqueConstraint("subscription_id", "month_year", name="uq_usage_cycle_sub_month"),
        Index("ix_usage_cycle_month", "month_year"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscriptions.id"), nullable=False
    )
    # Period (YYYY-MM format)
    month_year: Mapped[str] = mapped_column(String(7), nullable=False)
    # Usage tracking
    docs_used: Mapped[int] = mapped_column(Integer, default=0)
    docs_limit: Mapped[int] = mapped_column(Integer, default=100)
    # Lock state (once period ends, no more changes)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Billing info
    overage_docs: Mapped[int] = mapped_column(Integer, default=0)  # Docs over limit
    overage_charged_cents: Mapped[int] = mapped_column(Integer, default=0)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )
    
    # Relationships
    subscription: Mapped["Subscription"] = relationship(
        "Subscription", back_populates="usage_cycles"
    )
    
    def __repr__(self) -> str:
        return f"<UsageCycle(sub={self.subscription_id}, period={self.month_year}, used={self.docs_used})>"


# =============================================================================
# LegalAlert Model
# =============================================================================


class LegalAlert(Base):
    """
    Legal and regulatory alerts for compliance.
    
    Tracks NOM-052/SEMARNAT and other regulatory requirements.
    
    Multi-tenancy: organization_id REQUIRED.
    """
    __tablename__ = "legal_alerts"
    __table_args__ = (
        Index("ix_legal_alert_org_status", "organization_id", "status"),
        Index("ix_legal_alert_severity", "severity"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    # Alert identification
    norma: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., NOM-052, LFPDPPP
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    # Severity and status
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity), default=AlertSeverity.MEDIUM
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus), default=AlertStatus.OPEN
    )
    # Related entities (for context)
    related_resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    related_resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Resolution tracking
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    
    def __repr__(self) -> str:
        return f"<LegalAlert(id={self.id}, norma='{self.norma}', severity={self.severity.value})>"


class WasteMovement(Base):
    """
    Waste movement/manifest entity for NOM-052 compliance.
    
    Tracks the physical movement of waste from generator to disposal.
    
    Multi-tenancy: organization_id REQUIRED.
    """
    __tablename__ = "waste_movements"
    __table_args__ = (
        # FIX 5B-FIX-1: Unique constraint to prevent duplicate manifests per org/date
        UniqueConstraint(
            "organization_id", "manifest_number", "date",
            name="uq_waste_movement_org_manifest_date"
        ),
        Index("ix_waste_movement_org_timestamp", "organization_id", "created_at"),
        Index("ix_waste_movement_manifest", "manifest_number"),
        Index("ix_waste_movement_org_status", "organization_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    # Manifest details
    manifest_number: Mapped[str] = mapped_column(String(100), nullable=False)
    movement_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Measurement
    quantity: Mapped[Optional[float]] = mapped_column(nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Date of movement
    date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # AI Metadata
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    # Status
    status: Mapped[MovementStatus] = mapped_column(
        Enum(MovementStatus), default=MovementStatus.PENDING, nullable=False
    )
    # Controls
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # File storage
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    orig_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="movements")

    def __repr__(self) -> str:
        return f"<WasteMovement(id={self.id}, manifest='{self.manifest_number}', status={self.status.value})>"


# =============================================================================
# WebhookEvent Model (Idempotency for Stripe webhooks)
# =============================================================================


class WebhookEvent(Base):
    """
    Webhook event store for idempotency.
    
    Stores processed Stripe webhook events to prevent duplicate processing.
    Uses event_id as unique identifier per event type.
    
    Multi-tenancy: organization_id optional (some events may not have org context).
    """
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("event_id", "event_type", name="uq_webhook_event_id_type"),
        Index("ix_webhook_event_stripe_customer", "stripe_customer_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    # Payload snapshot (for debugging/audit)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Processing status
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    # Result tracking
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    def __repr__(self) -> str:
        return f"<WebhookEvent(id={self.id}, event_id='{self.event_id}', type='{self.event_type}')>"


# =============================================================================
# Add new relationships to Organization
# =============================================================================

# Add subscription relationship to Organization
Organization.subscription = relationship(
    "Subscription", back_populates="organization", uselist=False
)

# Add audit_logs relationship to Organization
Organization.audit_logs = relationship(
    "AuditLog", back_populates="organization", cascade="all, delete-orphan"
)

# Add legal_alerts relationship to Organization
Organization.legal_alerts = relationship(
    "LegalAlert", back_populates="organization", cascade="all, delete-orphan"
)

# Add movements relationship to Organization
Organization.movements = relationship(
    "WasteMovement", back_populates="organization", cascade="all, delete-orphan"
)