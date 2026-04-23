"""
Extended dependencies for domain API endpoints.

WARNING: This module is DEPRECATED.
All functionality has been moved to app/api/deps.py as the single source of truth.
Please use get_current_active_organization from deps.py instead.

Deprecated functions:
- get_current_org: Uses first membership by created_at instead of JWT org_id
- get_optional_org: Same issue as get_current_org

The correct approach uses org_id from JWT token and validates user membership.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_active_organization
from app.core.database import get_db
from app.models import Membership, Organization, User, UserRole


# Re-export from deps.py for backward compatibility during migration
# These are the CORRECT dependencies that use org_id from JWT
async def get_current_org(
    request=None,
    db: AsyncSession = Depends(get_db),
    credentials=None,
) -> Organization:
    """
    DEPRECATED: Use get_current_active_organization from deps.py instead.
    
    This function is kept for backward compatibility but should not be used.
    It incorrectly selects the first membership by created_at.
    
    The correct approach uses org_id from JWT token (see get_current_active_organization).
    """
    # Import here to avoid circular imports at module level
    from fastapi import Request
    from fastapi.security import HTTPBearer
    
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "https://api.pranely.com/errors/internal",
                "title": "Deprecated function called incorrectly",
                "status": 500,
                "detail": "get_current_org is deprecated. Use get_current_active_organization from deps.py",
            },
        )
    
    # Actually delegate to the correct implementation
    user, org = await get_current_active_organization(request, db, credentials)
    return org


async def get_optional_org(
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[Organization]:
    """Get current organization if user is authenticated, otherwise None."""
    if user is None:
        return None
    
    try:
        # This now properly uses JWT org_id
        raise NotImplementedError(
            "get_optional_org is deprecated. Use get_current_active_organization from deps.py"
        )
    except NotImplementedError as e:
        # Fallback that will be removed after migration
        result = await db.execute(
            select(Membership)
            .where(Membership.user_id == user.id)
            .order_by(Membership.created_at)
            .limit(1)
        )
        membership = result.scalar_one_or_none()
        
        if membership is None:
            return None
        
        org_result = await db.execute(
            select(Organization).where(Organization.id == membership.organization_id)
        )
        return org_result.scalar_one_or_none()