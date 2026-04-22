"""Employer API schemas - formal contract."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

from app.schemas.api.common import ListResponse


class EmployerIn(BaseModel):
    """Employer create/update input schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Employer name")
    rfc: str = Field(..., min_length=12, max_length=13, description="Tax ID (RFC Mexico)")
    address: str = Field(..., min_length=1, max_length=500, description="Physical address")
    contact_phone: Optional[str] = Field(default=None, max_length=30, description="Contact phone")
    email: Optional[EmailStr] = Field(default=None, description="Contact email")
    website: Optional[str] = Field(default=None, max_length=255, description="Website URL")
    industry: Optional[str] = Field(default=None, max_length=100, description="Industry sector")
    status: str = Field(default="active", description="Entity status (active/inactive/pending)")
    archived_at: Optional[datetime] = Field(default=None, description="Archive timestamp (soft-delete)")
    extra_data: Optional[dict] = Field(default=None, description="Additional metadata as JSON")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Empresa S.A. de C.V.",
                "rfc": "ESA123456789",
                "address": "Av. Industrial 123, Monterrey, NL",
                "contact_phone": "+52 81 1234 5678",
                "email": "contacto@empresa.com",
                "website": "https://empresa.com",
                "industry": "manufactura",
                "status": "active"
            }
        }
    }


class EmployerUpdateIn(BaseModel):
    """Employer partial update schema."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    rfc: Optional[str] = Field(default=None, min_length=12, max_length=13)
    address: Optional[str] = Field(default=None, max_length=500)
    contact_phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = Field(default=None)
    website: Optional[str] = Field(default=None, max_length=255)
    industry: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None)
    extra_data: Optional[dict] = Field(default=None)

    model_config = {"json_schema_extra": {"example": {"name": "Nuevo Nombre"}}}


class EmployerOut(BaseModel):
    """Employer response schema."""
    id: int = Field(description="Employer ID")
    organization_id: int = Field(description="Organization ID (multi-tenant)")
    name: str = Field(description="Employer name")
    rfc: str = Field(description="Tax ID (RFC)")
    address: str = Field(description="Physical address")
    contact_phone: Optional[str] = Field(default=None, description="Contact phone")
    email: Optional[str] = Field(default=None, description="Contact email")
    website: Optional[str] = Field(default=None, description="Website URL")
    industry: Optional[str] = Field(default=None, description="Industry sector")
    status: str = Field(description="Entity status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    archived_at: Optional[datetime] = Field(default=None, description="Archive timestamp")
    extra_data: Optional[dict] = Field(default=None, description="Additional metadata")

    model_config = {"from_attributes": True}


class EmployerListOut(ListResponse[EmployerOut]):
    """Paginated employer list response."""
    pass