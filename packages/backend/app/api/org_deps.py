"""Extended dependencies for domain API endpoints."""
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Membership, Organization, User, UserRole


async def get_current_org(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """
    Get the current user's primary organization.
    
    Returns the organization from the user's first membership.
    Raises 401 if no membership found.
    
    Multi-tenant: All domain endpoints require organization context.
    """
    result = await db.execute(
        select(Membership)
        .where(Membership.user_id == user.id)
        .order_by(Membership.created_at)
        .limit(1)
    )
    membership = result.scalar_one_or_none()
    
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "No organization",
                "status": 401,
                "detail": "User has no organization membership",
            },
        )
    
    # Get organization
    org_result = await db.execute(
        select(Organization).where(Organization.id == membership.organization_id)
    )
    org = org_result.scalar_one_or_none()
    
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Organization not found",
                "status": 404,
                "detail": "Organization associated with user not found",
            },
        )
    
    return org


async def get_optional_org(
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[Organization]:
    """Get current organization if user is authenticated, otherwise None."""
    if user is None:
        return None
    
    try:
        return await get_current_org(user, db)
    except HTTPException:
        return None