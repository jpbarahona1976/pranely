"""Tenant isolation middleware for multi-tenant authorization."""
from typing import Optional

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.tokens import decode_token
from app.models import UserRole


class TenantContext:
    """Tenant context holder with org_id, role, and permissions."""
    
    def __init__(
        self,
        user_id: int,
        org_id: Optional[int] = None,
        role: Optional[str] = None,
        permissions: Optional[list[str]] = None,
    ):
        self.user_id = user_id
        self.org_id = org_id
        self.role = role
        self.permissions = permissions or []
    
    def has_permission(self, permission: str) -> bool:
        """Check if context has a specific permission."""
        return permission in self.permissions
    
    def is_owner(self) -> bool:
        """Check if user is owner of the tenant."""
        return self.role == UserRole.OWNER.value
    
    def is_admin(self) -> bool:
        """Check if user has admin or owner role."""
        return self.role in (UserRole.OWNER.value, UserRole.ADMIN.value)
    
    def can_read(self) -> bool:
        """Check if user can read resources."""
        return self.role in (
            UserRole.OWNER.value,
            UserRole.ADMIN.value,
            UserRole.MEMBER.value,
            UserRole.VIEWER.value,
        )
    
    def can_write(self) -> bool:
        """Check if user can write/modify resources."""
        return self.role in (
            UserRole.OWNER.value,
            UserRole.ADMIN.value,
            UserRole.MEMBER.value,
        )


# Role-based permission mapping
ROLE_PERMISSIONS = {
    UserRole.OWNER.value: [
        "tenant:read",
        "tenant:write",
        "tenant:delete",
        "tenant:admin",
        "resources:read",
        "resources:write",
        "resources:delete",
        "users:read",
        "users:write",
        "users:delete",
    ],
    UserRole.ADMIN.value: [
        "tenant:read",
        "resources:read",
        "resources:write",
        "resources:delete",
        "users:read",
        "users:write",
    ],
    UserRole.MEMBER.value: [
        "tenant:read",
        "resources:read",
        "resources:write",
    ],
    UserRole.VIEWER.value: [
        "tenant:read",
        "resources:read",
    ],
}


def get_permissions_for_role(role: str) -> list[str]:
    """Get permissions list for a given role."""
    return ROLE_PERMISSIONS.get(role, [])


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts org_id and role from JWT token.
    
    Injects tenant context into request.state for downstream use.
    Rejects cross-tenant access attempts with 403.
    """
    
    # Paths that don't require tenant context
    PUBLIC_PATHS = [
        "/",
        "/api/auth/login",
        "/api/auth/register",
        "/api/health",
        "/api/health/db",
        "/api/health/redis",
        "/api/health/tenant",
        "/api/health/deep",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and inject tenant context."""
        # Skip tenant context for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Initialize tenant context as None
        request.state.tenant_ctx = None
        
        # Try to extract tenant context from JWT
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            tenant_ctx = self._extract_tenant_context(token)
            if tenant_ctx:
                request.state.tenant_ctx = tenant_ctx
        
        return await call_next(request)
    
    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required)."""
        for public_path in self.PUBLIC_PATHS:
            if path == public_path or path.startswith(f"{public_path}/"):
                return True
        return False
    
    def _extract_tenant_context(self, token: str) -> Optional[TenantContext]:
        """
        Extract tenant context from JWT token.
        
        Returns TenantContext with org_id, role, and permissions.
        Returns None if token is invalid (middleware doesn't reject,
        downstream auth dependencies will handle that).
        """
        payload = decode_token(token)
        if payload is None:
            return None
        
        try:
            user_id = int(payload.sub)
        except ValueError:
            return None
        
        # Extract role from token or default to viewer
        role = payload.role if hasattr(payload, "role") and payload.role else None
        
        # Get org_id
        org_id = payload.org_id
        
        # Get permissions based on role
        permissions = get_permissions_for_role(role) if role else []
        
        return TenantContext(
            user_id=user_id,
            org_id=org_id,
            role=role,
            permissions=permissions,
        )


def get_tenant_context(request: Request) -> Optional[TenantContext]:
    """Get tenant context from request state."""
    return getattr(request.state, "tenant_ctx", None)


def require_org_id(request: Request) -> int:
    """
    Require org_id in tenant context.
    
    Raises 403 if no valid tenant context or org_id is missing.
    """
    ctx = get_tenant_context(request)
    if ctx is None or ctx.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "No tenant context",
                "status": 403,
                "detail": "Authentication required with valid organization context",
            },
        )
    return ctx.org_id


def check_cross_tenant_access(request: Request, target_org_id: int) -> None:
    """
    Check if request has access to target organization.
    
    Raises 403 if tenant context doesn't match target_org_id.
    """
    ctx = get_tenant_context(request)
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Access denied",
                "status": 403,
                "detail": "Authentication required",
            },
        )
    
    if ctx.org_id != target_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Cross-tenant access denied",
                "status": 403,
                "detail": f"Access to organization {target_org_id} is not permitted",
            },
        )