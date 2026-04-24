"""Organization endpoints - CRUD operations."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Membership, Organization, User, UserRole
from app.api.v1.deps import get_current_user, get_current_user_with_org, get_current_owner


router = APIRouter(prefix="/orgs", tags=["Organizations"])


# --- Schemas ---

class OrganizationCreate(BaseModel):
    """Schema for creating an organization."""
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    legal_name: Optional[str] = Field(None, max_length=255, description="Legal name")
    industry: Optional[str] = Field(None, max_length=100, description="Industry sector")
    segment: Optional[str] = Field(None, max_length=100, description="Segment (generator, gestor)")


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization (idempotent - nulls not overwritten)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    segment: Optional[str] = Field(None, max_length=100)


class OrganizationResponse(BaseModel):
    """Schema for organization response."""
    id: int
    name: str
    legal_name: Optional[str]
    industry: Optional[str]
    segment: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationDetailResponse(BaseModel):
    """Schema for detailed organization response."""
    id: int
    name: str
    legal_name: Optional[str]
    industry: Optional[str]
    segment: Optional[str]
    is_active: bool
    stripe_customer_id: Optional[str]
    created_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class OrganizationListResponse(BaseModel):
    """Schema for listing organizations."""
    organizations: List[OrganizationResponse]
    total: int


# --- Endpoints ---

@router.get(
    "",
    response_model=OrganizationListResponse,
    summary="List user organizations",
    description="List all organizations the current user is a member of.",
)
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationListResponse:
    """
    List all organizations the user belongs to.
    
    Returns organizations filtered by user's memberships.
    """
    # Get all memberships for the user
    result = await db.execute(
        select(Membership)
        .where(Membership.user_id == current_user.id)
    )
    memberships = result.scalars().all()
    
    org_ids = [m.organization_id for m in memberships]
    
    if not org_ids:
        return OrganizationListResponse(organizations=[], total=0)
    
    # Get organizations
    result = await db.execute(
        select(Organization)
        .where(Organization.id.in_(org_ids))
        .order_by(Organization.created_at.desc())
    )
    organizations = result.scalars().all()
    
    return OrganizationListResponse(
        organizations=[OrganizationResponse.model_validate(o) for o in organizations],
        total=len(organizations),
    )


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Create a new organization. User becomes owner.",
)
async def create_organization(
    request: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationResponse:
    """
    Create a new organization.
    
    User becomes owner of the new organization.
    """
    # Create organization
    org = Organization(
        name=request.name,
        legal_name=request.legal_name,
        industry=request.industry,
        segment=request.segment,
        is_active=True,
    )
    db.add(org)
    await db.flush()  # Get org.id
    
    # Create membership with owner role
    membership = Membership(
        user_id=current_user.id,
        organization_id=org.id,
        role=UserRole.OWNER,
    )
    db.add(membership)
    
    await db.commit()
    await db.refresh(org)
    
    return OrganizationResponse.model_validate(org)


@router.get(
    "/{org_id}",
    response_model=OrganizationDetailResponse,
    summary="Get organization details",
    description="Get details of a specific organization.",
)
async def get_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> OrganizationDetailResponse:
    """
    Get organization by ID.
    
    User must be a member of the organization.
    """
    user, org_id_from_token = user_org
    
    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Organization not found",
                "status": 404,
                "detail": "Organization does not exist",
            },
        )
    
    # Verify user is member (user is already verified via get_current_user_with_org)
    # The user is member of org_id_from_token, but might not be member of org_id
    # We need to verify membership for the specific org_id
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org_id,
        )
    )
    membership = result.scalar_one_or_none()
    
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Not a member",
                "status": 403,
                "detail": "User is not a member of this organization",
            },
        )
    
    # Get member count
    result = await db.execute(
        select(Membership).where(Membership.organization_id == org_id)
    )
    member_count = len(result.scalars().all())
    
    return OrganizationDetailResponse(
        id=org.id,
        name=org.name,
        legal_name=org.legal_name,
        industry=org.industry,
        segment=org.segment,
        is_active=org.is_active,
        stripe_customer_id=org.stripe_customer_id,
        created_at=org.created_at,
        member_count=member_count,
    )


@router.patch(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Update organization",
    description="Update organization details. Only owner can update.",
)
async def update_organization(
    org_id: int,
    request: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_context: tuple = Depends(get_current_owner),
) -> OrganizationResponse:
    """
    Update organization.
    
    Only owner can update. Idempotent - null fields are not overwritten.
    """
    user, org_id_from_token, role = org_context
    
    # Verify org_id matches
    if org_id_from_token != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Access denied",
                "status": 403,
                "detail": "Cannot update organization you don't own",
            },
        )
    
    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Organization not found",
                "status": 404,
                "detail": "Organization does not exist",
            },
        )
    
    # Update only non-null fields (idempotent)
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(org, field, value)
    
    await db.commit()
    await db.refresh(org)
    
    return OrganizationResponse.model_validate(org)