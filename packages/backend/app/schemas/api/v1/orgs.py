"""Organizations API schemas v1 - centralized for Fase 5A."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class OrganizationIn(BaseModel):
    """Organization create/update schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    legal_name: Optional[str] = Field(default=None, max_length=255, description="Legal name")
    rfc: Optional[str] = Field(default=None, max_length=13, description="RFC (Mexican tax ID)")
    industry: Optional[str] = Field(default=None, max_length=100, description="Industry sector")
    address: Optional[str] = Field(default=None, max_length=500, description="Address")
    city: Optional[str] = Field(default=None, max_length=100, description="City")
    state: Optional[str] = Field(default=None, max_length=100, description="State")
    zip_code: Optional[str] = Field(default=None, max_length=10, description="ZIP code")
    country: str = Field(default="MX", description="Country code (ISO 3166-1 alpha-2)")

    model_config = {"from_attributes": True}


class OrganizationOut(BaseModel):
    """Organization response schema."""
    id: int = Field(description="Organization ID")
    name: str = Field(description="Organization name")
    legal_name: Optional[str] = Field(default=None, description="Legal name")
    rfc: Optional[str] = Field(default=None, description="RFC")
    industry: Optional[str] = Field(default=None, description="Industry")
    address: Optional[str] = Field(default=None, description="Address")
    city: Optional[str] = Field(default=None, description="City")
    state: Optional[str] = Field(default=None, description="State")
    zip_code: Optional[str] = Field(default=None, description="ZIP code")
    country: str = Field(default="MX", description="Country")
    is_active: bool = Field(default=True, description="Active status")
    stripe_customer_id: Optional[str] = Field(default=None, description="Stripe customer ID")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class OrganizationListOut(BaseModel):
    """Organization list response schema."""
    items: List[OrganizationOut] = Field(description="List of organizations")
    total: int = Field(description="Total number of organizations")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")


class MembershipIn(BaseModel):
    """Membership create schema."""
    user_id: int = Field(..., description="User ID")
    organization_id: int = Field(..., description="Organization ID")
    role: str = Field(..., description="Role (owner/admin/member/viewer)")

    model_config = {"from_attributes": True}


class MembershipOut(BaseModel):
    """Membership response schema."""
    id: int = Field(description="Membership ID")
    user_id: int = Field(description="User ID")
    organization_id: int = Field(description="Organization ID")
    role: str = Field(description="Role")
    is_active: bool = Field(default=True, description="Active status")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}


class MemberUserOut(BaseModel):
    """Member user info in organization context."""
    id: int = Field(description="User ID")
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(default=None, description="Full name")
    role: str = Field(description="Role in organization")
    is_active: bool = Field(default=True, description="Account status")
    joined_at: datetime = Field(description="Membership creation timestamp")

    model_config = {"from_attributes": True}


class OrganizationMembersOut(BaseModel):
    """Organization members list response."""
    items: List[MemberUserOut] = Field(description="List of members")
    total: int = Field(description="Total number of members")
