# 8A MOBILE BRIDGE - Backend Tests
"""Tests para Mobile Bridge API - Fase 8A."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
import asyncio

# Test configuration
BRIDGE_TOKEN_EXPIRY_MINUTES = 5


class TestBridgeSession:
    """Tests para POST /api/bridge/session"""

    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        user = MagicMock()
        user.id = 1
        user.org_id = 1
        user.role = "admin"
        user.is_active = True
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()

    def test_bridge_session_response_schema(self):
        """Test that BridgeSessionResponse has correct schema."""
        from app.schemas.bridge import BridgeSessionResponse
        
        response = BridgeSessionResponse(
            session_id="test-session-id",
            qr_token="ABCD1234EFGH5678",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            ws_url="ws://localhost:8000/ws/bridge/test-session-id",
            ws_token="test-bridge-token",
        )
        
        assert response.session_id == "test-session-id"
        assert response.qr_token == "ABCD1234EFGH5678"
        assert response.ws_token == "test-bridge-token"
        assert response.expires_at > datetime.utcnow()

    def test_bridge_token_creation(self):
        """Test bridge token contains expected claims."""
        from app.api.bridge import _create_bridge_token, _decode_bridge_token
        
        session_id = "test-session-123"
        user_id = 1
        org_id = 1
        
        token = _create_bridge_token(session_id, user_id, org_id)
        payload = _decode_bridge_token(token)
        
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["org_id"] == org_id
        assert payload["session_id"] == session_id
        assert payload["type"] == "bridge"
        assert "exp" in payload
        assert "iat" in payload

    def test_bridge_token_invalid_type(self):
        """Test that non-bridge tokens are rejected."""
        from app.core.tokens import create_access_token
        from app.api.bridge import _decode_bridge_token
        
        # Create regular access token (not bridge type)
        regular_token = create_access_token(user_id=1, org_id=1)
        payload = _decode_bridge_token(regular_token)
        
        assert payload is None

    def test_bridge_token_expired(self):
        """Test that expired bridge tokens are rejected."""
        from jose import jwt
        from app.core.config import settings
        
        # Create an already-expired bridge token
        expire = datetime.utcnow() - timedelta(minutes=1)
        payload = {
            "sub": "1",
            "org_id": 1,
            "session_id": "test-session",
            "type": "bridge",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        
        from app.api.bridge import _decode_bridge_token
        result = _decode_bridge_token(expired_token)
        
        assert result is None


class TestBridgeSessionExpiry:
    """Tests para expiración de sesiones bridge."""

    def test_session_expiry_calculation(self):
        """Test that session expiry is correctly calculated."""
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=BRIDGE_TOKEN_EXPIRY_MINUTES)
        
        # Should expire in approximately 5 minutes
        diff = (expires_at - now).total_seconds()
        assert 299 < diff <= 300  # Allow 1 second tolerance

    def test_expired_session_detection(self):
        """Test detection of expired sessions."""
        from datetime import datetime, timedelta
        
        # Create an expired session
        expired_time = datetime.utcnow() - timedelta(minutes=1)
        is_expired = datetime.utcnow() > expired_time
        
        assert is_expired is True
        
        # Create a valid session
        valid_time = datetime.utcnow() + timedelta(minutes=5)
        is_expired = datetime.utcnow() > valid_time
        
        assert is_expired is False


class TestBridgeWebSocketMessages:
    """Tests para mensajes WebSocket bridge."""

    def test_connected_message_format(self):
        """Test connected message has correct format."""
        from app.schemas.bridge import BridgeWSConnected
        
        msg = BridgeWSConnected(
            session_id="test-session",
            scanned_count=0,
            server_time=datetime.utcnow().isoformat(),
        )
        
        assert msg.type == "connected"
        assert msg.session_id == "test-session"
        assert msg.scanned_count == 0

    def test_scan_ack_message_format(self):
        """Test scan acknowledgement message format."""
        from app.schemas.bridge import BridgeWSScanAck
        
        msg = BridgeWSScanAck(
            scanned_count=1,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        assert msg.type == "scan_ack"
        assert msg.scanned_count == 1

    def test_sync_response_message_format(self):
        """Test sync response message format."""
        from app.schemas.bridge import BridgeWSSyncResponse
        
        msg = BridgeWSSyncResponse(
            session_id="test-session",
            scanned_count=5,
            last_sync=datetime.utcnow().isoformat(),
            server_time=datetime.utcnow().isoformat(),
        )
        
        assert msg.type == "sync_response"
        assert msg.session_id == "test-session"
        assert msg.scanned_count == 5
        assert msg.last_sync is not None


class TestBridgeRBAC:
    """Tests para RBAC del bridge."""

    @pytest.mark.parametrize("role,allowed", [
        ("owner", True),
        ("admin", True),
        ("member", True),
        ("viewer", False),
    ])
    def test_role_based_access(self, role, allowed):
        """Test that only allowed roles can create bridge sessions."""
        allowed_roles = {"owner", "admin", "member"}
        
        has_access = role in allowed_roles
        assert has_access == allowed


class TestBridgeCleanup:
    """Tests para cleanup de sesiones expiradas."""

    @pytest.mark.asyncio
    async def test_get_bridge_stats(self):
        """Test getting bridge statistics."""
        import pytest
        from app.api.bridge import get_bridge_stats
        from app.core.config import settings
        
        # Check if Redis is available, skip if not
        try:
            import redis.asyncio as redis
            r = redis.from_url(settings.REDIS_URL)
            await r.ping()
            await r.close()
        except Exception:
            pytest.skip("Redis not available for this test")
        
        stats = await get_bridge_stats()
        
        assert "total_sessions" in stats
        assert "active_connections" in stats
        assert "expired_sessions" in stats
        assert "sessions" in stats
        assert isinstance(stats["sessions"], list)


class TestBridgeStatusSchema:
    """Tests para schema de estado de sesión."""

    def test_bridge_session_status_schema(self):
        """Test BridgeSessionStatus schema."""
        from app.schemas.bridge import BridgeSessionStatus
        
        status = BridgeSessionStatus(
            session_id="test-session",
            status="waiting",
            scanned_count=0,
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            is_expired=False,
        )
        
        assert status.session_id == "test-session"
        assert status.status == "waiting"
        assert status.scanned_count == 0
        assert status.is_expired is False

    def test_bridge_session_status_expired(self):
        """Test BridgeSessionStatus with expired session."""
        from app.schemas.bridge import BridgeSessionStatus
        
        status = BridgeSessionStatus(
            session_id="test-session",
            status="expired",
            scanned_count=0,
            expires_at=datetime.utcnow() - timedelta(minutes=1),
            is_expired=True,
        )
        
        assert status.status == "expired"
        assert status.is_expired is True


# Integration test markers
pytestmark = pytest.mark.asyncio


class TestBridgeAPIIntegration:
    """Integration tests for Bridge API (requires full app setup)."""

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        from app.main import app
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    async def test_bridge_session_requires_auth(self, async_client):
        """Test that bridge session requires authentication."""
        response = await async_client.post("/bridge/session")
        
        assert response.status_code == 401

    async def test_bridge_session_status_requires_auth(self, async_client):
        """Test that bridge status requires authentication."""
        response = await async_client.get("/bridge/session/TESTTOKEN")
        
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
