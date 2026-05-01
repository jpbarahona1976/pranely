"""Cache service for PRANELY - FASE 9C Performance Optimization.

Provides Redis caching layer for frequently accessed data:
- Waste movement statistics (5min TTL)
- Session data (30min TTL)
- Dashboard aggregations

Target: p95 < 500ms, Redis hit rate > 70%
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.workers.redis_client import get_redis

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis cache service for PRANELY.
    
    Provides typed cache operations with automatic serialization
    and TTL management.
    """
    
    # TTL constants (in seconds)
    TTL_WASTE_STATS = 300  # 5 minutes
    TTL_SESSION = 1800  # 30 minutes
    TTL_DASHBOARD = 300  # 5 minutes
    TTL_ORG_CONFIG = 600  # 10 minutes
    
    def __init__(self):
        self._redis = None
    
    async def _get_redis(self):
        """Lazy initialization of Redis client."""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized value or None if not found
        """
        try:
            redis = await self._get_redis()
            value = await redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache GET failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (default 300)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis = await self._get_redis()
            serialized = json.dumps(value, default=str)
            await redis.set(key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"Cache SET failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis = await self._get_redis()
            await redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache DELETE failed for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "waste_stats:org:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            redis = await self._get_redis()
            # Use SCAN for production safety
            count = 0
            async for key in redis._client.scan_iter(match=pattern):
                await redis.delete(key)
                count += 1
            return count
        except Exception as e:
            logger.warning(f"Cache DELETE_PATTERN failed for pattern {pattern}: {e}")
            return 0
    
    # ========================================================================
    # Waste Movement Cache Operations
    # ========================================================================
    
    async def get_waste_stats(self, org_id: int) -> Optional[dict]:
        """Get cached waste statistics for organization."""
        key = f"waste_stats:org:{org_id}"
        return await self.get(key)
    
    async def set_waste_stats(self, org_id: int, stats: dict) -> bool:
        """Cache waste statistics for organization."""
        key = f"waste_stats:org:{org_id}"
        return await self.set(key, stats, self.TTL_WASTE_STATS)
    
    async def invalidate_waste_stats(self, org_id: int) -> bool:
        """Invalidate waste statistics cache for organization."""
        key = f"waste_stats:org:{org_id}"
        return await self.delete(key)
    
    async def invalidate_waste_stats_all(self) -> int:
        """Invalidate all waste statistics caches."""
        return await self.delete_pattern("waste_stats:org:*")
    
    # ========================================================================
    # Session Cache Operations
    # ========================================================================
    
    async def get_session(self, user_id: int, org_id: int) -> Optional[dict]:
        """Get cached session data."""
        key = f"session:user:{user_id}:org:{org_id}"
        return await self.get(key)
    
    async def set_session(self, user_id: int, org_id: int, session_data: dict) -> bool:
        """Cache session data."""
        key = f"session:user:{user_id}:org:{org_id}"
        return await self.set(key, session_data, self.TTL_SESSION)
    
    async def invalidate_session(self, user_id: int, org_id: int) -> bool:
        """Invalidate session cache."""
        key = f"session:user:{user_id}:org:{org_id}"
        return await self.delete(key)
    
    # ========================================================================
    # Dashboard Cache Operations
    # ========================================================================
    
    async def get_dashboard(self, org_id: int) -> Optional[dict]:
        """Get cached dashboard data."""
        key = f"dashboard:org:{org_id}"
        return await self.get(key)
    
    async def set_dashboard(self, org_id: int, dashboard_data: dict) -> bool:
        """Cache dashboard data."""
        key = f"dashboard:org:{org_id}"
        return await self.set(key, dashboard_data, self.TTL_DASHBOARD)
    
    async def invalidate_dashboard(self, org_id: int) -> bool:
        """Invalidate dashboard cache for organization."""
        key = f"dashboard:org:{org_id}"
        return await self.delete(key)
    
    # ========================================================================
    # Organization Config Cache
    # ========================================================================
    
    async def get_org_config(self, org_id: int) -> Optional[dict]:
        """Get cached organization configuration."""
        key = f"org_config:{org_id}"
        return await self.get(key)
    
    async def set_org_config(self, org_id: int, config: dict) -> bool:
        """Cache organization configuration."""
        key = f"org_config:{org_id}"
        return await self.set(key, config, self.TTL_ORG_CONFIG)
    
    # ========================================================================
    # Cache Statistics
    # ========================================================================
    
    async def get_cache_stats(self) -> dict:
        """
        Get cache statistics for monitoring.
        
        Returns cache hit/miss metrics and current size estimates.
        """
        try:
            redis = await self._get_redis()
            info = await redis._client.info("stats")
            
            return {
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "used_memory_human": info.get("used_memory_human", "N/A"),
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    async def warm_cache(self, org_ids: list[int]) -> dict:
        """
        Pre-warm cache for specified organizations.
        
        Args:
            org_ids: List of organization IDs to warm
            
        Returns:
            Dict with warming results per org_id
        """
        from app.core.database import async_session
        from app.models import WasteMovement
        from sqlalchemy import func, select, and_
        
        results = {}
        for org_id in org_ids:
            try:
                async with async_session() as db:
                    # Pre-compute waste stats for warm cache
                    status_query = (
                        select(
                            WasteMovement.status,
                            func.count().label("count")
                        )
                        .where(
                            and_(
                                WasteMovement.organization_id == org_id,
                                WasteMovement.archived_at.is_(None),
                            )
                        )
                        .group_by(WasteMovement.status)
                    )
                    status_result = await db.execute(status_query)
                    status_counts = {"pending": 0, "in_review": 0, "validated": 0, "rejected": 0, "exception": 0}
                    for row in status_result:
                        status_counts[row.status.value] = row.count
                    
                    total_query = select(func.count()).select_from(WasteMovement).where(
                        and_(
                            WasteMovement.organization_id == org_id,
                            WasteMovement.archived_at.is_(None),
                        )
                    )
                    total = (await db.execute(total_query)).scalar() or 0
                    
                    archived_query = select(func.count()).select_from(WasteMovement).where(
                        WasteMovement.organization_id == org_id,
                        WasteMovement.archived_at.is_not(None),
                    )
                    archived = (await db.execute(archived_query)).scalar() or 0
                    
                    stats = {
                        "total": total,
                        "by_status": status_counts,
                        "archived_count": archived,
                        "_cached_at": datetime.now(timezone.utc).isoformat(),
                    }
                    
                    await self.set_waste_stats(org_id, stats)
                    results[org_id] = {"status": "success", "stats": stats}
            except Exception as e:
                logger.warning(f"Cache warm failed for org {org_id}: {e}")
                results[org_id] = {"status": "error", "error": str(e)}
        
        return results


# Global cache service instance
cache_service = CacheService()


async def get_cache_service() -> CacheService:
    """Dependency to get cache service."""
    return cache_service