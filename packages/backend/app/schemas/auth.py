"""Pydantic schemas for authentication endpoints."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# --- Request Schemas ---

class RegisterRequest(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 chars)")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    organization_name: str = Field(..., min_length=1, max_length=255, description="Organization name")


class LoginRequest(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Password")


# --- Response Schemas ---

class UserResponse(BaseModel):
    """Schema for user data in responses."""
    id: int
    email: str
    full_name: Optional[str]
    locale: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationResponse(BaseModel):
    """Schema for organization data in responses."""
    id: int
    name: str
    legal_name: Optional[str]
    industry: Optional[str]
    segment: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours in seconds


class AuthResponse(BaseModel):
    """Schema for complete auth response (token + user + org)."""
    token: TokenResponse
    user: UserResponse
    organization: OrganizationResponse


class RegisterResponse(BaseModel):
    """Schema for registration response."""
    message: str = "User registered successfully"
    user: UserResponse
    organization: OrganizationResponse


class ErrorResponse(BaseModel):
    """Schema for error responses (RFC 7807 style)."""
    type: str = "https://api.pranely.com/errors/auth"
    title: str
    status: int
    detail: str
    instance: Optional[str] = None


# --- Refresh Schema ---

class RefreshRequest(BaseModel):
    """Schema for token refresh request."""
    access_token: str = Field(..., description="Current valid access token")


class RefreshResponse(BaseModel):
    """Schema for token refresh response."""
    token: TokenResponse
    user: UserResponse