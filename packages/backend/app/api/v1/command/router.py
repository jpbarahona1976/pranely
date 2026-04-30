"""
Command Center API v1 - Admin panel for configuration, operators, quotas, feature flags.

RBAC FIX 8B:
- Owner: full access (read + write)
- Admin: full access (read + write)
- Director: full access (read + write) - NEW
- Member: read-only (GET allowed, mutations denied) - FIXED
- Viewer: NO ACCESS (403)

PERSISTENCE FIX 8B:
- Feature flags stored in Organization.extra_data JSON field
- Persists across restarts/reboots

IMPORTANT: Member role is now read-only in Command Center per audit fix.
For mutations (POST/PATCH/DELETE), Member receives 403.
For reads (GET), Member is allowed.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.audit import create_audit_log
from app.models import (
    User, Organization, Membership, UserRole,
    AuditLog, AuditLogResult,
    Subscription, BillingPlan, UsageCycle,
    WasteMovement, MovementStatus,
)
from app.api.v1.deps import get_current_user_with_org
from app.schemas.api.v1.command import (
    OperatorResponse, OperatorListResponse,
    InviteOperatorRequest, InviteOperatorResponse,
    UpdateOperatorRoleRequest, RemoveOperatorRequest,
    TenantConfigResponse, TenantConfigUpdateRequest, TenantConfigUpdateResponse,
    QuotaInfoResponse, QuotaLimitUpdateRequest, QuotaLimitUpdateResponse,
    FeatureFlagResponse, FeatureFlagListResponse,
    FeatureFlagUpdateRequest, FeatureFlagUpdateResponse,
    AuditEntryResponse, AuditLogListResponse, AuditLogFilter,
    CommandCenterStatsResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/command", tags=["Command Center"])


# =============================================================================
# PERMISSION HELPERS
# =============================================================================

def require_command_access(role: str) -> None:
    """Ensure user has access to Command Center.
    
    FIX 8B: Added DIRECTOR role with full access.
    FIX 8B: Member can access (for read-only) but mutations are blocked separately.
    """
    if role not in ("owner", "admin", "director"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Access denied",
                "status": 403,
                "detail": "Command Center requires owner, admin, or director role",
            },
        )


def require_command_write(role: str) -> None:
    """Ensure user can write/modify Command Center settings.
    
    FIX 8B: Member can READ (GET) but cannot WRITE (POST/PATCH/DELETE).
    This enforces the read-only constraint for Member role.
    """
    if role not in ("owner", "admin", "director"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Write access denied",
                "status": 403,
                "detail": "This action requires owner, admin, or director role. Member role is read-only in Command Center.",
            },
        )


def require_command_admin(role: str) -> None:
    """Ensure user can perform admin-level operations."""
    if role not in ("owner",):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Owner required",
                "status": 403,
                "detail": "This action requires owner role",
            },
        )


def can_view_command_center(role: str) -> bool:
    """Check if role can view (read) Command Center.
    
    FIX 8B: Member can now view (GET) but cannot mutate.
    """
    return role in ("owner", "admin", "director", "member")


def can_mutate_command_center(role: str) -> bool:
    """Check if role can mutate Command Center.
    
    FIX 8B: Member is read-only, cannot mutate.
    """
    return role in ("owner", "admin", "director")


# =============================================================================
# PERMISSIONS MAPPING
# =============================================================================

def _get_permissions_for_role(role: str) -> list[str]:
    """Map role to permissions list.
    
    FIX 8B: Added DIRECTOR with full permissions.
    FIX 8B: Member has read-only permissions (no manage_operators, etc.)
    """
    base = ["read"]
    
    if role == "owner":
        return base + ["manage_operators", "change_config", "view_quotas", "toggle_features", "view_audit"]
    if role == "admin":
        return base + ["manage_operators", "change_config", "view_quotas", "toggle_features", "view_audit"]
    if role == "director":
        # Director has full access per PRD
        return base + ["manage_operators", "change_config", "view_quotas", "toggle_features", "view_audit"]
    if role == "member":
        # FIX 8B: Member is read-only - only view quotas
        return base + ["view_quotas"]
    
    # viewer has no special permissions
    return base


# =============================================================================
# FEATURE FLAGS - PERSISTENCE FIX 8B
# =============================================================================

# Default feature flags (used when org has no flags in extra_data)
DEFAULT_FLAGS = [
    {"key": "mobile_bridge", "enabled": True, "description": "Mobile Bridge QR/WS functionality"},
    {"key": "ai_extraction", "enabled": True, "description": "AI document extraction"},
    {"key": "legal_radar", "enabled": True, "description": "Legal/Radar compliance alerts"},
    {"key": "advanced_export", "enabled": False, "description": "Advanced export formats (Excel, PDF)"},
    {"key": "multi_language", "enabled": False, "description": "Multi-language support (EN/ES)"},
]


def _get_org_feature_flags(org: Organization) -> list[dict]:
    """Get feature flags from organization's extra_data.
    
    FIX 8B: Feature flags now persist in DB via Organization.extra_data JSON.
    Falls back to defaults if no flags stored.
    """
    if org.extra_data and "feature_flags" in org.extra_data:
        return org.extra_data["feature_flags"]
    return DEFAULT_FLAGS.copy()


def _set_org_feature_flags(org: Organization, flags: list[dict]) -> None:
    """Store feature flags in organization's extra_data.
    
    FIX 8B: Persists flags in DB, survives restarts.
    """
    if org.extra_data is None:
        org.extra_data = {}
    org.extra_data["feature_flags"] = flags


def _update_single_flag(org: Organization, flag_key: str, enabled: bool) -> Optional[dict]:
    """Update a single feature flag in organization's extra_data.
    
    FIX 8B: In-place update persists to DB.
    """
    flags = _get_org_feature_flags(org)
    
    for flag in flags:
        if flag["key"] == flag_key:
            old_value = flag["enabled"]
            flag["enabled"] = enabled
            _set_org_feature_flags(org, flags)
            return {"key": flag_key, "enabled": enabled, "previous": old_value}
    
    return None


# =============================================================================
# OPERATORS - Member management
# =============================================================================

@router.get(
    "/operators",
    response_model=OperatorListResponse,
    summary="List operators",
    description="List all operators in the tenant organization. Available to: owner, admin, director, member.",
)
async def list_operators(
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> OperatorListResponse:
    """List all operators/members in the organization.
    
    FIX 8B: Now accessible to member (read-only).
    """
    user, org_id = user_org
    
    # FIX 8B: Allow member to view (GET)
    if not can_view_command_center(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Access denied",
                "status": 403,
                "detail": "You do not have permission to view operators",
            },
        )
    
    # Query all memberships with user details
    result = await db.execute(
        select(Membership)
        .where(Membership.organization_id == org_id)
        .options(selectinload(Membership.user))
        .order_by(Membership.created_at.desc())
    )
    memberships = result.scalars().all()
    
    operators = [
        OperatorResponse(
            id=m.id,
            user_id=m.user_id,
            email=m.user.email if m.user else "",
            full_name=m.user.full_name if m.user else None,
            role=m.role.value,
            is_active=m.user.is_active if m.user else False,
            created_at=m.created_at,
            permissions=_get_permissions_for_role(m.role.value),
        )
        for m in memberships
        if m.user
    ]
    
    return OperatorListResponse(operators=operators, total=len(operators))


@router.post(
    "/operators/invite",
    response_model=InviteOperatorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite operator",
    description="Invite a new user to the organization with specified role. Owner/Admin/Director only.",
)
async def invite_operator(
    request: InviteOperatorRequest,
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> InviteOperatorResponse:
    """Invite a new operator to the organization.
    
    FIX 8B: Member cannot invite (write access denied).
    """
    user, org_id = user_org
    
    # FIX 8B: Only owner/admin/director can invite
    require_command_write(user.role)
    
    # Validate role is not director (can't invite as director via this endpoint)
    if request.role == "director":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Invalid role",
                "status": 400,
                "detail": "Cannot invite users with director role via this endpoint",
            },
        )
    
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Check if already a member
        result = await db.execute(
            select(Membership).where(
                Membership.user_id == existing_user.id,
                Membership.organization_id == org_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "https://api.pranely.com/errors/command",
                    "title": "Already member",
                    "status": 400,
                    "detail": "User is already an operator in this organization",
                },
            )
        
        # Add existing user as member
        role_enum = UserRole(request.role)
        membership = Membership(
            user_id=existing_user.id,
            organization_id=org_id,
            role=role_enum,
        )
        db.add(membership)
        
        await create_audit_log(
            db=db,
            org_id=org_id,
            user_id=user.id,
            action="operator.invite_existing",
            resource_type="membership",
            resource_id=str(membership.id),
            result=AuditLogResult.SUCCESS,
            details={"email": request.email, "role": request.role},
        )
        
        await db.commit()
        await db.refresh(membership)
        
        return InviteOperatorResponse(
            message=f"User {request.email} added as {request.role}",
            operator=OperatorResponse(
                id=membership.id,
                user_id=existing_user.id,
                email=existing_user.email,
                full_name=existing_user.full_name,
                role=request.role,
                is_active=existing_user.is_active,
                created_at=membership.created_at,
                permissions=_get_permissions_for_role(request.role),
            ),
        )
    
    # Create new user (pending activation)
    hashed_pw = "PLACEHOLDER"  # User must set password via invite flow
    new_user = User(
        email=request.email,
        hashed_password=hashed_pw,
        full_name=request.full_name,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()
    
    # Create membership
    role_enum = UserRole(request.role)
    membership = Membership(
        user_id=new_user.id,
        organization_id=org_id,
        role=role_enum,
    )
    db.add(membership)
    
    await create_audit_log(
        db=db,
        org_id=org_id,
        user_id=user.id,
        action="operator.invite_new",
        resource_type="membership",
        resource_id=str(membership.id),
        result=AuditLogResult.SUCCESS,
        details={"email": request.email, "role": request.role},
    )
    
    await db.commit()
    await db.refresh(membership)
    await db.refresh(new_user)
    
    return InviteOperatorResponse(
        message=f"Operator {request.email} invited as {request.role}",
        operator=OperatorResponse(
            id=membership.id,
            user_id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            role=request.role,
            is_active=new_user.is_active,
            created_at=membership.created_at,
            permissions=_get_permissions_for_role(request.role),
        ),
    )


@router.patch(
    "/operators/{membership_id}/role",
    response_model=InviteOperatorResponse,
    summary="Update operator role",
    description="Change the role of an existing operator. Owner/Admin/Director only.",
)
async def update_operator_role(
    membership_id: int,
    request: UpdateOperatorRoleRequest,
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> InviteOperatorResponse:
    """Update the role of an existing operator.
    
    FIX 8B: Member cannot update roles (write access denied).
    """
    user, org_id = user_org
    
    # FIX 8B: Only owner/admin/director can update roles
    require_command_write(user.role)
    
    # Get membership
    result = await db.execute(
        select(Membership)
        .where(
            Membership.id == membership_id,
            Membership.organization_id == org_id,
        )
        .options(selectinload(Membership.user))
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Operator not found",
                "status": 404,
                "detail": "Membership not found in this organization",
            },
        )
    
    # Cannot change owner role
    if membership.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Cannot change owner",
                "status": 400,
                "detail": "Cannot change the role of the organization owner",
            },
        )
    
    # Cannot change director role (unless you're owner)
    if membership.role == UserRole.DIRECTOR and user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Cannot change director",
                "status": 400,
                "detail": "Only owner can change director role",
            },
        )
    
    # Cannot demote yourself if you're the only owner
    if membership.user_id == user.id and request.role not in ("owner", "admin", "director"):
        result = await db.execute(
            select(Membership).where(
                Membership.organization_id == org_id,
                Membership.role == UserRole.OWNER,
            )
        )
        owner_count = len(result.scalars().all())
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "https://api.pranely.com/errors/command",
                    "title": "Last owner",
                    "status": 400,
                    "detail": "Cannot demote the last owner of the organization",
                },
            )
    
    # Update role
    old_role = membership.role.value
    membership.role = UserRole(request.role)
    
    await create_audit_log(
        db=db,
        org_id=org_id,
        user_id=user.id,
        action="operator.role_changed",
        resource_type="membership",
        resource_id=str(membership_id),
        result=AuditLogResult.SUCCESS,
        details={"old_role": old_role, "new_role": request.role},
    )
    
    await db.commit()
    await db.refresh(membership)
    
    return InviteOperatorResponse(
        message=f"Role updated from {old_role} to {request.role}",
        operator=OperatorResponse(
            id=membership.id,
            user_id=membership.user_id,
            email=membership.user.email if membership.user else "",
            full_name=membership.user.full_name if membership.user else None,
            role=request.role,
            is_active=membership.user.is_active if membership.user else False,
            created_at=membership.created_at,
            permissions=_get_permissions_for_role(request.role),
        ),
    )


@router.delete(
    "/operators/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove operator",
    description="Remove an operator from the organization. Owner/Admin/Director only.",
)
async def remove_operator(
    membership_id: int,
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
):
    """Remove an operator from the organization.
    
    FIX 8B: Member cannot remove operators (write access denied).
    """
    user, org_id = user_org
    
    # FIX 8B: Only owner/admin/director can remove
    require_command_write(user.role)
    
    # Get membership
    result = await db.execute(
        select(Membership)
        .where(
            Membership.id == membership_id,
            Membership.organization_id == org_id,
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Operator not found",
                "status": 404,
                "detail": "Membership not found in this organization",
            },
        )
    
    # Cannot remove owner
    if membership.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Cannot remove owner",
                "status": 400,
                "detail": "Cannot remove the organization owner",
            },
        )
    
    # Cannot remove yourself
    if membership.user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Cannot remove self",
                "status": 400,
                "detail": "Cannot remove yourself from the organization",
            },
        )
    
    # Delete membership
    await db.delete(membership)
    
    await create_audit_log(
        db=db,
        org_id=org_id,
        user_id=user.id,
        action="operator.removed",
        resource_type="membership",
        resource_id=str(membership_id),
        result=AuditLogResult.SUCCESS,
        details={"removed_user_id": membership.user_id},
    )
    
    await db.commit()


# =============================================================================
# CONFIG - Tenant configuration
# =============================================================================

@router.get(
    "/config",
    response_model=TenantConfigResponse,
    summary="Get tenant configuration",
    description="Get the current tenant organization configuration. Available to: owner, admin, director, member.",
)
async def get_config(
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> TenantConfigResponse:
    """Get tenant configuration.
    
    FIX 8B: Now accessible to member (read-only).
    """
    user, org_id = user_org
    
    # FIX 8B: Allow member to view (GET)
    if not can_view_command_center(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Access denied",
                "status": 403,
                "detail": "You do not have permission to view configuration",
            },
        )
    
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Organization not found",
                "status": 404,
                "detail": "Organization not found",
            },
        )
    
    return TenantConfigResponse(
        organization_id=org.id,
        name=org.name,
        industry=org.industry,
        segment=org.segment,
        locale="es",
        timezone="America/Mexico_City",
        updated_at=org.updated_at,
    )


@router.patch(
    "/config",
    response_model=TenantConfigUpdateResponse,
    summary="Update tenant configuration",
    description="Update the tenant organization configuration. Owner/Admin/Director only.",
)
async def update_config(
    request: TenantConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> TenantConfigUpdateResponse:
    """Update tenant configuration.
    
    FIX 8B: Member cannot update config (write access denied).
    """
    user, org_id = user_org
    
    # FIX 8B: Only owner/admin/director can update
    require_command_write(user.role)
    
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Organization not found",
                "status": 404,
                "detail": "Organization not found",
            },
        )
    
    # Update fields
    changes = {}
    if request.name is not None:
        changes["name"] = request.name
        org.name = request.name
    if request.industry is not None:
        changes["industry"] = request.industry
        org.industry = request.industry
    if request.segment is not None:
        changes["segment"] = request.segment
        org.segment = request.segment
    
    org.updated_at = datetime.utcnow()
    
    await create_audit_log(
        db=db,
        org_id=org_id,
        user_id=user.id,
        action="config.updated",
        resource_type="organization",
        resource_id=str(org_id),
        result=AuditLogResult.SUCCESS,
        details=changes,
    )
    
    await db.commit()
    await db.refresh(org)
    
    return TenantConfigUpdateResponse(
        message="Configuration updated successfully",
        config=TenantConfigResponse(
            organization_id=org.id,
            name=org.name,
            industry=org.industry,
            segment=org.segment,
            locale="es",
            timezone="America/Mexico_City",
            updated_at=org.updated_at,
        ),
    )


# =============================================================================
# QUOTAS - Usage limits
# =============================================================================

@router.get(
    "/quotas",
    response_model=QuotaInfoResponse,
    summary="Get quota information",
    description="Get current usage and limits for the tenant. Available to: owner, admin, director, member.",
)
async def get_quotas(
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> QuotaInfoResponse:
    """Get current quota information.
    
    FIX 8B: Now accessible to member (read-only).
    """
    user, org_id = user_org
    
    # FIX 8B: Allow member to view (GET)
    if not can_view_command_center(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Access denied",
                "status": 403,
                "detail": "You do not have permission to view quotas",
            },
        )
    
    # Get subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == org_id)
        .options(selectinload(Subscription.plan))
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        return QuotaInfoResponse(
            plan_code="free",
            plan_name="Free",
            doc_limit=100,
            docs_used=0,
            docs_remaining=100,
            period="monthly",
            period_start=None,
            period_end=None,
            status="active",
        )
    
    # Get current usage
    current_month = datetime.utcnow().strftime("%Y-%m")
    result = await db.execute(
        select(UsageCycle)
        .where(
            UsageCycle.subscription_id == subscription.id,
            UsageCycle.month_year == current_month,
        )
    )
    usage = result.scalar_one_or_none()
    
    plan = subscription.plan
    docs_limit = plan.doc_limit if plan else 100
    docs_used = usage.docs_used if usage else 0
    
    return QuotaInfoResponse(
        plan_code=plan.code.value if plan else "free",
        plan_name=plan.name if plan else "Free",
        doc_limit=docs_limit,
        docs_used=docs_used,
        docs_remaining=max(0, docs_limit - docs_used),
        period=plan.doc_limit_period if plan else "monthly",
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        status=subscription.status.value,
    )


@router.post(
    "/quotas/upgrade-request",
    response_model=QuotaLimitUpdateResponse,
    summary="Request limit increase",
    description="Request a limit increase. Owner/Admin/Director only.",
)
async def request_quota_increase(
    request: QuotaLimitUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> QuotaLimitUpdateResponse:
    """Request a quota increase.
    
    FIX 8B: Member cannot request upgrade (write access denied).
    """
    user, org_id = user_org
    
    # FIX 8B: Only owner/admin/director can request
    require_command_write(user.role)
    
    # Get current subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == org_id)
        .options(selectinload(Subscription.plan))
    )
    subscription = result.scalar_one_or_none()
    
    current_limit = subscription.plan.doc_limit if subscription and subscription.plan else 100
    
    await create_audit_log(
        db=db,
        org_id=org_id,
        user_id=user.id,
        action="quota.upgrade_requested",
        resource_type="subscription",
        resource_id=str(subscription.id) if subscription else None,
        result=AuditLogResult.SUCCESS,
        details={"current_limit": current_limit, "requested_limit": request.requested_limit},
    )
    
    requires_upgrade = request.requested_limit > current_limit
    
    return QuotaLimitUpdateResponse(
        message="Upgrade request submitted" if requires_upgrade else "Limit within current plan",
        current_limit=current_limit,
        requested_limit=request.requested_limit,
        requires_upgrade=requires_upgrade,
    )


# =============================================================================
# FEATURE FLAGS - PERSISTENCE FIX 8B (stored in Organization.extra_data)
# =============================================================================

@router.get(
    "/features",
    response_model=FeatureFlagListResponse,
    summary="List feature flags",
    description="List all feature flags for the tenant. Available to: owner, admin, director, member.",
)
async def list_features(
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> FeatureFlagListResponse:
    """List feature flags.
    
    FIX 8B: Now accessible to member (read-only).
    FIX 8B: Flags are read from Organization.extra_data (persisted in DB).
    """
    user, org_id = user_org
    
    # FIX 8B: Allow member to view (GET)
    if not can_view_command_center(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Access denied",
                "status": 403,
                "detail": "You do not have permission to view feature flags",
            },
        )
    
    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Organization not found",
                "status": 404,
                "detail": "Organization not found",
            },
        )
    
    # Get flags from org.extra_data (persisted)
    flags = _get_org_feature_flags(org)
    
    return FeatureFlagListResponse(
        flags=[
            FeatureFlagResponse(
                key=f["key"],
                enabled=f["enabled"],
                description=f.get("description"),
                updated_at=None,
            )
            for f in flags
        ],
        total=len(flags),
    )


@router.patch(
    "/features/{flag_key}",
    response_model=FeatureFlagUpdateResponse,
    summary="Update feature flag",
    description="Enable or disable a feature flag. Owner/Admin/Director only.",
)
async def update_feature(
    flag_key: str,
    request: FeatureFlagUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> FeatureFlagUpdateResponse:
    """Update a feature flag.
    
    FIX 8B: Member cannot toggle features (write access denied).
    FIX 8B: Flag state is persisted in Organization.extra_data (survives restarts).
    """
    user, org_id = user_org
    
    # FIX 8B: Only owner/admin/director can toggle
    require_command_write(user.role)
    
    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Organization not found",
                "status": 404,
                "detail": "Organization not found",
            },
        )
    
    # Find and update flag (persisted in extra_data)
    result_update = _update_single_flag(org, flag_key, request.enabled)
    
    if not result_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Feature not found",
                "status": 404,
                "detail": f"Feature '{flag_key}' does not exist",
            },
        )
    
    await create_audit_log(
        db=db,
        org_id=org_id,
        user_id=user.id,
        action="feature.toggled",
        resource_type="feature_flag",
        resource_id=flag_key,
        result=AuditLogResult.SUCCESS,
        details={"enabled": request.enabled, "previous": result_update["previous"]},
    )
    
    await db.commit()
    
    return FeatureFlagUpdateResponse(
        message=f"Feature '{flag_key}' {'enabled' if request.enabled else 'disabled'}",
        flag=FeatureFlagResponse(
            key=flag_key,
            enabled=request.enabled,
            description=None,
            updated_at=datetime.utcnow(),
        ),
    )


# =============================================================================
# AUDIT LOGS - Command center audit trail
# =============================================================================

@router.get(
    "/audit",
    response_model=AuditLogListResponse,
    summary="List audit logs",
    description="List audit logs for command center actions. Available to: owner, admin, director, member.",
)
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action_filter: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
) -> AuditLogListResponse:
    """List audit logs for the organization.
    
    FIX 8B: Now accessible to member (read-only).
    """
    user, org_id = user_org
    
    # FIX 8B: Allow member to view (GET)
    if not can_view_command_center(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Access denied",
                "status": 403,
                "detail": "You do not have permission to view audit logs",
            },
        )
    
    # Build query
    query = select(AuditLog).where(AuditLog.organization_id == org_id)
    
    if action_filter:
        query = query.where(AuditLog.action.like(f"{action_filter}%"))
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    
    query = query.order_by(AuditLog.timestamp.desc())
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Get user emails
    user_ids = [log.user_id for log in logs if log.user_id]
    users_map = {}
    if user_ids:
        user_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users_map = {u.id: u.email for u in user_result.scalars().all()}
    
    return AuditLogListResponse(
        entries=[
            AuditEntryResponse(
                id=log.id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                result=log.result.value,
                user_email=users_map.get(log.user_id) if log.user_id else None,
                ip_address=log.ip_address,
                timestamp=log.timestamp,
                details=log.payload_json,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# STATS - Command center overview
# =============================================================================

@router.get(
    "/stats",
    response_model=CommandCenterStatsResponse,
    summary="Get command center stats",
    description="Get overview statistics for the command center. Available to: owner, admin, director, member.",
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> CommandCenterStatsResponse:
    """Get command center statistics.
    
    FIX 8B: Now accessible to member (read-only).
    """
    user, org_id = user_org
    
    # FIX 8B: Allow member to view (GET)
    if not can_view_command_center(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Access denied",
                "status": 403,
                "detail": "You do not have permission to view command center stats",
            },
        )
    
    # Count operators
    result = await db.execute(
        select(func.count()).select_from(Membership)
        .where(Membership.organization_id == org_id)
    )
    total_operators = result.scalar() or 0
    
    # Count active operators
    result = await db.execute(
        select(func.count()).select_from(Membership)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.organization_id == org_id,
            User.is_active == True,
        )
    )
    active_operators = result.scalar() or 0
    
    # Get current plan
    result = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == org_id)
        .options(selectinload(Subscription.plan))
    )
    subscription = result.scalar_one_or_none()
    current_plan = subscription.plan.code.value if subscription and subscription.plan else "free"
    
    # Get usage percentage
    current_month = datetime.utcnow().strftime("%Y-%m")
    doc_limit = 100
    docs_used = 0
    
    if subscription:
        doc_limit = subscription.plan.doc_limit if subscription.plan else 100
        result = await db.execute(
            select(UsageCycle)
            .where(
                UsageCycle.subscription_id == subscription.id,
                UsageCycle.month_year == current_month,
            )
        )
        usage = result.scalar_one_or_none()
        docs_used = usage.docs_used if usage else 0
    
    usage_percent = (docs_used / doc_limit * 100) if doc_limit > 0 else 0
    
    # Count recent changes (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(func.count()).select_from(AuditLog)
        .where(
            AuditLog.organization_id == org_id,
            AuditLog.timestamp >= week_ago,
        )
    )
    recent_changes = result.scalar() or 0
    
    # Count pending actions (pending waste movements)
    result = await db.execute(
        select(func.count()).select_from(WasteMovement)
        .where(
            WasteMovement.organization_id == org_id,
            WasteMovement.status == MovementStatus.PENDING,
        )
    )
    pending_actions = result.scalar() or 0
    
    return CommandCenterStatsResponse(
        total_operators=total_operators,
        active_operators=active_operators,
        current_plan=current_plan,
        doc_usage_percent=round(usage_percent, 1),
        pending_actions=pending_actions,
        recent_changes=recent_changes,
    )