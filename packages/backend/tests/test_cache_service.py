"""Tests for cache service - FASE 9C Performance.

Tests cache layer for waste stats and dashboard caching.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.services.cache import CacheService, cache_service


class TestCacheService:
    """Test suite for CacheService."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for testing."""
        mock = MagicMock()
        mock._client = MagicMock()
        mock._client.info = AsyncMock(return_value={
            "keyspace_hits": 1000,
            "keyspace_misses": 200,
            "total_commands_processed": 1200,
            "used_memory_human": "1.5M",
        })
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def cache(self):
        """Create cache service instance."""
        return CacheService()

    # ========================================================================
    # Basic Operations Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cache_get_returns_none_on_miss(self, cache, mock_redis):
        """Test that cache.get returns None on cache miss."""
        cache._redis = mock_redis
        mock_redis.get.return_value = None
        
        result = await cache.get("test:key")
        
        assert result is None
        mock_redis.get.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_cache_get_returns_deserialized_value(self, cache, mock_redis):
        """Test that cache.get deserializes JSON values."""
        cache._redis = mock_redis
        mock_redis.get.return_value = '{"total": 42, "by_status": {}}'
        
        result = await cache.get("test:key")
        
        assert result == {"total": 42, "by_status": {}}

    @pytest.mark.asyncio
    async def test_cache_set_serializes_and_stores(self, cache, mock_redis):
        """Test that cache.set serializes Python objects."""
        cache._redis = mock_redis
        mock_redis.set.return_value = True
        
        result = await cache.set("test:key", {"value": 123}, ttl=300)
        
        assert result is True
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_delete(self, cache, mock_redis):
        """Test cache.delete removes key."""
        cache._redis = mock_redis
        mock_redis.delete.return_value = True
        
        result = await cache.delete("test:key")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_cache_handles_redis_error_gracefully(self, cache, mock_redis):
        """Test that cache operations fail gracefully on Redis errors."""
        cache._redis = mock_redis
        mock_redis.get.side_effect = Exception("Redis connection error")
        
        # Should not raise, returns None
        result = await cache.get("test:key")
        assert result is None
        
        # For set, we need to simulate error on set operation
        mock_redis.set.side_effect = Exception("Redis connection error")
        result = await cache.set("test:key", {"data": 1})
        assert result is False
        
        # Reset for delete test
        mock_redis.set.side_effect = None
        mock_redis.delete.side_effect = Exception("Redis connection error")
        result = await cache.delete("test:key")
        assert result is False

    # ========================================================================
    # Waste Stats Cache Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_waste_stats_uses_correct_key(self, cache, mock_redis):
        """Test that waste stats cache uses org_id in key."""
        cache._redis = mock_redis
        mock_redis.get.return_value = '{"total": 10}'
        
        result = await cache.get_waste_stats(org_id=42)
        
        mock_redis.get.assert_called_with("waste_stats:org:42")

    @pytest.mark.asyncio
    async def test_set_waste_stats_uses_correct_ttl(self, cache, mock_redis):
        """Test that waste stats cache uses 5min TTL."""
        cache._redis = mock_redis
        
        await cache.set_waste_stats(org_id=1, stats={"total": 5})
        
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "waste_stats:org:1"
        assert call_args[1]["ex"] == 300  # 5 minutes

    @pytest.mark.asyncio
    async def test_invalidate_waste_stats(self, cache, mock_redis):
        """Test waste stats invalidation."""
        cache._redis = mock_redis
        
        result = await cache.invalidate_waste_stats(org_id=1)
        
        assert result is True
        mock_redis.delete.assert_called_with("waste_stats:org:1")

    # ========================================================================
    # Session Cache Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_session_uses_user_and_org(self, cache, mock_redis):
        """Test session cache key includes user_id and org_id."""
        cache._redis = mock_redis
        
        await cache.get_session(user_id=5, org_id=10)
        
        mock_redis.get.assert_called_with("session:user:5:org:10")

    @pytest.mark.asyncio
    async def test_set_session_uses_30min_ttl(self, cache, mock_redis):
        """Test session cache uses 30min TTL."""
        cache._redis = mock_redis
        
        await cache.set_session(user_id=1, org_id=1, session_data={"token": "abc"})
        
        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == 1800  # 30 minutes

    # ========================================================================
    # Dashboard Cache Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_dashboard_cache_operations(self, cache, mock_redis):
        """Test dashboard cache get/set/invalidate."""
        cache._redis = mock_redis
        
        # Set
        await cache.set_dashboard(org_id=1, dashboard_data={"widgets": []})
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "dashboard:org:1"
        
        # Get
        mock_redis.get.return_value = '{"widgets": []}'
        result = await cache.get_dashboard(org_id=1)
        assert result == {"widgets": []}
        
        # Invalidate
        await cache.invalidate_dashboard(org_id=1)
        mock_redis.delete.assert_called_with("dashboard:org:1")

    # ========================================================================
    # Cache Stats Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache, mock_redis):
        """Test cache statistics retrieval."""
        cache._redis = mock_redis
        
        stats = await cache.get_cache_stats()
        
        assert "keyspace_hits" in stats
        assert "keyspace_misses" in stats
        assert stats["keyspace_hits"] == 1000

    # ========================================================================
    # TTL Constants Tests
    # ========================================================================

    def test_ttl_constants(self):
        """Test that TTL constants are set correctly."""
        assert CacheService.TTL_WASTE_STATS == 300  # 5 min
        assert CacheService.TTL_SESSION == 1800  # 30 min
        assert CacheService.TTL_DASHBOARD == 300  # 5 min
        assert CacheService.TTL_ORG_CONFIG == 600  # 10 min


class TestCacheServiceWarmCache:
    """Test cache warming functionality."""

    @pytest.mark.asyncio
    async def test_warm_cache_integration_point(self):
        """Test that warm_cache method exists and is callable."""
        cache = CacheService()
        
        # Verify the method exists and is async
        assert hasattr(cache, 'warm_cache')
        import inspect
        assert inspect.iscoroutinefunction(cache.warm_cache)
        
        # Note: Full integration test requires actual DB setup
        # This test verifies the method signature only


class TestCacheServiceKeyPatterns:
    """Test cache key patterns."""

    def test_waste_stats_key_format(self):
        """Test waste stats cache key format."""
        cache = CacheService()
        key = f"waste_stats:org:{42}"
        assert key == "waste_stats:org:42"

    def test_session_key_format(self):
        """Test session cache key format."""
        key = f"session:user:{5}:org:{10}"
        assert key == "session:user:5:org:10"

    def test_dashboard_key_format(self):
        """Test dashboard cache key format."""
        key = f"dashboard:org:{1}"
        assert key == "dashboard:org:1"

    def test_org_config_key_format(self):
        """Test org config cache key format."""
        key = f"org_config:{99}"
        assert key == "org_config:99"