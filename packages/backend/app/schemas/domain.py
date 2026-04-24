"""Pydantic schemas for domain entities: Employer, Residue, Transporter."""
import re
from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


# =============================================================================
# Constants & Patterns
# =============================================================================

# RFC Mexico pattern: 12 chars (persona moral) o 13 chars (persona fisica)
# Formato persona fisica: 4 letras + 6 digitos (AAMMDD) + 3 alfanumericos (homoclave)
# Formato persona moral: 3 letras + 6 digitos (AAMMDD) + 2 alfanumericos + 1 digito
RFC_PATTERN = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{2,3}$")


# =============================================================================
# Enums
# =============================================================================

class EntityStatusEnum(str, Enum):
    """Generic status for entities."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class WasteTypeEnum(str, Enum):
    """Types of waste according to NOM-052."""
    PELIGROSO = "peligroso"        # Hazardous
    ESPECIAL = "especial"          # Special
    INERTE = "inerte"              # Inert
    ORGANICO = "organico"          # Organic
    RECICLABLE = "reciclable"      # Recyclable


class WasteStatusEnum(str, Enum):
    """Status for waste movements."""
    PENDING = "pending"
    ACTIVE = "active"
    DISPOSED = "disposed"
    ARCHIVED = "archived"


# =============================================================================
# Helper Validators
# =============================================================================

def validate_rfc(value: str) -> str:
    """Validate RFC format for Mexico."""
    value = value.upper().strip()
    if not RFC_PATTERN.match(value):
        raise ValueError(
            "RFC must be 12-13 characters: "
            "3-4 letters + 6 digits + 2-3 alphanumeric"
        )
    return value


# =============================================================================
# Employer Schemas
# =============================================================================

class EmployerBase(BaseModel):
    """Base schema for Employer entity."""
    name: str = Field(..., min_length=1, max_length=255, description="Employer name")
    rfc: str = Field(..., min_length=12, max_length=13, description="Tax ID (RFC Mexico)")
    address: str = Field(..., min_length=1, max_length=500, description="Physical address")
    contact_phone: Optional[str] = Field(None, max_length=30, description="Contact phone")
    # A3 FIX: EmailStr para validación correcta
    email: Optional[EmailStr] = Field(None, description="Contact email")
    website: Optional[str] = Field(None, max_length=255, description="Website URL")
    industry: Optional[str] = Field(None, max_length=100, description="Industry sector")
    status: EntityStatusEnum = Field(
        default=EntityStatusEnum.ACTIVE, 
        description="Entity status"
    )
    # H2: Soft delete timestamp
    archived_at: Optional[datetime] = Field(None, description="Archive timestamp")
    # A5 FIX: extra_data instead of metadata (SQLAlchemy reserved)
    extra_data: Optional[dict] = Field(None, description="Additional data as JSON")

    @field_validator("rfc")
    @classmethod
    def rfc_must_be_valid(cls, v: str) -> str:
        """A4 FIX: Validate RFC Mexico format."""
        return validate_rfc(v)


class EmployerCreate(EmployerBase):
    """Schema for creating a new Employer."""
    pass


class EmployerUpdate(BaseModel):
    """Schema for updating an Employer."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    rfc: Optional[str] = Field(None, min_length=12, max_length=13)
    address: Optional[str] = Field(None, max_length=500)
    contact_phone: Optional[str] = Field(None, max_length=30)
    # A3 FIX: EmailStr
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    status: Optional[EntityStatusEnum] = None
    # A5 FIX: extra_data instead of metadata
    extra_data: Optional[dict] = None

    @field_validator("rfc")
    @classmethod
    def rfc_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        """A4 FIX: Validate RFC Mexico format if provided."""
        if v is not None:
            return validate_rfc(v)
        return v


class EmployerResponse(EmployerBase):
    """Schema for Employer response."""
    id: int
    organization_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EmployerListResponse(BaseModel):
    """Schema for paginated Employer list response."""
    items: List[EmployerResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# Transporter Schemas
# =============================================================================

class TransporterBase(BaseModel):
    """Base schema for Transporter entity."""
    name: str = Field(..., min_length=1, max_length=255, description="Transporter name")
    rfc: str = Field(..., min_length=12, max_length=13, description="Tax ID (RFC Mexico)")
    address: str = Field(..., min_length=1, max_length=500, description="Business address")
    contact_phone: Optional[str] = Field(None, max_length=30, description="Contact phone")
    # A3 FIX: EmailStr
    email: Optional[EmailStr] = Field(None, description="Contact email")
    license_number: Optional[str] = Field(None, max_length=100, description="Transport license number")
    vehicle_plate: Optional[str] = Field(None, max_length=20, description="Primary vehicle plate")
    status: EntityStatusEnum = Field(
        default=EntityStatusEnum.ACTIVE,
        description="Entity status"
    )
    # H2: Soft delete timestamp
    archived_at: Optional[datetime] = Field(None, description="Archive timestamp")
    # A5 FIX: extra_data instead of metadata (SQLAlchemy reserved)
    extra_data: Optional[dict] = Field(None, description="Additional data as JSON")

    @field_validator("rfc")
    @classmethod
    def rfc_must_be_valid(cls, v: str) -> str:
        """A4/H1 FIX: Validate RFC Mexico format (13 chars with Ñ support)."""
        return validate_rfc(v)


class TransporterCreate(TransporterBase):
    """Schema for creating a new Transporter."""
    pass


class TransporterUpdate(BaseModel):
    """Schema for updating a Transporter."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    rfc: Optional[str] = Field(None, min_length=12, max_length=13)
    address: Optional[str] = Field(None, max_length=500)
    contact_phone: Optional[str] = Field(None, max_length=30)
    # A3 FIX: EmailStr
    email: Optional[EmailStr] = None
    license_number: Optional[str] = Field(None, max_length=100)
    vehicle_plate: Optional[str] = Field(None, max_length=20)
    status: Optional[EntityStatusEnum] = None
    # A5 FIX: extra_data instead of metadata
    extra_data: Optional[dict] = None

    @field_validator("rfc")
    @classmethod
    def rfc_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        """A4 FIX: Validate RFC Mexico format if provided."""
        if v is not None:
            return validate_rfc(v)
        return v


class TransporterResponse(TransporterBase):
    """Schema for Transporter response."""
    id: int
    organization_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TransporterListResponse(BaseModel):
    """Schema for paginated Transporter list response."""
    items: List[TransporterResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# Residue Schemas
# =============================================================================

class ResidueBase(BaseModel):
    """Base schema for Residue entity."""
    name: str = Field(..., min_length=1, max_length=255, description="Residue name")
    waste_type: WasteTypeEnum = Field(..., description="Waste classification per NOM-052")
    un_code: Optional[str] = Field(None, max_length=20, description="UN number for dangerous goods")
    hs_code: Optional[str] = Field(None, max_length=20, description="Harmonized System code")
    description: Optional[str] = Field(None, max_length=1000, description="Waste description")
    weight_kg: Optional[float] = Field(None, ge=0, description="Weight in kilograms")
    volume_m3: Optional[float] = Field(None, ge=0, description="Volume in cubic meters")
    status: WasteStatusEnum = Field(
        default=WasteStatusEnum.PENDING,
        description="Residue status"
    )
    # A5 FIX: extra_data instead of metadata (SQLAlchemy reserved)
    extra_data: Optional[dict] = Field(None, description="Additional data as JSON")


class ResidueCreate(ResidueBase):
    """Schema for creating a new Residue."""
    employer_id: int = Field(..., description="Associated employer ID")
    transporter_id: Optional[int] = Field(None, description="Associated transporter ID")


class ResidueUpdate(BaseModel):
    """Schema for updating a Residue."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    waste_type: Optional[WasteTypeEnum] = None
    un_code: Optional[str] = Field(None, max_length=20)
    hs_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=1000)
    weight_kg: Optional[float] = Field(None, ge=0)
    volume_m3: Optional[float] = Field(None, ge=0)
    transporter_id: Optional[int] = None
    status: Optional[WasteStatusEnum] = None
    # A5 FIX: extra_data instead of metadata
    extra_data: Optional[dict] = None


class ResidueResponse(ResidueBase):
    """Schema for Residue response."""
    id: int
    organization_id: int
    employer_id: int
    transporter_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ResidueListResponse(BaseModel):
    """Schema for paginated Residue list response."""
    items: List[ResidueResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# Employer-Transporter Link Schemas
# =============================================================================

class EmployerTransporterLinkBase(BaseModel):
    """Base schema for Employer-Transporter relationship."""
    is_authorized: bool = Field(default=True, description="Authorization status")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")


class EmployerTransporterLinkCreate(EmployerTransporterLinkBase):
    """Schema for creating a link between Employer and Transporter."""
    employer_id: int = Field(..., description="Employer ID")
    transporter_id: int = Field(..., description="Transporter ID")


class EmployerTransporterLinkUpdate(BaseModel):
    """Schema for updating an Employer-Transporter link."""
    is_authorized: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)


class EmployerTransporterLinkResponse(EmployerTransporterLinkBase):
    """Schema for Employer-Transporter link response."""
    id: int
    organization_id: int  # C1 FIX: Incluir org_id
    employer_id: int
    transporter_id: int
    authorization_date: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Combined / Nested Schemas
# =============================================================================

class EmployerWithRelations(EmployerResponse):
    """Employer with its residues and transporter links."""
    residues: List[ResidueResponse] = []
    transporters: List[TransporterResponse] = []


class ResidueWithEmployer(ResidueResponse):
    """Residue with employer details."""
    employer: EmployerResponse


class TransporterWithEmployers(TransporterResponse):
    """Transporter with its linked employers."""
    employers: List[EmployerResponse] = []


# =============================================================================
# Common Schemas
# =============================================================================

class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    # Optional filters
    status: Optional[EntityStatusEnum] = None
    search: Optional[str] = Field(None, max_length=255, description="Search term")


# =============================================================================
# FASE 4A: Waste/Audit/Billing Schemas
# =============================================================================


# Enums adicionales
class MovementStatusEnum(str, Enum):
    """Status for waste movements (NOM-052 compliance)."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    VALIDATED = "validated"
    REJECTED = "rejected"
    EXCEPTION = "exception"


class AlertSeverityEnum(str, Enum):
    """Severity levels for legal alerts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatusEnum(str, Enum):
    """Status for legal alerts."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class SubscriptionStatusEnum(str, Enum):
    """Subscription status for billing."""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class BillingPlanCodeEnum(str, Enum):
    """Billing plan codes."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class AuditLogResultEnum(str, Enum):
    """Result of audited operations."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


# =============================================================================
# AuditLog Schemas
# =============================================================================

class AuditLogBase(BaseModel):
    """Base schema for AuditLog."""
    action: str = Field(..., max_length=50, description="Action performed")
    resource_type: str = Field(..., max_length=50, description="Type of resource")
    resource_id: Optional[str] = Field(None, max_length=100, description="Resource ID")
    result: AuditLogResultEnum = Field(
        default=AuditLogResultEnum.SUCCESS,
        description="Result of the operation"
    )
    payload_json: Optional[dict] = Field(None, description="PII-redacted payload")
    ip_address: Optional[str] = Field(None, max_length=45, description="Client IP")
    user_agent: Optional[str] = Field(None, description="Client user agent")


class AuditLogCreate(AuditLogBase):
    """Schema for creating an AuditLog entry."""
    organization_id: int = Field(..., description="Organization ID")
    user_id: Optional[int] = Field(None, description="User ID who performed action")


class AuditLogResponse(AuditLogBase):
    """Schema for AuditLog response."""
    id: int
    organization_id: int
    user_id: Optional[int] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Schema for paginated AuditLog list."""
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# BillingPlan Schemas
# =============================================================================

class BillingPlanBase(BaseModel):
    """Base schema for BillingPlan."""
    code: BillingPlanCodeEnum = Field(..., description="Plan code")
    name: str = Field(..., max_length=100, description="Plan name")
    description: Optional[str] = Field(None, max_length=500, description="Plan description")
    price_usd_cents: int = Field(default=0, ge=0, description="Price in USD cents")
    doc_limit: int = Field(default=100, ge=0, description="Document limit (0=unlimited)")
    doc_limit_period: str = Field(default="monthly", max_length=20, description="Limit period")
    features_json: Optional[dict] = Field(None, description="Feature flags")
    is_active: bool = Field(default=True, description="Plan is active")


class BillingPlanCreate(BillingPlanBase):
    """Schema for creating a BillingPlan."""
    pass


class BillingPlanUpdate(BaseModel):
    """Schema for updating a BillingPlan."""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price_usd_cents: Optional[int] = Field(None, ge=0)
    doc_limit: Optional[int] = Field(None, ge=0)
    doc_limit_period: Optional[str] = Field(None, max_length=20)
    features_json: Optional[dict] = None
    is_active: Optional[bool] = None


class BillingPlanResponse(BillingPlanBase):
    """Schema for BillingPlan response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# Subscription Schemas
# =============================================================================

class SubscriptionBase(BaseModel):
    """Base schema for Subscription."""
    plan_id: int = Field(..., description="Billing plan ID")
    stripe_sub_id: Optional[str] = Field(None, max_length=255, description="Stripe subscription ID")
    stripe_customer_id: Optional[str] = Field(None, max_length=255, description="Stripe customer ID")
    status: SubscriptionStatusEnum = Field(
        default=SubscriptionStatusEnum.ACTIVE,
        description="Subscription status"
    )
    current_period_start: Optional[datetime] = Field(None, description="Current period start")
    current_period_end: Optional[datetime] = Field(None, description="Current period end")
    metadata_json: Optional[dict] = Field(None, description="Additional metadata")


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a Subscription."""
    organization_id: int = Field(..., description="Organization ID")


class SubscriptionUpdate(BaseModel):
    """Schema for updating a Subscription."""
    stripe_sub_id: Optional[str] = Field(None, max_length=255)
    stripe_customer_id: Optional[str] = Field(None, max_length=255)
    status: Optional[SubscriptionStatusEnum] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    metadata_json: Optional[dict] = None


class SubscriptionResponse(SubscriptionBase):
    """Schema for Subscription response."""
    id: int
    organization_id: int
    started_at: datetime
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# UsageCycle Schemas
# =============================================================================

class UsageCycleBase(BaseModel):
    """Base schema for UsageCycle."""
    month_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Period (YYYY-MM)")
    docs_used: int = Field(default=0, ge=0, description="Documents used")
    docs_limit: int = Field(default=100, ge=0, description="Documents allowed")
    is_locked: bool = Field(default=False, description="Cycle is locked")
    overage_docs: int = Field(default=0, ge=0, description="Documents over limit")
    overage_charged_cents: int = Field(default=0, ge=0, description="Overage charges in cents")


class UsageCycleCreate(UsageCycleBase):
    """Schema for creating a UsageCycle."""
    subscription_id: int = Field(..., description="Subscription ID")


class UsageCycleUpdate(BaseModel):
    """Schema for updating a UsageCycle."""
    docs_used: Optional[int] = Field(None, ge=0)
    docs_limit: Optional[int] = Field(None, ge=0)
    is_locked: Optional[bool] = None
    overage_docs: Optional[int] = Field(None, ge=0)
    overage_charged_cents: Optional[int] = Field(None, ge=0)


class UsageCycleResponse(UsageCycleBase):
    """Schema for UsageCycle response."""
    id: int
    subscription_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UsageCycleListResponse(BaseModel):
    """Schema for paginated UsageCycle list."""
    items: List[UsageCycleResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# LegalAlert Schemas
# =============================================================================

class LegalAlertBase(BaseModel):
    """Base schema for LegalAlert."""
    norma: str = Field(..., max_length=50, description="Norma (e.g., NOM-052, LFPDPPP)")
    title: str = Field(..., max_length=255, description="Alert title")
    description: Optional[str] = Field(None, max_length=2000, description="Alert description")
    severity: AlertSeverityEnum = Field(
        default=AlertSeverityEnum.MEDIUM,
        description="Alert severity"
    )
    status: AlertStatusEnum = Field(
        default=AlertStatusEnum.OPEN,
        description="Alert status"
    )
    related_resource_type: Optional[str] = Field(None, max_length=50, description="Related resource type")
    related_resource_id: Optional[str] = Field(None, max_length=100, description="Related resource ID")
    acknowledged_at: Optional[datetime] = Field(None, description="When alert was acknowledged")
    resolved_at: Optional[datetime] = Field(None, description="When alert was resolved")
    resolution_notes: Optional[str] = Field(None, max_length=1000, description="Resolution notes")
    metadata_json: Optional[dict] = Field(None, description="Additional metadata")


class LegalAlertCreate(LegalAlertBase):
    """Schema for creating a LegalAlert."""
    organization_id: int = Field(..., description="Organization ID")


class LegalAlertUpdate(BaseModel):
    """Schema for updating a LegalAlert."""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    severity: Optional[AlertSeverityEnum] = None
    status: Optional[AlertStatusEnum] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = Field(None, max_length=1000)
    metadata_json: Optional[dict] = None


class LegalAlertResponse(LegalAlertBase):
    """Schema for LegalAlert response."""
    id: int
    organization_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LegalAlertListResponse(BaseModel):
    """Schema for paginated LegalAlert list."""
    items: List[LegalAlertResponse]
    total: int
    page: int
    page_size: int
    pages: int


# =============================================================================
# WasteMovement Schemas
# =============================================================================

class WasteMovementBase(BaseModel):
    """Base schema for WasteMovement."""
    manifest_number: str = Field(..., max_length=100, description="Manifest document number")
    movement_type: Optional[str] = Field(None, max_length=50, description="Type of movement")
    quantity: Optional[float] = Field(None, ge=0, description="Quantity")
    unit: Optional[str] = Field(None, max_length=20, description="Unit of measure")
    date: Optional[datetime] = Field(None, description="Movement date")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="AI confidence score")
    status: MovementStatusEnum = Field(
        default=MovementStatusEnum.PENDING,
        description="Processing status"
    )
    is_immutable: bool = Field(default=False, description="Cannot be modified")
    file_path: Optional[str] = Field(None, max_length=500, description="Document file path")
    orig_filename: Optional[str] = Field(None, max_length=255, description="Original filename")


class WasteMovementCreate(WasteMovementBase):
    """Schema for creating a WasteMovement.
    
    Note: organization_id is NOT required - it comes from the authenticated token.
    """


class WasteMovementUpdate(BaseModel):
    """Schema for updating a WasteMovement."""
    manifest_number: Optional[str] = Field(None, max_length=100)
    movement_type: Optional[str] = Field(None, max_length=50)
    quantity: Optional[float] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=20)
    date: Optional[datetime] = None
    status: Optional[MovementStatusEnum] = None
    is_immutable: Optional[bool] = None
    # H2: archived_at for soft delete
    archived_at: Optional[datetime] = None


class WasteMovementResponse(WasteMovementBase):
    """Schema for WasteMovement response."""
    id: int
    organization_id: int
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WasteMovementListResponse(BaseModel):
    """Schema for paginated WasteMovement list."""
    items: List[WasteMovementResponse]
    total: int
    page: int
    page_size: int
    pages: int