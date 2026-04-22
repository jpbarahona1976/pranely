"""Residue API schemas - formal contract."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.api.common import ListResponse


class ResidueIn(BaseModel):
    """Residue create input schema."""
    employer_id: int = Field(..., description="Associated employer ID")
    transporter_id: Optional[int] = Field(default=None, description="Associated transporter ID")
    name: str = Field(..., min_length=1, max_length=255, description="Residue name")
    waste_type: str = Field(..., description="Waste type (peligroso/especial/inertes/organico/reciclable)")
    un_code: Optional[str] = Field(default=None, max_length=20, description="UN number")
    hs_code: Optional[str] = Field(default=None, max_length=20, description="HS code")
    description: Optional[str] = Field(default=None, max_length=1000, description="Description")
    weight_kg: Optional[float] = Field(default=None, ge=0, description="Weight in kg")
    volume_m3: Optional[float] = Field(default=None, ge=0, description="Volume in m3")
    status: str = Field(default="pending", description="Residue status")
    extra_data: Optional[dict] = Field(default=None, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "employer_id": 1,
                "transporter_id": 2,
                "name": "Residuo Metálico Peligroso",
                "waste_type": "peligroso",
                "un_code": "UN3077",
                "hs_code": "3824.99",
                "description": "Scrap metal contaminated with oil",
                "weight_kg": 500.5,
                "volume_m3": 2.0,
                "status": "pending"
            }
        }
    }


class ResidueUpdateIn(BaseModel):
    """Residue partial update schema."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    waste_type: Optional[str] = Field(default=None)
    un_code: Optional[str] = Field(default=None, max_length=20)
    hs_code: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = Field(default=None, max_length=1000)
    weight_kg: Optional[float] = Field(default=None, ge=0)
    volume_m3: Optional[float] = Field(default=None, ge=0)
    transporter_id: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    extra_data: Optional[dict] = Field(default=None)


class ResidueOut(BaseModel):
    """Residue response schema."""
    id: int = Field(description="Residue ID")
    organization_id: int = Field(description="Organization ID (multi-tenant)")
    employer_id: int = Field(description="Employer ID")
    transporter_id: Optional[int] = Field(default=None, description="Transporter ID")
    name: str = Field(description="Residue name")
    waste_type: str = Field(description="Waste type (NOM-052)")
    un_code: Optional[str] = Field(default=None, description="UN number")
    hs_code: Optional[str] = Field(default=None, description="HS code")
    description: Optional[str] = Field(default=None, description="Description")
    weight_kg: Optional[float] = Field(default=None, description="Weight in kg")
    volume_m3: Optional[float] = Field(default=None, description="Volume in m3")
    status: str = Field(description="Residue status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update")
    extra_data: Optional[dict] = Field(default=None, description="Additional metadata")

    model_config = {"from_attributes": True}


class ResidueListOut(ListResponse[ResidueOut]):
    """Paginated residue list response."""
    pass