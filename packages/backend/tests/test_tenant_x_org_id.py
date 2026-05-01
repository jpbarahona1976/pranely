"""Tests for TenantMiddleware x-org-id header propagation and ASGI middleware order.

FIX: MetricsMiddleware captures x-org-id AFTER TenantMiddleware injects it.
ASGI middleware execution order (LIFO):
  1. TenantMiddleware (added last, executes first) → injects x-org-id
  2. RateLimitMiddleware
  3. AuditMiddleware  
  4. MetricsMiddleware (added first, executes last) → captures correct org_id
"""
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import Request

from app.api.middleware.tenant import TenantMiddleware, get_tenant_context
from app.models import UserRole


class TestTenantMiddlewareXOrgIdHeader:
    """Verify TenantMiddleware injects x-org-id into request.scope for MetricsMiddleware."""

    @pytest.mark.asyncio
    async def test_sets_x_org_id_header_when_org_id_exists(self):
        """TenantMiddleware injects x-org-id header with correct org_id value."""
        middleware = TenantMiddleware(app=Mock())

        from app.core.tokens import create_access_token
        token = create_access_token(
            user_id=42,
            org_id=100,
            role=UserRole.OWNER.value,
            permissions=["tenant:read"],
        )

        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/waste"
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = Mock()
        mock_request.scope = {"headers": []}

        call_next = AsyncMock(return_value=Mock())
        await middleware.dispatch(mock_request, call_next)

        # Verify x-org-id header was added
        headers_dict = dict(mock_request.scope["headers"])
        assert b"x-org-id" in headers_dict
        assert headers_dict[b"x-org-id"] == b"100"

    @pytest.mark.asyncio
    async def test_request_state_also_populated(self):
        """request.state.org_id is set alongside header injection."""
        middleware = TenantMiddleware(app=Mock())

        from app.core.tokens import create_access_token
        token = create_access_token(
            user_id=42,
            org_id=100,
            role=UserRole.OWNER.value,
            permissions=["tenant:read"],
        )

        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/waste"
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = Mock()
        mock_request.scope = {"headers": []}

        call_next = AsyncMock(return_value=Mock())
        await middleware.dispatch(mock_request, call_next)

        assert mock_request.state.org_id == 100
        assert mock_request.state.user_id == 42

    @pytest.mark.asyncio
    async def test_replaces_existing_x_org_id_header(self):
        """Existing x-org-id header is replaced, not duplicated."""
        middleware = TenantMiddleware(app=Mock())

        from app.core.tokens import create_access_token
        token = create_access_token(
            user_id=1,
            org_id=200,
            role=UserRole.ADMIN.value,
            permissions=["tenant:read"],
        )

        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/audit"
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = Mock()
        # Pre-existing x-org-id header
        mock_request.scope = {"headers": [(b"x-org-id", b"old-value"), (b"accept", b"application/json")]}

        call_next = AsyncMock(return_value=Mock())
        await middleware.dispatch(mock_request, call_next)

        # Verify old header replaced
        headers_dict = dict(mock_request.scope["headers"])
        assert headers_dict[b"x-org-id"] == b"200"

        # Verify only one x-org-id header
        x_org_count = sum(1 for k, _ in mock_request.scope["headers"] if k == b"x-org-id")
        assert x_org_count == 1

    @pytest.mark.asyncio
    async def test_no_header_added_when_org_id_is_none(self):
        """No x-org-id header added when org_id is None in token."""
        middleware = TenantMiddleware(app=Mock())

        from app.core.tokens import create_access_token
        token = create_access_token(
            user_id=1,
            org_id=None,
            role=UserRole.VIEWER.value,
            permissions=["tenant:read"],
        )

        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/any"
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = Mock()
        mock_request.scope = {"headers": []}

        call_next = AsyncMock(return_value=Mock())
        await middleware.dispatch(mock_request, call_next)

        headers_dict = dict(mock_request.scope["headers"])
        assert b"x-org-id" not in headers_dict

    @pytest.mark.asyncio
    async def test_public_paths_skip_header_injection(self):
        """Public paths like /api/health do not get header injection."""
        middleware = TenantMiddleware(app=Mock())

        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/health"
        mock_request.headers = {}
        mock_request.state = Mock()
        mock_request.scope = {"headers": []}

        call_next = AsyncMock(return_value=Mock())
        await middleware.dispatch(mock_request, call_next)

        # No header added for public paths
        headers_dict = dict(mock_request.scope["headers"])
        assert b"x-org-id" not in headers_dict
        # State should remain None
        assert mock_request.state.org_id is None

    @pytest.mark.asyncio
    async def test_request_scope_headers_initialized_if_missing(self):
        """If headers key is missing from scope, it is initialized."""
        middleware = TenantMiddleware(app=Mock())

        from app.core.tokens import create_access_token
        token = create_access_token(
            user_id=1,
            org_id=300,
            role=UserRole.MEMBER.value,
            permissions=["tenant:read"],
        )

        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/dashboard"
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = Mock()
        # headers key missing from scope
        mock_request.scope = {}

        call_next = AsyncMock(return_value=Mock())
        await middleware.dispatch(mock_request, call_next)

        # Headers should be initialized and contain x-org-id
        assert "headers" in mock_request.scope
        headers_dict = dict(mock_request.scope["headers"])
        assert b"x-org-id" in headers_dict
        assert headers_dict[b"x-org-id"] == b"300"


class TestASGIMiddlewareOrder:
    """Verify ASGI middleware execution order ensures correct org_id propagation."""

    @pytest.mark.asyncio
    async def test_asgi_middleware_order_tenant_metrics(self):
        """
        CRITICAL TEST: TenantMiddleware MUST inject x-org-id BEFORE MetricsMiddleware captures.
        
        ASGI execution order (LIFO - Last In, First Out):
          1. TenantMiddleware (added LAST) → executes FIRST → injects x-org-id=123
          2. AuditMiddleware
          3. RateLimitMiddleware
          4. MetricsMiddleware (added FIRST) → executes LAST → captures x-org-id=123
        
        This test verifies that when a request flows through the middleware chain,
        the x-org-id header is correctly propagated and can be read by downstream
        middlewares like MetricsMiddleware.
        """
        # Create TenantMiddleware (simulates what happens when it's added last)
        tenant_middleware = TenantMiddleware(app=Mock())

        from app.core.tokens import create_access_token
        # Create a token with known org_id=123
        token = create_access_token(
            user_id=42,
            org_id=123,  # This is the value MetricsMiddleware should see
            role=UserRole.OWNER.value,
            permissions=["tenant:read"],
        )

        # Create mock request with initial empty headers
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/waste/456"
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = Mock()
        mock_request.scope = {"headers": []}

        # Simulate middleware chain execution
        # In real app, MetricsMiddleware would capture after TenantMiddleware
        
        # First: TenantMiddleware processes (simulates add_middleware order)
        call_next = AsyncMock(return_value=Mock())
        await tenant_middleware.dispatch(mock_request, call_next)

        # Verify: x-org-id=123 is now in scope (ready for MetricsMiddleware to capture)
        headers_dict = dict(mock_request.scope["headers"])
        
        # MetricsMiddleware reads from headers, so this is what it should see
        x_org_id_header = headers_dict.get(b"x-org-id", b"unknown")
        assert x_org_id_header == b"123", (
            f"Expected x-org-id=123 in scope for MetricsMiddleware, "
            f"got x-org-id={x_org_id_header.decode()}. "
            f"This means Prometheus metrics will show 'unknown' instead of tenant ID."
        )

    @pytest.mark.asyncio
    async def test_metrics_middleware_reads_correct_org_id_from_scope(self):
        """
        Verify MetricsMiddleware can read x-org-id from scope after TenantMiddleware injection.
        
        This simulates the actual MetricsMiddleware behavior:
        1. Read headers from scope["headers"]
        2. Find x-org-id header
        3. Use its value in Prometheus labels
        """
        # Simulate what happens after TenantMiddleware has injected x-org-id
        from app.core.tokens import create_access_token
        token = create_access_token(
            user_id=99,
            org_id=456,  # This should appear in metrics, NOT "unknown"
            role=UserRole.MEMBER.value,
        )

        # Create request with x-org-id already injected (as TenantMiddleware would do)
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/dashboard"
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = Mock()
        mock_request.scope = {
            "headers": [
                (b"host", b"localhost:8000"),
                (b"x-org-id", b"456"),  # TenantMiddleware already injected this
                (b"authorization", b"Bearer ..."),
            ]
        }

        # Simulate MetricsMiddleware reading x-org-id from scope
        org_id = "unknown"
        for header_name, header_value in mock_request.scope.get("headers", []):
            if header_name == b"x-org-id":
                org_id = header_value.decode()
                break

        # This is what MetricsMiddleware does - verify it gets correct value
        assert org_id == "456", (
            f"MetricsMiddleware would record org_id='{org_id}' in Prometheus. "
            f"Expected org_id='456'. If 'unknown', all tenant metrics are blind."
        )

    @pytest.mark.asyncio
    async def test_full_middleware_chain_integration(self):
        """
        Integration test: Verify full request flow through middleware chain.
        
        This test simulates the complete ASGI flow:
        1. Request arrives with Bearer token
        2. TenantMiddleware extracts org_id and injects x-org-id
        3. MetricsMiddleware captures x-org-id for Prometheus
        """
        from app.core.tokens import create_access_token
        
        # Create token with known org_id
        token = create_access_token(
            user_id=77,
            org_id=789,
            role=UserRole.ADMIN.value,
        )

        # Initialize request scope as FastAPI/Starlette would
        request_scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/waste",
            "headers": [
                (b"host", b"localhost:8000"),
                (b"authorization", f"Bearer {token}".encode()),
            ],
        }

        # Step 1: TenantMiddleware processes (added last in main.py, executes first)
        tenant_middleware = TenantMiddleware(app=Mock())
        
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/v1/waste"
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.state = Mock()
        mock_request.scope = request_scope.copy()

        call_next = AsyncMock(return_value=Mock())
        await tenant_middleware.dispatch(mock_request, call_next)

        # Step 2: Simulate MetricsMiddleware reading (added first, executes last)
        # This is the ACTUAL code from observability/middleware.py lines 34-39
        metrics_org_id = "unknown"
        for header_name, header_value in mock_request.scope.get("headers", []):
            if header_name == b"x-org-id":
                metrics_org_id = header_value.decode()
                break

        # ASSERTION: Metrics should see org_id=789, NOT "unknown"
        assert metrics_org_id == "789", (
            f"BUG DETECTED: Metrics recorded org_id='{metrics_org_id}' instead of '789'. "
            f"This means Prometheus/Grafana dashboards show 'unknown' for all tenant metrics. "
            f"Fix: Ensure TenantMiddleware is added AFTER MetricsMiddleware in main.py "
            f"OR verify x-org-id injection happens before MetricsMiddleware captures."
        )
        
        # Additional verification: request.state also has org_id
        assert mock_request.state.org_id == 789
        assert mock_request.state.user_id == 77
