"""Link API schemas - formal contract."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.api.common import ListResponse


class LinkIn(BaseModel):
    """Link create input schema."""
    employer_id: int = Field(..., description="Employer ID")
    transporter_id: int = Field(..., description="Transporter ID")
    is_authorized: bool = Field(default=True, description="Authorization status")
    notes: Optional[str] = Field(default=None, max_length=500, description="Additional notes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "employer_id": 1,
                "transporter_id": 2,
                "is_authorized": True,
                "notes": "Autorizado por Gerencia de Operaciones"
            }
        }
    }


class LinkUpdateIn(BaseModel):
    """Link partial update schema."""
    is_authorized: Optional[bool] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=500)


class LinkOut(BaseModel):
    """Link response schema."""
    id: int = Field(description="Link ID")
    organization_id: int = Field(description="Organization ID (multi-tenant)")
    employer_id: int = Field(description="Employer ID")
    transporter_id: int = Field(description="Transporter ID")
    is_authorized: bool = Field(description="Authorization status")
    authorization_date: Optional[datetime] = Field(default=None, description="Authorization timestamp")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}


class LinkListOut(ListResponse[LinkOut]):
    """Paginated link list response."""
    pass