"""Command operator management (FASE 2 FIX 4)

POST /api/v1/command/operators
- role + extra_data JSONB
- tenant filter (organization_id REQUIRED)
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import User, Organization, Membership, UserRole
from app.api.deps import get_current_active_user, get_current_active_organization

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/command", tags=["command"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class OperatorRoleUpdate(BaseModel):
    """Schema for updating operator role."""
    membership_id: int
    role: str = Field(..., pattern="^(admin|member|viewer)$")
    extra_data: Optional[dict] = None


class OperatorResponse(BaseModel):
    """Response for operator operations."""
    id: int
    user_id: int
    email: str
    full_name: Optional[str]
    role: str
    extra_data: Optional[dict]
    created_at: datetime


class OperatorCreateRequest(BaseModel):
    """Schema for creating a new operator."""
    email: str
    role: str = Field(..., pattern="^(admin|member|viewer)$")
    full_name: Optional[str] = None
    extra_data: Optional[dict] = None


class OperatorListResponse(BaseModel):
    """Response for listing operators."""
    operators: list[OperatorResponse]
    total: int


class OperatorUpdateResponse(BaseModel):
    """Response for operator update."""
    success: bool
    operator: OperatorResponse
    message: str


# =============================================================================
# Permission helpers
# =============================================================================

ALLOWED_ROLES = {"owner", "admin"}
MUTABLE_ROLES = {"admin", "member", "viewer"}  # Cannot set owner/director via this


def check_can_manage_operators(user: User, membership: Membership) -> bool:
    """Check if user can manage operators."""
    if membership.role == UserRole.OWNER:
        return True
    if membership.role == UserRole.ADMIN:
        return True
    return False


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/operators",
    response_model=OperatorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create operator",
    description="Create a new operator in the organization with role and extra_data.",
)
async def create_operator(
    data: OperatorCreateRequest,
    user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> OperatorResponse:
    """
    Create a new operator in the organization.
    
    - **email**: Email of the user to add
    - **role**: Role to assign (admin, member, viewer)
    - **full_name**: Optional full name
    - **extra_data**: JSONB field for additional metadata
    
    Requires owner/admin role.
    Organization isolation enforced.
    """
    # Get current user's membership
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org.id,
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership or not check_can_manage_operators(user, membership):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Forbidden",
                "status": 403,
                "detail": "You do not have permission to manage operators",
            },
        )
    
    # Validate role (cannot create owner/director via this endpoint)
    if data.role not in MUTABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Invalid role",
                "status": 400,
                "detail": f"Cannot create operator with role '{data.role}'. Allowed: {MUTABLE_ROLES}",
            },
        )
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        # Create placeholder user (will need to verify email)
        from app.core.security import hash_password
        target_user = User(
            email=data.email,
            hashed_password=hash_password("PLACEHOLDER_CHANGE_ME"),
            full_name=data.full_name,
            is_active=False,  # Require email verification
        )
        db.add(target_user)
        await db.flush()
    
    # Check if already member
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == target_user.id,
            Membership.organization_id == org.id,
        )
    )
    existing_membership = result.scalar_one_or_none()
    
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Already operator",
                "status": 400,
                "detail": "User is already an operator in this organization",
            },
        )
    
    # Create membership with extra_data (FASE 2.1 FIX 4: Persist extra_data)
    role_enum = UserRole(data.role)
    
    membership = Membership(
        user_id=target_user.id,
        organization_id=org.id,
        role=role_enum,
        extra_data=data.extra_data,  # FASE 2.1 FIX 4: Store operator metadata
    )
    
    db.add(membership)
    
    logger.info(
        f"Created operator: email={data.email}, role={data.role}, "
        f"org_id={org.id}, extra_data={data.extra_data}"
    )
    
    await db.commit()
    await db.refresh(membership)
    
    return OperatorResponse(
        id=membership.id,
        user_id=target_user.id,
        email=target_user.email,
        full_name=target_user.full_name,
        role=data.role,
        extra_data=data.extra_data,
        created_at=membership.created_at,
    )


@router.get(
    "/operators",
    response_model=OperatorListResponse,
    summary="List operators",
    description="List all operators in the organization with role and extra_data.",
)
async def list_operators(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> OperatorListResponse:
    """
    List all operators in the organization.
    
    - **page**: Page number (1-based)
    - **page_size**: Items per page (max 100)
    
    Returns operators with role and extra_data.
    Organization isolation enforced (only org's operators returned).
    """
    # Get current user's membership
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org.id,
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Forbidden",
                "status": 403,
                "detail": "You are not a member of this organization",
            },
        )
    
    # Query operators for THIS organization ONLY (tenant isolation)
    offset = (page - 1) * page_size
    
    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(Membership).where(
            Membership.organization_id == org.id  # CRITICAL: tenant filter
        )
    )
    total = count_result.scalar() or 0
    
    # Get operators
    result = await db.execute(
        select(Membership)
        .where(Membership.organization_id == org.id)  # Tenant isolation
        .options(selectinload(Membership.user))
        .order_by(Membership.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    memberships = result.scalars().all()
    
    operators = [
        OperatorResponse(
            id=m.id,
            user_id=m.user_id,
            email=m.user.email if m.user else "",
            full_name=m.user.full_name if m.user else None,
            role=m.role.value,
            extra_data=m.extra_data,  # FIX: Return extra_data from DB
            created_at=m.created_at,
        )
        for m in memberships
        if m.user
    ]
    
    return OperatorListResponse(operators=operators, total=total)


@router.patch(
    "/operators/{membership_id}",
    response_model=OperatorUpdateResponse,
    summary="Update operator",
    description="Update operator role and extra_data. Admin/Owner only.",
)
async def update_operator(
    membership_id: int,
    data: OperatorRoleUpdate,
    user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> OperatorUpdateResponse:
    """
    Update an operator's role and extra_data.
    
    - **membership_id**: ID of the membership to update
    - **role**: New role (admin, member, viewer)
    - **extra_data**: New extra_data JSONB
    
    Requires owner/admin role.
    Cannot change owner's role.
    Organization isolation enforced.
    """
    # Get current user's membership
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org.id,
        )
    )
    user_membership = result.scalar_one_or_none()
    
    if not user_membership or not check_can_manage_operators(user, user_membership):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Forbidden",
                "status": 403,
                "detail": "You do not have permission to manage operators",
            },
        )
    
    # Get target membership with tenant isolation
    result = await db.execute(
        select(Membership)
        .where(
            Membership.id == membership_id,
            Membership.organization_id == org.id,  # Tenant isolation
        )
        .options(selectinload(Membership.user))
    )
    target_membership = result.scalar_one_or_none()
    
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Operator not found",
                "status": 404,
                "detail": "Operator not found in this organization",
            },
        )
    
    # Cannot change owner role
    if target_membership.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Cannot change owner",
                "status": 400,
                "detail": "Cannot change the role of the organization owner",
            },
        )
    
    # Validate new role
    if data.role not in MUTABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Invalid role",
                "status": 400,
                "detail": f"Cannot set role to '{data.role}'. Allowed: {MUTABLE_ROLES}",
            },
        )
    
    old_role = target_membership.role.value
    target_membership.role = UserRole(data.role)
    if data.extra_data is not None:
        target_membership.extra_data = data.extra_data  # FASE 2.1 FIX 4
    
    logger.info(
        f"Updated operator: membership_id={membership_id}, "
        f"role={old_role}->{data.role}, extra_data={data.extra_data}, org_id={org.id}"
    )
    
    await db.commit()
    await db.refresh(target_membership)
    
    return OperatorUpdateResponse(
        success=True,
        operator=OperatorResponse(
            id=target_membership.id,
            user_id=target_membership.user_id,
            email=target_membership.user.email if target_membership.user else "",
            full_name=target_membership.user.full_name if target_membership.user else None,
            role=data.role,
            extra_data=data.extra_data,
            created_at=target_membership.created_at,
        ),
        message=f"Role updated from {old_role} to {data.role}",
    )


@router.delete(
    "/operators/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove operator",
    description="Remove an operator from the organization.",
)
async def remove_operator(
    membership_id: int,
    user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove an operator from the organization.
    
    Requires owner/admin role.
    Cannot remove owner.
    Cannot remove self.
    Organization isolation enforced.
    """
    # Get current user's membership
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org.id,
        )
    )
    user_membership = result.scalar_one_or_none()
    
    if not user_membership or not check_can_manage_operators(user, user_membership):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Forbidden",
                "status": 403,
                "detail": "You do not have permission to manage operators",
            },
        )
    
    # Get target membership with tenant isolation
    result = await db.execute(
        select(Membership).where(
            Membership.id == membership_id,
            Membership.organization_id == org.id,  # Tenant isolation
        )
    )
    target_membership = result.scalar_one_or_none()
    
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Operator not found",
                "status": 404,
                "detail": "Operator not found in this organization",
            },
        )
    
    # Cannot remove owner
    if target_membership.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Cannot remove owner",
                "status": 400,
                "detail": "Cannot remove the organization owner",
            },
        )
    
    # Cannot remove self
    if target_membership.user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/command",
                "title": "Cannot remove self",
                "status": 400,
                "detail": "Cannot remove yourself from the organization",
            },
        )
    
    await db.delete(target_membership)
    
    logger.info(
        f"Removed operator: membership_id={membership_id}, org_id={org.id}"
    )
    
    await db.commit()