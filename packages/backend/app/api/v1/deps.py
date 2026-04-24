"""API v1 dependencies - Shared authentication and authorization."""
from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tokens import decode_token
from app.models import User, Membership, UserRole, Organization


# HTTP Bearer scheme for JWT authentication
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Raises 401 if no token or invalid token.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "No token",
                "status": 401,
                "detail": "Authentication required",
            },
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Invalid token",
                "status": 401,
                "detail": "Token is invalid or expired",
            },
        )
    
    try:
        user_id = int(payload.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Invalid token payload",
                "status": 401,
                "detail": "Token contains invalid user ID",
            },
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "User not found",
                "status": 401,
                "detail": "User associated with token no longer exists",
            },
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "User disabled",
                "status": 403,
                "detail": "User account is disabled",
            },
        )
    
    return user


async def get_current_user_with_org(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Tuple[User, int]:
    """
    Get current user with organization context from JWT.
    
    Returns (User, org_id) tuple.
    Raises 401 if no auth, 403 if no org context.
    """
    user = await get_current_user(credentials, db)
    
    # Extract org_id from JWT payload
    payload = decode_token(credentials.credentials)
    if payload is None or payload.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "No organization context",
                "status": 403,
                "detail": "Token does not contain valid organization context",
            },
        )
    
    org_id = payload.org_id
    
    # Verify user is member of the organization
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
    
    return user, org_id


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Tuple[User, int, str]:
    """
    Get current admin (owner or admin role).
    
    Returns (User, org_id, role) tuple.
    Raises 403 if not admin/owner.
    """
    user, org_id = await get_current_user_with_org(credentials, db)
    
    # Extract role from token
    payload = decode_token(credentials.credentials)
    role = payload.role if payload and payload.role else None
    
    # Verify admin role
    if role not in (UserRole.OWNER.value, UserRole.ADMIN.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Insufficient permissions",
                "status": 403,
                "detail": "Admin or owner role required",
            },
        )
    
    return user, org_id, role


async def get_current_owner(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Tuple[User, int, str]:
    """
    Get current owner (owner role only).
    
    Returns (User, org_id, role) tuple.
    Raises 403 if not owner.
    """
    user, org_id = await get_current_user_with_org(credentials, db)
    
    # Extract role from token
    payload = decode_token(credentials.credentials)
    role = payload.role if payload and payload.role else None
    
    # Verify owner role
    if role != UserRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Insufficient permissions",
                "status": 403,
                "detail": "Owner role required",
            },
        )
    
    return user, org_id, role