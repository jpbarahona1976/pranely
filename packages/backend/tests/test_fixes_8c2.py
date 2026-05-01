"""Tests for FASE 8C.2 Fixes: Rate Limiting, RBAC/Tenant Hardening, Secrets Validation."""
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Set test environment before imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_mock")  # Mock Stripe key
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_mock")  # Mock webhook secret


# =============================================================================
# FIX 1: Rate Limiting Tests
# =============================================================================

class TestRateLimiting:
    """Tests for rate limiting middleware."""

    @pytest.mark.asyncio
    async def test_rate_limit_excluded_paths(self):
        """Test that excluded paths are not rate limited."""
        from app.api.middleware.rate_limit import is_excluded_path
        
        # Public paths should be excluded
        assert is_excluded_path("/api/health") is True
        assert is_excluded_path("/api/health/") is True
        assert is_excluded_path("/docs") is True
        assert is_excluded_path("/openapi.json") is True
        assert is_excluded_path("/api/v1/billing/plans") is True
        assert is_excluded_path("/api/v1/auth/login") is True
        
        # Protected paths should not be excluded
        assert is_excluded_path("/api/v1/waste") is False
        assert is_excluded_path("/api/v1/billing/subscription") is False
        assert is_excluded_path("/api/v1/command") is False

    @pytest.mark.asyncio
    async def test_rate_limit_get_identifier_with_org(self):
        """Test identifier extraction with organization context."""
        from app.api.middleware.rate_limit import get_identifier
        
        # Mock request with org_id in state
        mock_request = MagicMock()
        mock_request.state.org_id = 123
        
        identifier = await get_identifier(mock_request)
        assert identifier == "org:123"

    @pytest.mark.asyncio
    async def test_rate_limit_get_identifier_without_org(self):
        """Test identifier extraction without organization context (IP fallback)."""
        from app.api.middleware.rate_limit import get_identifier
        
        # Mock request without org_id
        mock_request = MagicMock()
        mock_request.state.org_id = None
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.1"
        
        identifier = await get_identifier(mock_request)
        assert identifier == "ip:192.168.1.1"

    @pytest.mark.asyncio
    async def test_rate_limit_get_identifier_x_forwarded(self):
        """Test identifier extraction with X-Forwarded-For header."""
        from app.api.middleware.rate_limit import get_identifier
        
        mock_request = MagicMock()
        mock_request.state.org_id = None
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
        mock_request.client.host = "192.168.1.1"
        
        identifier = await get_identifier(mock_request)
        assert identifier == "ip:10.0.0.1"


# =============================================================================
# FIX 2: RBAC/Tenant Hardening Tests
# =============================================================================

class TestRBACTenantHardening:
    """Tests for RBAC and tenant isolation hardening."""

    @pytest.mark.asyncio
    async def test_billing_require_owner_validates_org_id(self, client, db_session):
        """Test that billing mutation validates org_id.
        
        This test verifies the hardended require_owner_role function
        by calling billing endpoints with proper auth.
        """
        from app.core.security import hash_password
        from app.models import User, Organization, Membership, UserRole
        
        # Create test org and user with owner membership
        org = Organization(name="Billing Test Org", is_active=True)
        db_session.add(org)
        await db_session.flush()
        
        user = User(
            email="billing_rbac@test.com",
            hashed_password=hash_password("password123"),
            full_name="Billing RBAC Test",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        
        membership = Membership(
            user_id=user.id,
            organization_id=org.id,
            role=UserRole.OWNER,
        )
        db_session.add(membership)
        await db_session.commit()
        
        # Login to get token
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "billing_rbac@test.com", "password": "password123"},
        )
        assert response.status_code == 200
        token = response.json()["token"]["access_token"]
        
        # Test billing subscription endpoint with valid auth
        response = await client.get(
            "/api/v1/billing/subscription",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        # Should work with valid auth - 200 or empty subscription response
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_waste_validate_membership_function(self, db_session):
        """Test the validate_membership_and_role helper function."""
        from app.api.v1.waste import validate_membership_and_role
        from app.models import User, Organization, Membership, UserRole
        
        # Create test org
        org = Organization(name="Test Org", is_active=True)
        db_session.add(org)
        await db_session.flush()
        
        # Create test user
        user = User(
            email="rbac_test@test.com",
            hashed_password="fakehash",
            full_name="RBAC Test User",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        
        # Create membership
        membership = Membership(
            user_id=user.id,
            organization_id=org.id,
            role=UserRole.ADMIN,
        )
        db_session.add(membership)
        await db_session.commit()
        
        # Test valid case
        # Should not raise - membership exists
        await validate_membership_and_role(user, org.id, db_session, "test.action")
        
    @pytest.mark.asyncio
    async def test_waste_validate_membership_rejects_invalid_org_id(self, db_session):
        """Test that invalid org_id is rejected."""
        from app.api.v1.waste import validate_membership_and_role
        from fastapi import HTTPException
        from app.models import User, Organization
        
        # Create test org
        org = Organization(name="Test Org 2", is_active=True)
        db_session.add(org)
        await db_session.flush()
        
        # Create test user (no membership)
        user = User(
            email="no_membership@test.com",
            hashed_password="fakehash",
            full_name="No Membership User",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        
        # Test invalid org_id (None or 0)
        with pytest.raises(HTTPException) as exc_info:
            await validate_membership_and_role(user, None, db_session, "test.action")
        assert exc_info.value.status_code == 403
        assert "Invalid organization context" in exc_info.value.detail["detail"]

    @pytest.mark.asyncio
    async def test_waste_validate_membership_rejects_missing_membership(self, db_session):
        """Test that missing membership is rejected with logging."""
        from app.api.v1.waste import validate_membership_and_role
        from fastapi import HTTPException
        from app.models import User, Organization
        
        # Create test org
        org = Organization(name="Test Org 3", is_active=True)
        db_session.add(org)
        await db_session.flush()
        
        # Create test user (no membership for this org)
        user = User(
            email="no_membership@test.com",
            hashed_password="fakehash",
            full_name="No Membership User",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.commit()
        
        # Test with valid org_id but no membership
        with pytest.raises(HTTPException) as exc_info:
            await validate_membership_and_role(user, org.id, db_session, "test.action")
        assert exc_info.value.status_code == 403
        assert "not a member" in exc_info.value.detail["detail"].lower()


# =============================================================================
# FIX 3: Secrets Validation Tests
# =============================================================================

class TestSecretsValidation:
    """Tests for secrets validation in production."""

    def test_dev_environment_allows_missing_secrets(self):
        """Test that development environment allows missing secrets with warnings."""
        os.environ["ENV"] = "development"
        os.environ.pop("STRIPE_SECRET_KEY", None)
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
        
        # Clear cached settings
        import importlib
        import app.core.config as config_module
        if hasattr(config_module.get_settings, 'cache_clear'):
            config_module.get_settings.cache_clear()
        
        from app.core.config import Settings
        settings = Settings()
        
        # Should not raise in dev
        settings.validate_production_config()

    def test_prod_environment_rejects_missing_secrets(self):
        """Test that production environment rejects missing secrets."""
        os.environ["ENV"] = "production"
        os.environ.pop("STRIPE_SECRET_KEY", None)
        
        # Clear cached settings
        import importlib
        import app.core.config as config_module
        if hasattr(config_module.get_settings, 'cache_clear'):
            config_module.get_settings.cache_clear()
        
        from app.core.config import Settings, ConfigurationError
        settings = Settings()
        
        with pytest.raises(ConfigurationError) as exc_info:
            settings.validate_production_config()
        
        assert "STRIPE_SECRET_KEY" in str(exc_info.value)
        assert "STRIPE_WEBHOOK_SECRET" in str(exc_info.value)

    def test_prod_environment_rejects_placeholder_secret(self):
        """Test that production rejects placeholder SECRET_KEY."""
        os.environ["ENV"] = "production"
        os.environ["SECRET_KEY"] = "changeme"
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_xxx"
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_xxx"
        
        # Clear cached settings
        import importlib
        import app.core.config as config_module
        if hasattr(config_module.get_settings, 'cache_clear'):
            config_module.get_settings.cache_clear()
        
        from app.core.config import Settings, ConfigurationError
        settings = Settings()
        
        with pytest.raises(ConfigurationError) as exc_info:
            settings.validate_production_config()
        
        assert "SECRET_KEY" in str(exc_info.value)

    def test_validate_settings_function(self):
        """Test the validate_settings function."""
        os.environ["ENV"] = "development"
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_xxx"
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_xxx"
        
        # Clear cached settings
        import importlib
        import app.core.config as config_module
        if hasattr(config_module.get_settings, 'cache_clear'):
            config_module.get_settings.cache_clear()
        
        from app.core.config import validate_settings
        # Should not raise in dev
        validate_settings()


# =============================================================================
# Integration Tests
# =============================================================================

class TestFixeIntegration:
    """Integration tests for all 3 fixes."""

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_instance(self):
        """Test that rate limiting middleware can be instantiated."""
        from app.api.middleware.rate_limit import RateLimitMiddleware
        
        middleware = RateLimitMiddleware(None, redis_url="redis://localhost:6379")
        assert middleware is not None
        assert middleware.redis_url == "redis://localhost:6379"

    @pytest.mark.asyncio
    async def test_configuration_error_exception(self):
        """Test ConfigurationError exception."""
        from app.core.config import ConfigurationError
        
        error = ConfigurationError("Test error message")
        assert str(error) == "Test error message"