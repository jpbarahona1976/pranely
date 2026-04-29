"""Redis client with circuit breaker pattern for resilience."""
import asyncio
import logging
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.exceptions import (
    ConnectionError,
    TimeoutError,
    RedisError,
    TimeoutError as RedisTimeoutError,
)

from app.core.config import get_settings

logger = logging.getLogger("redis.client")


@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking."""
    failures: int = 0
    last_failure: Optional[datetime] = None
    is_open: bool = False
    is_half_open: bool = False


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for Redis connections.
    
    States:
    - CLOSED: Normal operation, requests flow through
    - OPEN: Circuit is tripped, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.half_open_max_calls = half_open_max_calls
        self.state = CircuitBreakerState()
        self._lock = asyncio.Lock()
    
    @property
    def is_closed(self) -> bool:
        return not self.state.is_open and not self.state.is_half_open
    
    async def record_success(self) -> None:
        """Record successful call, reset circuit if half-open."""
        async with self._lock:
            if self.state.is_half_open:
                self.state.is_half_open = False
                self.state.is_open = False
                self.state.failures = 0
                logger.info("Circuit breaker: HALF_OPEN → CLOSED")
            elif self.state.is_open:
                # Should not happen, but reset if it does
                self.state.is_open = False
                self.state.failures = 0
    
    async def record_failure(self) -> None:
        """Record failed call, potentially open the circuit."""
        async with self._lock:
            self.state.failures += 1
            self.state.last_failure = datetime.now(timezone.utc)
            
            if self.state.is_half_open:
                self.state.is_half_open = False
                self.state.is_open = True
                logger.warning("Circuit breaker: HALF_OPEN → OPEN (call failed)")
            elif self.state.failures >= self.failure_threshold:
                self.state.is_open = True
                logger.warning(
                    f"Circuit breaker: CLOSED → OPEN "
                    f"(failures={self.state.failures})"
                )
    
    async def can_attempt(self) -> bool:
        """Check if a call should be attempted."""
        async with self._lock:
            if self.state.is_open:
                # Check if recovery timeout has passed
                if self.state.last_failure:
                    if datetime.now(timezone.utc) - self.state.last_failure >= self.recovery_timeout:
                        self.state.is_open = False
                        self.state.is_half_open = True
                        self.state.failures = 0
                        logger.info("Circuit breaker: OPEN → HALF_OPEN (recovery timeout)")
                        return True
                return False
            return True


class RedisClient:
    """
    Redis client wrapper with circuit breaker and timeout handling.
    
    Provides resilient Redis operations with automatic reconnection
    and fallback behavior.
    """
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
        )
        self._settings = get_settings()
    
    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self._settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0,
                    retry_on_timeout=True,
                    retry_on_error=[RedisTimeoutError],
                )
                # Test connection
                await self._client.ping()
                logger.info("Redis connection established")
            except RedisError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._client = None
                raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")
    
    async def is_healthy(self) -> bool:
        """Check if Redis is healthy."""
        try:
            if self._client is None:
                await self.connect()
            await self._client.ping()
            return True
        except RedisError:
            return False
    
    @asynccontextmanager
    async def circuit_protected(self):
        """
        Context manager for circuit breaker protected operations.
        
        Yields True if operation is allowed, raises exception otherwise.
        """
        if not await self._circuit_breaker.can_attempt():
            raise ConnectionError("Circuit breaker is OPEN - Redis unavailable")
        yield True
    
    async def get(self, key: str) -> Optional[str]:
        """Get value with circuit breaker protection."""
        try:
            async with self.circuit_protected():
                if self._client is None:
                    await self.connect()
                result = await self._client.get(key)
                await self._circuit_breaker.record_success()
                return result
        except (ConnectionError, TimeoutError) as e:
            await self._circuit_breaker.record_failure()
            logger.warning(f"Redis GET failed: {e}")
            raise
    
    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
    ) -> bool:
        """Set value with circuit breaker protection."""
        try:
            async with self.circuit_protected():
                if self._client is None:
                    await self.connect()
                result = await self._client.set(key, value, ex=ex)
                await self._circuit_breaker.record_success()
                return result
        except (ConnectionError, TimeoutError) as e:
            await self._circuit_breaker.record_failure()
            logger.warning(f"Redis SET failed: {e}")
            raise
    
    async def delete(self, key: str) -> int:
        """Delete key with circuit breaker protection."""
        try:
            async with self.circuit_protected():
                if self._client is None:
                    await self.connect()
                result = await self._client.delete(key)
                await self._circuit_breaker.record_success()
                return result
        except (ConnectionError, TimeoutError) as e:
            await self._circuit_breaker.record_failure()
            logger.warning(f"Redis DELETE failed: {e}")
            raise
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration with circuit breaker protection."""
        try:
            async with self.circuit_protected():
                if self._client is None:
                    await self.connect()
                result = await self._client.expire(key, seconds)
                await self._circuit_breaker.record_success()
                return result
        except (ConnectionError, TimeoutError) as e:
            await self._circuit_breaker.record_failure()
            logger.warning(f"Redis EXPIRE failed: {e}")
            raise
    
    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get circuit breaker state for monitoring."""
        return self._circuit_breaker


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency to get Redis client."""
    return redis_client
