"""Auth API schemas - formal contract."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class LoginIn(BaseModel):
    """Login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }
    }


class RegisterIn(BaseModel):
    """Register request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="Password (8-100 chars)")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    organization_name: str = Field(..., min_length=1, max_length=255, description="Organization name")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "full_name": "Juan Perez",
                "organization_name": "Empresa ABC"
            }
        }
    }


class TokenOut(BaseModel):
    """JWT token response."""
    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(default=86400, description="Token lifetime in seconds")

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    """User response schema."""
    id: int = Field(description="User ID")
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(default=None, description="Full name")
    locale: str = Field(default="es", description="Locale (es/en)")
    is_active: bool = Field(default=True, description="Account status")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}


class OrgOut(BaseModel):
    """Organization response schema."""
    id: int = Field(description="Organization ID")
    name: str = Field(description="Organization name")
    is_active: bool = Field(default=True, description="Organization status")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}


class LoginOut(BaseModel):
    """Login response schema."""
    token: TokenOut = Field(description="JWT token")
    user: UserOut = Field(description="User info")
    organization: Optional[OrgOut] = Field(default=None, description="Organization info")

    model_config = {"from_attributes": True}


class RegisterOut(BaseModel):
    """Register response schema."""
    message: str = Field(default="User registered successfully")
    user: UserOut = Field(description="Created user info")
    organization: OrgOut = Field(description="Created organization info")

    model_config = {"from_attributes": True}