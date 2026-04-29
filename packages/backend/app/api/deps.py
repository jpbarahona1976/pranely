"""Authentication dependencies (JWT verification, current user, RBAC)."""
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tokens import decode_token
from app.models import User, Membership, UserRole, Organization
from app.api.middleware.tenant import TenantContext, get_tenant_context, require_org_id


# Use auto_error=False so we can handle the 401 ourselves
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
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


# Alias for backwards compatibility with imports
get_current_active_user = get_current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_current_user_with_org(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
) -> tuple[User, Optional[int]]:
    """
    Get current user and organization ID from JWT token.
    
    Returns tuple of (User, org_id). org_id may be None if token doesn't contain it.
    Authentication is still required.
    """
    user = await get_current_user(credentials, db)
    
    # Try to get org_id from token payload
    org_id = None
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload:
            org_id = payload.org_id
    
    # Fallback to tenant middleware context if available
    if org_id is None and request is not None:
        ctx = get_tenant_context(request)
        if ctx:
            org_id = ctx.org_id
    
    return user, org_id


async def get_current_active_user_org(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> tuple[User, int]:
    """
    Get current authenticated user with validated organization context.
    
    This dependency ensures:
    1. User is authenticated
    2. User has valid org_id in token
    3. User is member of the organization
    
    Returns tuple of (User, org_id).
    Raises 403 if no valid org context.
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


async def get_current_active_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> tuple[User, int, str]:
    """
    Get current authenticated admin (owner or admin role).
    
    This dependency ensures:
    1. User is authenticated
    2. User has valid org_id in token
    3. User has admin or owner role in the organization
    
    Returns tuple of (User, org_id, role).
    Raises 403 if user is not admin/owner.
    """
    user, org_id = await get_current_active_user_org(request, db, credentials)
    
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


async def get_current_active_owner(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> tuple[User, int, str]:
    """
    Get current authenticated owner.
    
    This dependency ensures:
    1. User is authenticated
    2. User has valid org_id in token
    3. User has owner role in the organization
    
    Returns tuple of (User, org_id, role).
    Raises 403 if user is not owner.
    """
    user, org_id = await get_current_active_user_org(request, db, credentials)
    
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


class RequireOrgId:
    """
    Dependency class for requiring org_id in request.
    
    Use as: Depends(RequireOrgId())
    """
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db),
    ) -> tuple[User, int]:
        """Validate org context and return user + org_id."""
        return await get_current_active_user_org(request, db, credentials)


class RequireAdmin:
    """
    Dependency class for requiring admin/owner role.
    
    Use as: Depends(RequireAdmin())
    """
    
    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> tuple[User, int, str]:
        """Validate admin role and return user + org_id + role."""
        return await get_current_active_admin(request, db, credentials)


def require_permission(permission: str):
    """
    Create a dependency that requires a specific permission.
    
    Usage:
        @router.get("/resource", dependencies=[Depends(require_permission("resources:write"))])
    """
    async def check_permission(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> TenantContext:
        ctx = get_tenant_context(request)
        if ctx is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "type": "https://api.pranely.com/errors/auth",
                    "title": "Not authenticated",
                    "status": 401,
                    "detail": "Authentication required",
                },
            )
        
        if not ctx.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "type": "https://api.pranely.com/errors/authz",
                    "title": "Permission denied",
                    "status": 403,
                    "detail": f"Permission '{permission}' required",
                },
            )
        
        return ctx
    
    return check_permission


async def get_current_active_organization(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> tuple[User, Organization]:
    """
    Get current authenticated user with validated organization.
    
    This dependency is the SOLE SOURCE OF TRUTH for tenant context.
    It uses org_id from JWT token and validates user membership.
    
    Returns tuple of (User, Organization).
    Raises 403 if no valid org context or membership invalid.
    
    IMPORTANT: This replaces get_current_org from org_deps.py which was
    incorrectly selecting the first membership by created_at instead of
    using the org_id from the JWT token.
    """
    user = await get_current_user(credentials, db)
    
    # Extract org_id from JWT payload (CRITICAL: use token's org_id)
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Invalid token",
                "status": 403,
                "detail": "Token is invalid or malformed",
            },
        )
    
    org_id = payload.org_id
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "No organization context",
                "status": 403,
                "detail": "Token does not contain organization context",
            },
        )
    
    # CRITICAL: Verify user is member of the organization from token
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
    
    # Get and validate organization
    org_result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = org_result.scalar_one_or_none()
    
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
    
    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Organization inactive",
                "status": 403,
                "detail": "Organization is inactive",
            },
        )
    
    return user, org


async def get_user_role_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    Extract user role from JWT token.
    
    Returns:
        Role string from token claims, or 'member' as default fallback.
    """
    if credentials is None:
        return "member"
    
    payload = decode_token(credentials.credentials)
    if payload is None:
        return "member"
    
    return payload.role or "member"