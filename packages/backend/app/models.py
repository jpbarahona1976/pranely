"""SQLAlchemy models for PRANELY core entities."""
from datetime import datetime, timezone
from typing import List, Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
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


class Organization(Base):
    """Organization/Tenant entity for multi-tenancy."""
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
    waste_movements: Mapped[List["WasteMovement"]] = relationship(
        "WasteMovement", back_populates="organization"
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
    """User entity for authentication."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    locale: Mapped[str] = mapped_column(String(10), default="es")  # es/en
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
    """Membership linking users to organizations with roles."""
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memberships")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<Membership(user_id={self.user_id}, org_id={self.organization_id}, role={self.role})>"


class WasteMovement(Base):
    """Waste movement entity for tracking."""
    __tablename__ = "waste_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    manifest_number: Mapped[str] = mapped_column(String(100), nullable=False)
    movement_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, inreview, validated, exception, rejected
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    orig_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=_utcnow
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="waste_movements")

    def __repr__(self) -> str:
        return f"<WasteMovement(id={self.id}, manifest='{self.manifest_number}')>"


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