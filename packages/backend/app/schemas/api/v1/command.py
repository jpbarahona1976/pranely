"""Pydantic schemas for Command Center API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


# =============================================================================
# OPERATORS - Member management within tenant
# =============================================================================

class OperatorResponse(BaseModel):
    """Schema for operator/member response."""
    id: int
    user_id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    permissions: list[str] = []

    model_config = {"from_attributes": True}


class OperatorListResponse(BaseModel):
    """Schema for listing operators."""
    operators: list[OperatorResponse]
    total: int


class InviteOperatorRequest(BaseModel):
    """Schema for inviting a new operator."""
    email: EmailStr
    role: str = Field(..., pattern="^(admin|member|viewer)$")
    full_name: Optional[str] = None


class InviteOperatorResponse(BaseModel):
    """Schema for invite response."""
    message: str
    operator: Optional[OperatorResponse] = None


class UpdateOperatorRoleRequest(BaseModel):
    """Schema for updating operator role."""
    role: str = Field(..., pattern="^(admin|member|viewer)$")


class RemoveOperatorRequest(BaseModel):
    """Schema for removing an operator."""
    user_id: int


# =============================================================================
# CONFIG - Tenant configuration
# =============================================================================

class TenantConfigResponse(BaseModel):
    """Schema for tenant configuration."""
    organization_id: int
    name: str
    industry: Optional[str]
    segment: Optional[str]
    locale: str = "es"
    timezone: str = "America/Mexico_City"
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TenantConfigUpdateRequest(BaseModel):
    """Schema for updating tenant configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    segment: Optional[str] = Field(None, max_length=100)
    locale: Optional[str] = Field(None, pattern="^(es|en)$")
    timezone: Optional[str] = Field(None, max_length=50)


class TenantConfigUpdateResponse(BaseModel):
    """Schema for config update response."""
    message: str
    config: TenantConfigResponse


# =============================================================================
# QUOTAS - Usage limits management
# =============================================================================

class QuotaInfoResponse(BaseModel):
    """Schema for quota information."""
    plan_code: str
    plan_name: str
    doc_limit: int
    docs_used: int
    docs_remaining: int
    period: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    status: str  # active, paused, past_due

    model_config = {"from_attributes": True}


class QuotaLimitUpdateRequest(BaseModel):
    """Schema for requesting limit increase (stub for MVP)."""
    requested_limit: int = Field(..., gt=0)


class QuotaLimitUpdateResponse(BaseModel):
    """Schema for quota limit update response."""
    message: str
    current_limit: int
    requested_limit: int
    requires_upgrade: bool


# =============================================================================
# FEATURE FLAGS - Feature toggles
# =============================================================================

class FeatureFlagResponse(BaseModel):
    """Schema for feature flag."""
    key: str
    enabled: bool
    description: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FeatureFlagListResponse(BaseModel):
    """Schema for listing feature flags."""
    flags: list[FeatureFlagResponse]
    total: int


class FeatureFlagUpdateRequest(BaseModel):
    """Schema for updating a feature flag."""
    enabled: bool


class FeatureFlagUpdateResponse(BaseModel):
    """Schema for feature flag update response."""
    message: str
    flag: FeatureFlagResponse


# =============================================================================
# AUDIT LOGS - Command center audit trail
# =============================================================================

class AuditEntryResponse(BaseModel):
    """Schema for audit log entry."""
    id: int
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    result: str
    user_email: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime
    details: Optional[dict] = None

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Schema for listing audit logs."""
    entries: list[AuditEntryResponse]
    total: int
    page: int
    page_size: int


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs."""
    action: Optional[str] = None
    resource_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


# =============================================================================
# COMMAND CENTER STATS
# =============================================================================

class CommandCenterStatsResponse(BaseModel):
    """Schema for command center statistics."""
    total_operators: int
    active_operators: int
    current_plan: str
    doc_usage_percent: float
    pending_actions: int
    recent_changes: int

    model_config = {"from_attributes": True}