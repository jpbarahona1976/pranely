"""
PRANELY Audit Middleware - Request/Response Audit Logging

Middleware for automatic audit trail recording of API requests.
Integrates with TenantMiddleware for multi-tenant context.
"""
from __future__ import annotations

import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.audit import (
    AuditAction,
    AuditSeverity,
    CorrelationContext,
    PIIRedactor,
    record_audit_event,
)
from app.core.logging import get_logger

logger = get_logger("middleware.audit")


# Paths that should NOT be audited
PUBLIC_PATHS = {
    "/",
    "/api/health",
    "/api/health/db",
    "/api/health/redis",
    "/api/health/tenant",
    "/api/health/deep",
    "/docs",
    "/openapi.json",
    "/redoc",
}


# Sensitive paths that need extra handling
SENSITIVE_PATHS = {
    "/api/auth/login": {"action": AuditAction.LOGIN},
    "/api/auth/logout": {"action": AuditAction.LOGOUT},
    "/api/auth/register": {"action": AuditAction.CREATE},
}


def extract_path_pattern(path: str) -> str:
    """
    Extract resource type from request path.
    
    Examples:
        /api/employers/123 → employer
        /api/users/me → user
        /api/employers → employer
        /api/v1/waste/123 → waste  (FIX: skip version prefix)
        /api/v1/waste → waste
    """
    parts = path.strip("/").split("/")
    
    # Skip 'api' prefix
    if parts and parts[0] == "api":
        parts = parts[1:]
    
    # Skip API version prefix (e.g., 'v1', 'v2')
    if parts and parts[0] and parts[0][0] == 'v' and parts[0][1:].isdigit():
        parts = parts[1:]
    
    if not parts:
        return "unknown"
    
    resource = parts[0]
    
    # Remove plural for consistency
    if resource.endswith("s") and not resource.endswith("ss"):
        resource = resource[:-1]
    
    return resource


def determine_action(method: str, path: str) -> AuditAction:
    """
    Determine audit action from HTTP method and path.
    """
    # Check for exact matches first
    for sensitive_path, config in SENSITIVE_PATHS.items():
        if path.startswith(sensitive_path):
            return config["action"]
    
    # Map HTTP methods to actions
    method_action_map = {
        "POST": AuditAction.CREATE,
        "PUT": AuditAction.UPDATE,
        "PATCH": AuditAction.UPDATE,
        "GET": AuditAction.READ,
        "DELETE": AuditAction.DELETE,
    }
    
    return method_action_map.get(method.upper(), AuditAction.READ)


def determine_severity(action: AuditAction, status_code: int) -> AuditSeverity:
    """
    Determine severity based on action and response status.
    """
    # Error responses always get error severity
    if status_code >= 500:
        return AuditSeverity.ERROR
    
    if status_code >= 400:
        return AuditSeverity.WARN
    
    # Security-sensitive actions always get AUDIT severity
    audit_actions = {
        AuditAction.LOGIN,
        AuditAction.LOGOUT,
        AuditAction.CREATE,  # User creation
        AuditAction.DELETE,  # Deletions
        AuditAction.CONSENT,
        AuditAction.CONSENT_WITHDRAW,
        AuditAction.EXPORT,
    }
    
    if action in audit_actions:
        return AuditSeverity.AUDIT
    
    return AuditSeverity.INFO


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic audit trail recording.
    
    Features:
    - Automatic audit event recording for all API requests
    - Correlation ID injection
    - PII redaction from request/response data
    - Configurable path exclusions
    - Tenant context integration
    
    Usage:
        app.add_middleware(AuditMiddleware)
    
    Note: This middleware should be added AFTER TenantMiddleware
    to have access to org_id and user_id from JWT claims.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[set] = None,
        include_request_body: bool = True,
        include_response_body: bool = False,
    ):
        """
        Initialize audit middleware.
        
        Args:
            app: ASGI application
            exclude_paths: Set of paths to exclude from audit
            include_request_body: Whether to include request body in audit
            include_response_body: Whether to include response body (not recommended)
        """
        super().__init__(app)
        self.exclude_paths = PUBLIC_PATHS.copy()
        if exclude_paths:
            self.exclude_paths.update(exclude_paths)
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
    
    def _should_audit(self, path: str) -> bool:
        """Check if path should be audited."""
        # Exact match
        if path in self.exclude_paths:
            return False
        
        # Prefix match for path patterns
        for excluded in self.exclude_paths:
            if path.startswith(excluded):
                return False
        
        # Only audit /api/* paths
        if not path.startswith("/api"):
            return False
        
        return True
    
    def _extract_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check X-Forwarded-For first (for load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _get_request_data(self, request: Request) -> Optional[dict]:
        """Extract and parse request body if configured."""
        if not self.include_request_body:
            return None
        
        try:
            # Only attempt to read body for methods that typically have it
            if request.method in ("POST", "PUT", "PATCH"):
                body = await request.body()
                if body:
                    import json
                    try:
                        data = json.loads(body)
                        # Redact PII
                        return PIIRedactor.redact_dict(data)
                    except json.JSONDecodeError:
                        return {"raw_body": "[non-json-body]"}
        except Exception:
            pass
        
        return None
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and record audit event."""
        path = request.url.path
        
        # Skip non-auditable paths
        if not self._should_audit(path):
            return await call_next(request)
        
        # Generate or use existing correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Set correlation context
        CorrelationContext.set(
            correlation_id=correlation_id,
            org_id=getattr(request.state, "org_id", None),
            user_id=getattr(request.state, "user_id", None),
            request_id=request.headers.get("X-Request-ID"),
        )
        
        # Determine action and resource
        action = determine_action(request.method, path)
        resource_type = extract_path_pattern(path)
        
        # Extract resource ID from path if present
        # FIX: Handle versioned paths like /api/v1/waste/123
        resource_id = None
        path_parts = [p for p in path.strip("/").split("/") if p]
        
        # Filter out path segments that are not IDs
        # Valid ID patterns: numeric (123) or UUID (with dashes)
        potential_ids = []
        for part in path_parts:
            if part.isdigit():
                potential_ids.append(part)
            elif len(part) == 36 and part.count("-") == 4:
                potential_ids.append(part)  # UUID
        
        # Use the last valid ID found (usually the resource ID)
        # Skip 'stats', 'archive' etc. which are action names, not IDs
        for potential_id in reversed(potential_ids):
            # Don't use action names as IDs
            if potential_id not in ("stats", "archive", "upload", "approve", "review"):
                resource_id = potential_id
                break
        
        # Record start time
        import time
        start_time = time.time()
        
        # Get request data
        request_data = await self._get_request_data(request)
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Determine severity
            severity = determine_severity(action, status_code)
            
            # Record audit event (async, non-blocking)
            try:
                await record_audit_event(
                    correlation_id=correlation_id,
                    user_id=CorrelationContext.get_user_id(),
                    organization_id=CorrelationContext.get_org_id(),
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    severity=severity,
                    ip_address=self._extract_client_ip(request),
                    user_agent=request.headers.get("User-Agent"),
                    request_path=path,
                    request_method=request.method,
                    request_data=request_data,
                    response_status=status_code,
                    metadata={
                        "duration_ms": round(duration_ms, 2),
                        "query_params": dict(request.query_params),
                    },
                )
            except Exception as e:
                # Don't fail the request if audit fails
                logger.error(f"Failed to record audit event: {e}")
        
        return response


# =============================================================================
# Audit Logging Integration for Specific Operations
# =============================================================================


async def log_audit_login(
    user_id: int,
    org_id: int,
    success: bool,
    ip_address: str,
    user_agent: Optional[str] = None,
):
    """Log authentication events."""
    await record_audit_event(
        user_id=user_id,
        organization_id=org_id,
        action=AuditAction.LOGIN,
        resource_type="session",
        severity=AuditSeverity.AUDIT,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"success": success},
    )


async def log_audit_consent(
    user_id: int,
    org_id: int,
    consent_type: str,
    granted: bool,
    purpose: str,
):
    """Log consent events for PII handling."""
    await record_audit_event(
        user_id=user_id,
        organization_id=org_id,
        action=AuditAction.CONSENT if granted else AuditAction.CONSENT_WITHDRAW,
        resource_type="consent",
        severity=AuditSeverity.AUDIT,
        metadata={
            "consent_type": consent_type,
            "granted": granted,
            "purpose": purpose,
        },
    )


async def log_audit_data_export(
    user_id: int,
    org_id: int,
    resource_type: str,
    record_count: int,
    export_format: str,
):
    """Log data export events (NOM-151 portability)."""
    await record_audit_event(
        user_id=user_id,
        organization_id=org_id,
        action=AuditAction.EXPORT,
        resource_type=resource_type,
        severity=AuditSeverity.AUDIT,
        metadata={
            "record_count": record_count,
            "export_format": export_format,
        },
    )
