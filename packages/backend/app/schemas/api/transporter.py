"""Transporter API schemas - formal contract."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

from app.schemas.api.common import ListResponse


class TransporterIn(BaseModel):
    """Transporter create input schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Transporter name")
    rfc: str = Field(..., min_length=12, max_length=13, description="Tax ID (RFC Mexico)")
    address: str = Field(..., min_length=1, max_length=500, description="Business address")
    contact_phone: Optional[str] = Field(default=None, max_length=30, description="Contact phone")
    email: Optional[EmailStr] = Field(default=None, description="Contact email")
    license_number: Optional[str] = Field(default=None, max_length=100, description="Transport license")
    vehicle_plate: Optional[str] = Field(default=None, max_length=20, description="Primary vehicle plate")
    status: str = Field(default="active", description="Entity status")
    archived_at: Optional[datetime] = Field(default=None, description="Archive timestamp")
    extra_data: Optional[dict] = Field(default=None, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Transportes del Norte",
                "rfc": "TDN123456789",
                "address": "Carretera 40 Km 45, Monterrey, NL",
                "contact_phone": "+52 81 9876 5432",
                "email": "operaciones@transportesnorte.com",
                "license_number": "SEMARNAT-TR-2024-001",
                "vehicle_plate": "ABC-1234",
                "status": "active"
            }
        }
    }


class TransporterUpdateIn(BaseModel):
    """Transporter partial update schema."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    rfc: Optional[str] = Field(default=None, min_length=12, max_length=13)
    address: Optional[str] = Field(default=None, max_length=500)
    contact_phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = Field(default=None)
    license_number: Optional[str] = Field(default=None, max_length=100)
    vehicle_plate: Optional[str] = Field(default=None, max_length=20)
    status: Optional[str] = Field(default=None)
    extra_data: Optional[dict] = Field(default=None)


class TransporterOut(BaseModel):
    """Transporter response schema."""
    id: int = Field(description="Transporter ID")
    organization_id: int = Field(description="Organization ID (multi-tenant)")
    name: str = Field(description="Transporter name")
    rfc: str = Field(description="Tax ID (RFC)")
    address: str = Field(description="Business address")
    contact_phone: Optional[str] = Field(default=None, description="Contact phone")
    email: Optional[str] = Field(default=None, description="Contact email")
    license_number: Optional[str] = Field(default=None, description="Transport license")
    vehicle_plate: Optional[str] = Field(default=None, description="Vehicle plate")
    status: str = Field(description="Entity status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update")
    archived_at: Optional[datetime] = Field(default=None, description="Archive timestamp")
    extra_data: Optional[dict] = Field(default=None, description="Additional metadata")

    model_config = {"from_attributes": True}


class TransporterListOut(ListResponse[TransporterOut]):
    """Paginated transporter list response."""
    pass