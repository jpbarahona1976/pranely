"""Tests for TenantMiddleware org_id propagation (FIX 2)."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import Request

from app.api.middleware.tenant import (
    TenantMiddleware,
    TenantContext,
    get_tenant_context,
    require_org_id,
    get_permissions_for_role,
)
from app.models import UserRole


class TestTenantContext:
    """Test TenantContext class."""

    def test_tenant_context_initialization(self):
        """TenantContext initializes with correct values."""
        ctx = TenantContext(
            user_id=1,
            org_id=100,
            role=UserRole.OWNER.value,
            permissions=["tenant:read", "tenant:write"],
        )

        assert ctx.user_id == 1
        assert ctx.org_id == 100
        assert ctx.role == "owner"
        assert ctx.permissions == ["tenant:read", "tenant:write"]

    def test_has_permission(self):
        """has_permission returns correct value."""
        ctx = TenantContext(
            user_id=1,
            org_id=100,
            role=UserRole.MEMBER.value,
            permissions=["tenant:read", "resources:read"],
        )

        assert ctx.has_permission("tenant:read") is True
        assert ctx.has_permission("tenant:write") is False

    def test_is_owner(self):
        """is_owner returns correct value."""
        owner_ctx = TenantContext(user_id=1, org_id=100, role=UserRole.OWNER.value)
        member_ctx = TenantContext(user_id=2, org_id=100, role=UserRole.MEMBER.value)

        assert owner_ctx.is_owner() is True
        assert member_ctx.is_owner() is False

    def test_is_admin(self):
        """is_admin returns correct value for admin and owner."""
        owner_ctx = TenantContext(user_id=1, org_id=100, role=UserRole.OWNER.value)
        admin_ctx = TenantContext(user_id=2, org_id=100, role=UserRole.ADMIN.value)
        member_ctx = TenantContext(user_id=3, org_id=100, role=UserRole.MEMBER.value)

        assert owner_ctx.is_admin() is True
        assert admin_ctx.is_admin() is True
        assert member_ctx.is_admin() is False

    def test_can_read(self):
        """can_read returns correct value for all read roles."""
        owner_ctx = TenantContext(user_id=1, org_id=100, role=UserRole.OWNER.value)
        viewer_ctx = TenantContext(user_id=2, org_id=100, role=UserRole.VIEWER.value)

        assert owner_ctx.can_read() is True
        assert viewer_ctx.can_read() is True

    def test_can_write(self):
        """can_write returns correct value for write roles."""
        owner_ctx = TenantContext(user_id=1, org_id=100, role=UserRole.OWNER.value)
        viewer_ctx = TenantContext(user_id=2, org_id=100, role=UserRole.VIEWER.value)

        assert owner_ctx.can_write() is True
        assert viewer_ctx.can_write() is False


class TestGetPermissionsForRole:
    """Test get_permissions_for_role function."""

    def test_owner_permissions(self):
        """Owner has all permissions."""
        perms = get_permissions_for_role(UserRole.OWNER.value)
        
        assert "tenant:read" in perms
        assert "tenant:write" in perms
        assert "tenant:delete" in perms
        assert "tenant:admin" in perms

    def test_viewer_permissions(self):
        """Viewer has only read permissions."""
        perms = get_permissions_for_role(UserRole.VIEWER.value)
        
        assert "tenant:read" in perms
        assert "tenant:write" not in perms
        assert len(perms) == 2

    def test_unknown_role_returns_empty(self):
        """Unknown role returns empty list."""
        perms = get_permissions_for_role("unknown_role")
        
        assert perms == []


class TestGetTenantContext:
    """Test get_tenant_context function."""

    def test_get_tenant_context_exists(self):
        """get_tenant_context returns tenant_ctx from request.state."""
        mock_request = Mock()
        mock_request.state.tenant_ctx = TenantContext(user_id=1, org_id=100)

        ctx = get_tenant_context(mock_request)

        assert ctx is not None
        assert ctx.user_id == 1
        assert ctx.org_id == 100

    def test_get_tenant_context_none(self):
        """get_tenant_context returns None when no tenant_ctx."""
        mock_request = Mock()
        mock_request.state.tenant_ctx = None

        ctx = get_tenant_context(mock_request)

        assert ctx is None


class TestRequireOrgId:
    """Test require_org_id function."""

    def test_require_org_id_with_valid_context(self):
        """require_org_id returns org_id when valid."""
        mock_request = Mock()
        mock_request.state.tenant_ctx = TenantContext(user_id=1, org_id=100)

        org_id = require_org_id(mock_request)

        assert org_id == 100

    def test_require_org_id_raises_when_no_context(self):
        """require_org_id raises HTTPException when no tenant context."""
        mock_request = Mock()
        mock_request.state.tenant_ctx = None

        with pytest.raises(Exception):  # HTTPException
            require_org_id(mock_request)

    def test_require_org_id_raises_when_no_org_id(self):
        """require_org_id raises HTTPException when org_id is None."""
        mock_request = Mock()
        mock_request.state.tenant_ctx = TenantContext(user_id=1, org_id=None)

        with pytest.raises(Exception):  # HTTPException
            require_org_id(mock_request)


class TestTenantMiddleware:
    """Test TenantMiddleware class."""

    @pytest.mark.asyncio
    async def test_public_paths_skip_tenant_context(self):
        """Public paths skip tenant context injection."""
        middleware = TenantMiddleware(app=Mock())
        
        mock_request = Mock()
        mock_request.url.path = "/api/health"
        mock_request.headers = {}
        
        mock_response = Mock()
        call_next = AsyncMock(return_value=mock_response)
        
        await middleware.dispatch(mock_request, call_next)
        
        call_next.assert_called_once()
        assert mock_request.state.org_id is None

    @pytest.mark.asyncio
    async def test_authenticated_request_sets_state(self):
        """Authenticated request sets org_id and user_id in state."""
        from app.core.tokens import create_access_token
        
        middleware = TenantMiddleware(app=Mock())
        
        token = create_access_token(
            user_id=42,
            org_id=100,
            role=UserRole.OWNER.value,
            permissions=["tenant:read"],
        )
        
        mock_request = Mock()
        mock_request.url.path = "/api/v1/waste"
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = Mock()
        
        mock_response = Mock()
        call_next = AsyncMock(return_value=mock_response)
        
        await middleware.dispatch(mock_request, call_next)
        
        assert mock_request.state.org_id == 100
        assert mock_request.state.user_id == 42
        assert mock_request.state.role == UserRole.OWNER.value

    @pytest.mark.asyncio
    async def test_unauthenticated_request_clears_state(self):
        """Unauthenticated request clears tenant state."""
        middleware = TenantMiddleware(app=Mock())
        
        mock_request = Mock()
        mock_request.url.path = "/api/v1/waste"
        mock_request.headers = {}
        mock_request.state = Mock(spec=[])  # Empty state
        
        mock_response = Mock()
        call_next = AsyncMock(return_value=mock_response)
        
        await middleware.dispatch(mock_request, call_next)
        
        assert mock_request.state.org_id is None
        assert mock_request.state.user_id is None
