"""
Tests for Redis circuit breaker and worker resilience.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from app.workers.redis_client import CircuitBreaker, CircuitBreakerState


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""
    
    @pytest.fixture
    def cb(self) -> CircuitBreaker:
        """Create fresh circuit breaker."""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5,
        )
    
    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, cb: CircuitBreaker):
        """Circuit starts in CLOSED state."""
        assert cb.is_closed
        assert not cb.state.is_open
        assert not cb.state.is_half_open
    
    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self, cb: CircuitBreaker):
        """Circuit opens after failure threshold reached."""
        for _ in range(3):
            await cb.record_failure()
        
        assert cb.state.is_open
        assert not cb.is_closed
    
    @pytest.mark.asyncio
    async def test_failure_in_half_open_reopens(self, cb: CircuitBreaker):
        """Failure in half-open state reopens circuit."""
        cb.state.is_open = True
        cb.state.is_half_open = True
        cb.state.failures = 0
        
        await cb.record_failure()
        
        assert cb.state.is_open
        assert not cb.state.is_half_open
    
    @pytest.mark.asyncio
    async def test_can_attempt_when_closed(self, cb: CircuitBreaker):
        """can_attempt returns True when closed."""
        assert await cb.can_attempt()
    
    @pytest.mark.asyncio
    async def test_can_attempt_returns_false_when_open_recent(self, cb: CircuitBreaker):
        """can_attempt returns False when open and recent failure."""
        # Open circuit
        for _ in range(3):
            await cb.record_failure()
        
        # Should not allow attempts immediately
        assert not await cb.can_attempt()


class TestCircuitBreakerRecovery:
    """Tests for circuit breaker recovery."""
    
    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self):
        """Circuit can transition to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Open circuit
        await cb.record_failure()
        await cb.record_failure()
        assert cb.state.is_open
        
        # Simulate time passing
        cb.state.last_failure = datetime.now(timezone.utc) - timedelta(seconds=5)
        
        # Should transition to half-open
        assert await cb.can_attempt()
        assert cb.state.is_half_open


# =============================================================================
# Integration Tests (require Redis running)
# =============================================================================

class TestRedisIntegration:
    """Integration tests for Redis client (requires Redis running)."""
    
    @pytest.fixture(autouse=True)
    def check_redis(self):
        """Skip if Redis is not available."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            sock.connect(("localhost", 6379))
            sock.close()
        except (socket.timeout, ConnectionRefusedError):
            pytest.skip("Redis not available")
    
    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self):
        """Test connect → ping → disconnect."""
        from app.workers import redis_client
        
        await redis_client.connect()
        assert await redis_client.is_healthy()
        await redis_client.disconnect()
    
    @pytest.mark.asyncio
    async def test_basic_operations(self):
        """Test basic GET/SET/DELETE operations."""
        from app.workers import redis_client
        
        await redis_client.connect()
        
        # SET
        await redis_client.set("test_key", "test_value", ex=60)
        
        # GET
        value = await redis_client.get("test_key")
        assert value == "test_value"
        
        # DELETE
        await redis_client.delete("test_key")
        value = await redis_client.get("test_key")
        assert value is None
        
        await redis_client.disconnect()
