"""Rate limiting middleware using Redis for multi-tenant API protection.

FASE 8C.2 FIX: Rate Limiting Crítico - Previene DoS
Límites: 100 req/min, 1000 req/hora por organization_id
Excepciones: health, openapi.json, billing/plans (públicos)
"""
import logging
from typing import Callable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Paths excluded from rate limiting (public endpoints)
EXCLUDED_PATHS = {
    "/api/health",
    "/api/health/",
    "/health",
    "/health/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/billing/plans",  # Public plans listing
    "/api/v1/auth/login",      # Login endpoint
    "/api/v1/auth/register",  # Registration endpoint
    "/",                      # Root
}


def is_excluded_path(path: str) -> bool:
    """
    Check if path should be excluded from rate limiting.
    
    Uses exact prefix matching to avoid false positives.
    e.g., /api/v1/waste should NOT match /api/v1/billing/plans
    """
    # Exact matches
    exact_paths = {
        "/api/health",
        "/api/health/",
        "/health",
        "/health/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/",
    }
    
    if path in exact_paths:
        return True
    
    # Prefix matches for public endpoints
    public_prefixes = [
        "/api/v1/billing/plans",      # Public plans listing
        "/api/v1/auth/login",          # Login endpoint
        "/api/v1/auth/register",        # Registration endpoint
    ]
    
    for prefix in public_prefixes:
        if path == prefix:
            return True
    
    return False


async def get_identifier(request: Request) -> str:
    """
    Get rate limit identifier based on organization context.
    
    For authenticated requests, use organization_id for multi-tenant limits.
    For unauthenticated requests, use IP address.
    
    Returns:
        str: Identifier for rate limiting (org_id or IP)
    """
    # Try to get org_id from request state (set by TenantMiddleware)
    org_id = getattr(request.state, "org_id", None)
    
    if org_id:
        return f"org:{org_id}"
    
    # Fallback to IP address for unauthenticated requests
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits per organization.
    
    Uses Redis for distributed rate limiting across multiple instances.
    Limits:
    - 100 requests per minute per org/IP
    - 1000 requests per hour per org/IP
    
    Excludes: health checks, public billing endpoints, auth endpoints
    """
    
    def __init__(self, app, redis_url: str = None):
        super().__init__(app)
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis = None
    
    async def setup(self):
        """Initialize Redis connection."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Test connection
                await self._redis.ping()
                logger.info("Rate limiting Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis for rate limiting: {e}")
                self._redis = None
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ):
        """Process request with rate limiting."""
        # Skip excluded paths
        if is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Setup if needed
        if self._redis is None:
            await self.setup()
        
        # Skip rate limiting if Redis unavailable (fail open for availability)
        if self._redis is None:
            return await call_next(request)
        
        # Get identifier for rate limiting
        identifier = await get_identifier(request)
        
        try:
            # Check minute limit (100 req/min)
            minute_key = f"rl:minute:{identifier}"
            minute_count = await self._redis.incr(minute_key)
            
            # Set expiry on first request
            if minute_count == 1:
                await self._redis.expire(minute_key, 60)
            
            if minute_count > 100:
                logger.warning(
                    f"Rate limit exceeded (minute): identifier={identifier}, "
                    f"path={request.url.path}, count={minute_count}"
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Try again later.",
                        "type": "https://api.pranely.com/errors/rate-limit",
                        "title": "Too Many Requests",
                        "status": 429,
                    },
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit": "100/minute",
                        "X-RateLimit-Remaining": "0",
                    }
                )
            
            # Check hour limit (1000 req/hour)
            hour_key = f"rl:hour:{identifier}"
            hour_count = await self._redis.incr(hour_key)
            
            if hour_count == 1:
                await self._redis.expire(hour_key, 3600)
            
            if hour_count > 1000:
                logger.warning(
                    f"Rate limit exceeded (hour): identifier={identifier}, "
                    f"path={request.url.path}, count={hour_count}"
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Try again later.",
                        "type": "https://api.pranely.com/errors/rate-limit",
                        "title": "Too Many Requests",
                        "status": 429,
                    },
                    headers={
                        "Retry-After": "3600",
                        "X-RateLimit-Limit": "1000/hour",
                        "X-RateLimit-Remaining": "0",
                    }
                )
            
            # Add rate limit headers to response
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = "100/minute, 1000/hour"
            response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, 100 - minute_count))
            response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, 1000 - hour_count))
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # On Redis failure, allow request (fail open for availability)
            return await call_next(request)


async def setup_rate_limiting(redis_url: str = None) -> RateLimitMiddleware:
    """
    Setup rate limiting middleware.
    
    Args:
        redis_url: Redis connection URL (defaults to settings.REDIS_URL)
    
    Returns:
        Configured RateLimitMiddleware instance
    """
    from app.main import app
    url = redis_url or settings.REDIS_URL
    
    middleware = RateLimitMiddleware(app, redis_url=url)
    await middleware.setup()
    
    return middleware