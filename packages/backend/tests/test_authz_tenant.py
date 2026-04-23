"""Tests for authorization and tenant isolation (Phase 3B)."""
import pytest
from jose import jwt

from app.core.tokens import create_access_token, decode_token, create_org_token
from app.core.config import settings
from app.api.middleware.tenant import (
    TenantContext,
    TenantMiddleware,
    get_permissions_for_role,
    ROLE_PERMISSIONS,
    check_cross_tenant_access,
    get_tenant_context,
)
from app.models import UserRole


# =============================================================================
# Token Payload Tests
# =============================================================================

class TestTokenPayload:
    """Tests for JWT token payload claims."""

    def test_create_token_with_minimal_claims(self):
        """Test creating token with only user_id."""
        token = create_access_token(user_id=123)
        payload = decode_token(token)
        
        assert payload is not None
        assert payload.sub == "123"
        assert payload.org_id is None
        assert payload.role is None
        assert payload.permissions == []

    def test_create_token_with_org_id(self):
        """Test creating token with org_id claim."""
        token = create_access_token(user_id=1, org_id=42)
        payload = decode_token(token)
        
        assert payload.org_id == 42

    def test_create_token_with_role(self):
        """Test creating token with role claim."""
        token = create_access_token(user_id=1, role=UserRole.ADMIN.value)
        payload = decode_token(token)
        
        assert payload.role == "admin"

    def test_create_token_with_permissions(self):
        """Test creating token with permissions list."""
        perms = ["resources:read", "resources:write"]
        token = create_access_token(user_id=1, permissions=perms)
        payload = decode_token(token)
        
        assert payload.permissions == perms

    def test_create_token_with_all_claims(self):
        """Test creating token with all claims (org_id, role, permissions)."""
        token = create_org_token(
            user_id=1,
            org_id=10,
            role=UserRole.OWNER.value,
            permissions=ROLE_PERMISSIONS[UserRole.OWNER.value],
        )
        payload = decode_token(token)
        
        assert payload.sub == "1"
        assert payload.org_id == 10
        assert payload.role == "owner"
        assert len(payload.permissions) > 0

    def test_invalid_token_returns_none(self):
        """Test decoding invalid token returns None."""
        result = decode_token("invalid.token.here")
        assert result is None

    def test_token_without_signature_returns_none(self):
        """Test decoding token with wrong signature returns None."""
        bad_token = jwt.encode(
            {"sub": "123", "org_id": 1},
            "wrong-secret-key",
            algorithm="HS256"
        )
        result = decode_token(bad_token)
        assert result is None


# =============================================================================
# Role Permissions Tests
# =============================================================================

class TestRolePermissions:
    """Tests for role-based permission mapping."""

    def test_owner_has_all_permissions(self):
        """Test owner role has all permissions."""
        perms = get_permissions_for_role(UserRole.OWNER.value)
        
        assert "tenant:read" in perms
        assert "tenant:write" in perms
        assert "tenant:delete" in perms
        assert "resources:read" in perms
        assert "resources:write" in perms
        assert "resources:delete" in perms

    def test_admin_permissions(self):
        """Test admin role has appropriate permissions."""
        perms = get_permissions_for_role(UserRole.ADMIN.value)
        
        assert "tenant:read" in perms
        assert "resources:read" in perms
        assert "resources:write" in perms
        # Admin should NOT have tenant:delete
        assert "tenant:delete" not in perms

    def test_member_permissions(self):
        """Test member role has limited permissions."""
        perms = get_permissions_for_role(UserRole.MEMBER.value)
        
        assert "tenant:read" in perms
        assert "resources:read" in perms
        assert "resources:write" in perms
        # Member should NOT have delete or admin permissions
        assert "resources:delete" not in perms
        assert "tenant:admin" not in perms

    def test_viewer_permissions(self):
        """Test viewer role has read-only permissions."""
        perms = get_permissions_for_role(UserRole.VIEWER.value)
        
        assert "tenant:read" in perms
        assert "resources:read" in perms
        # Viewer should NOT have write permissions
        assert "resources:write" not in perms

    def test_unknown_role_returns_empty_permissions(self):
        """Test unknown role returns empty list."""
        perms = get_permissions_for_role("unknown_role")
        assert perms == []


# =============================================================================
# TenantContext Tests
# =============================================================================

class TestTenantContext:
    """Tests for TenantContext class."""

    def test_tenant_context_initialization(self):
        """Test TenantContext initialization with all params."""
        ctx = TenantContext(
            user_id=1,
            org_id=10,
            role="admin",
            permissions=["resources:read"],
        )
        
        assert ctx.user_id == 1
        assert ctx.org_id == 10
        assert ctx.role == "admin"
        assert ctx.permissions == ["resources:read"]

    def test_tenant_context_default_permissions(self):
        """Test TenantContext defaults permissions to empty list."""
        ctx = TenantContext(user_id=1, org_id=10)
        assert ctx.permissions == []

    def test_has_permission_returns_true(self):
        """Test has_permission returns True for valid permission."""
        ctx = TenantContext(user_id=1, permissions=["resources:read"])
        assert ctx.has_permission("resources:read") is True

    def test_has_permission_returns_false(self):
        """Test has_permission returns False for missing permission."""
        ctx = TenantContext(user_id=1, permissions=["resources:read"])
        assert ctx.has_permission("resources:delete") is False

    def test_is_owner_returns_true_for_owner(self):
        """Test is_owner returns True when role is owner."""
        ctx = TenantContext(user_id=1, role="owner")
        assert ctx.is_owner() is True

    def test_is_owner_returns_false_for_admin(self):
        """Test is_owner returns False for admin role."""
        ctx = TenantContext(user_id=1, role="admin")
        assert ctx.is_owner() is False

    def test_is_admin_returns_true_for_admin(self):
        """Test is_admin returns True for admin role."""
        ctx = TenantContext(user_id=1, role="admin")
        assert ctx.is_admin() is True

    def test_is_admin_returns_true_for_owner(self):
        """Test is_admin returns True for owner role (owner is admin)."""
        ctx = TenantContext(user_id=1, role="owner")
        assert ctx.is_admin() is True

    def test_is_admin_returns_false_for_member(self):
        """Test is_admin returns False for member role."""
        ctx = TenantContext(user_id=1, role="member")
        assert ctx.is_admin() is False

    def test_can_read_all_roles(self):
        """Test can_read returns True for all roles."""
        for role in ["owner", "admin", "member", "viewer"]:
            ctx = TenantContext(user_id=1, role=role)
            assert ctx.can_read() is True

    def test_can_write_excludes_viewer(self):
        """Test can_write returns False for viewer."""
        ctx = TenantContext(user_id=1, role="viewer")
        assert ctx.can_write() is False

    def test_can_write_includes_member(self):
        """Test can_write returns True for member."""
        ctx = TenantContext(user_id=1, role="member")
        assert ctx.can_write() is True

    def test_can_write_includes_admin_and_owner(self):
        """Test can_write returns True for admin and owner."""
        for role in ["admin", "owner"]:
            ctx = TenantContext(user_id=1, role=role)
            assert ctx.can_write() is True


# =============================================================================
# Middleware Public Paths Tests
# =============================================================================

class TestTenantMiddlewarePaths:
    """Tests for TenantMiddleware public path detection."""

    def test_public_path_health_endpoints(self):
        """Test health endpoints are public."""
        middleware = TenantMiddleware(app=None)
        
        assert middleware._is_public_path("/api/health") is True
        assert middleware._is_public_path("/api/health/db") is True
        assert middleware._is_public_path("/api/health/redis") is True
        assert middleware._is_public_path("/api/health/tenant") is True
        assert middleware._is_public_path("/api/health/deep") is True

    def test_public_path_auth_endpoints(self):
        """Test auth endpoints are public."""
        middleware = TenantMiddleware(app=None)
        
        assert middleware._is_public_path("/api/auth/login") is True
        assert middleware._is_public_path("/api/auth/register") is True

    def test_public_path_docs_endpoints(self):
        """Test docs endpoints are public."""
        middleware = TenantMiddleware(app=None)
        
        assert middleware._is_public_path("/docs") is True
        assert middleware._is_public_path("/openapi.json") is True
        assert middleware._is_public_path("/redoc") is True

    def test_public_path_root(self):
        """Test root path is public."""
        middleware = TenantMiddleware(app=None)
        assert middleware._is_public_path("/") is True

    def test_protected_path_employers(self):
        """Test employers endpoint requires auth (not in public paths)."""
        middleware = TenantMiddleware(app=None)
        
        assert middleware._is_public_path("/api/employers") is False
        assert middleware._is_public_path("/api/employers/123") is False

    def test_protected_path_transporters(self):
        """Test transporters endpoint requires auth."""
        middleware = TenantMiddleware(app=None)
        
        assert middleware._is_public_path("/api/transporters") is False

    def test_protected_path_residues(self):
        """Test residues endpoint requires auth."""
        middleware = TenantMiddleware(app=None)
        
        assert middleware._is_public_path("/api/residues") is False


# =============================================================================
# Cross-Tenant Access Tests
# =============================================================================

class TestCrossTenantAccess:
    """Tests for cross-tenant access prevention."""

    def test_check_cross_tenant_same_org_allowed(self):
        """Test access to same organization is allowed."""
        from unittest.mock import MagicMock
        
        # Create mock request with tenant context
        mock_request = MagicMock()
        mock_request.state.tenant_ctx = TenantContext(
            user_id=1,
            org_id=10,
            role="member",
        )
        
        # Should not raise
        check_cross_tenant_access(mock_request, target_org_id=10)

    def test_check_cross_tenant_different_org_forbidden(self):
        """Test access to different organization raises 403."""
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        
        mock_request = MagicMock()
        mock_request.state.tenant_ctx = TenantContext(
            user_id=1,
            org_id=10,
            role="owner",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            check_cross_tenant_access(mock_request, target_org_id=999)
        
        assert exc_info.value.status_code == 403
        assert "Cross-tenant access denied" in str(exc_info.value.detail)

    def test_check_cross_tenant_no_context_forbidden(self):
        """Test request without tenant context raises 403."""
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        
        mock_request = MagicMock()
        mock_request.state.tenant_ctx = None
        
        with pytest.raises(HTTPException) as exc_info:
            check_cross_tenant_access(mock_request, target_org_id=10)
        
        assert exc_info.value.status_code == 403

    def test_check_cross_tenant_owner_can_access(self):
        """Test owner can access their organization."""
        from unittest.mock import MagicMock
        
        mock_request = MagicMock()
        mock_request.state.tenant_ctx = TenantContext(
            user_id=1,
            org_id=5,
            role="owner",
        )
        
        # Should not raise
        check_cross_tenant_access(mock_request, target_org_id=5)


# =============================================================================
# Integration Token Tests
# =============================================================================

class TestTokenIntegration:
    """Integration tests for token with full claims chain."""

    def test_full_claims_chain_encode_decode(self):
        """Test complete token claims can be encoded and decoded."""
        original_perms = ROLE_PERMISSIONS[UserRole.ADMIN.value]
        
        token = create_org_token(
            user_id=42,
            org_id=15,
            role=UserRole.ADMIN.value,
            permissions=original_perms,
        )
        
        payload = decode_token(token)
        
        assert payload.sub == "42"
        assert payload.org_id == 15
        assert payload.role == "admin"
        assert payload.permissions == original_perms

    def test_token_preserves_all_permissions(self):
        """Test token preserves all permissions without loss."""
        all_perms = ROLE_PERMISSIONS[UserRole.OWNER.value]
        
        token = create_access_token(
            user_id=1,
            org_id=1,
            role=UserRole.OWNER.value,
            permissions=all_perms,
        )
        
        payload = decode_token(token)
        
        assert len(payload.permissions) == len(all_perms)
        for perm in all_perms:
            assert perm in payload.permissions

    def test_expired_token_claims_still_present(self):
        """Test that decoded token still has all claims regardless of expiry."""
        # Create token manually with past expiry for testing
        from datetime import datetime, timedelta, timezone
        
        payload_dict = {
            "sub": "123",
            "org_id": 10,
            "role": "member",
            "permissions": ["resources:read"],
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            "iat": datetime.now(timezone.utc) - timedelta(hours=25),
        }
        
        expired_token = jwt.encode(
            payload_dict,
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        # Note: decode_token will return None for expired tokens due to jose validation
        # This is the expected behavior - expired tokens should not decode
        result = decode_token(expired_token)
        assert result is None