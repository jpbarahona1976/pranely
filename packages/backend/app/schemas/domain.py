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