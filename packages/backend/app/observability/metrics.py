"""PRANELY Metrics System - Prometheus instrumentation.

FASE 9B: Core metrics for API observability.
Tracks: latency, throughput, errors, queue status.
"""
from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from fastapi import APIRouter, Request
from typing import Callable
import time
from functools import wraps

# =============================================================================
# Metrics Definitions
# =============================================================================

# Application info
APP_INFO = Info("pranely_app", "PRANELY application information")
APP_INFO.info({
    "version": "1.13.0",
    "environment": "development",
})

# Request metrics
REQUEST_COUNT = Counter(
    "pranely_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code", "org_id"]
)

REQUEST_LATENCY = Histogram(
    "pranely_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint", "org_id"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)
)

REQUEST_IN_PROGRESS = Gauge(
    "pranely_http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"]
)

# Error metrics
ERROR_COUNT = Counter(
    "pranely_errors_total",
    "Total errors",
    ["error_type", "endpoint", "org_id"]
)

# Database metrics
DB_QUERY_COUNT = Counter(
    "pranely_db_queries_total",
    "Total database queries",
    ["operation", "org_id"]
)

DB_QUERY_LATENCY = Histogram(
    "pranely_db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# Redis metrics
REDIS_OPERATIONS = Counter(
    "pranely_redis_operations_total",
    "Total Redis operations",
    ["operation", "status"]
)

REDIS_LATENCY = Histogram(
    "pranely_redis_operation_duration_seconds",
    "Redis operation latency in seconds",
    ["operation"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1)
)

# Queue/Worker metrics
RQ_JOBS_TOTAL = Counter(
    "pranely_rq_jobs_total",
    "Total RQ jobs",
    ["job_name", "status"]  # status: queued, started, finished, failed
)

RQ_JOB_DURATION = Histogram(
    "pranely_rq_job_duration_seconds",
    "RQ job duration in seconds",
    ["job_name"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0)
)

RQ_QUEUE_SIZE = Gauge(
    "pranely_rq_queue_size",
    "Current RQ queue size",
    ["queue_name"]
)

RQ_WORKERS_ACTIVE = Gauge(
    "pranely_rq_workers_active",
    "Number of active RQ workers",
    ["queue_name"]
)

# Rate limiting metrics
RATE_LIMIT_HITS = Counter(
    "pranely_rate_limit_hits_total",
    "Total rate limit hits",
    ["org_id", "endpoint"]
)

# Auth metrics
AUTH_ATTEMPTS = Counter(
    "pranely_auth_attempts_total",
    "Total authentication attempts",
    ["result", "org_id"]  # result: success, failure, rate_limited
)

# Health metrics
HEALTH_CHECK_STATUS = Gauge(
    "pranely_health_check_status",
    "Health check component status (1=healthy, 0=unhealthy)",
    ["component"]  # component: postgres, redis, api
)


# =============================================================================
# Metrics Router
# =============================================================================

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def metrics_endpoint():
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )


# =============================================================================
# Helper Functions
# =============================================================================

def get_org_id(request: Request) -> str:
    """Extract org_id from request state or return 'unknown'."""
    org_id = getattr(request.state, "org_id", None)
    return str(org_id) if org_id else "unknown"


def get_endpoint_path(request: Request) -> str:
    """Get normalized endpoint path for metrics."""
    path = request.url.path
    # Normalize dynamic segments
    if path.startswith("/api/v1/"):
        parts = path.split("/")
        # Simplify: /api/v1/users/123 -> /api/v1/users/{id}
        normalized = []
        for i, part in enumerate(parts):
            if part.isdigit():
                normalized.append("{id}")
            elif part.startswith("pk") and len(part) > 2 and part[2:].isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/".join(normalized)
    return path


# =============================================================================
# Decorators for automatic instrumentation
# =============================================================================

def track_request_metrics(func: Callable) -> Callable:
    """Decorator to track request metrics automatically."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if request is None:
            # Try to get request from args
            for arg in args:
                if hasattr(arg, "url"):
                    request = arg
                    break
            else:
                return await func(*args, **kwargs)
        
        method = request.method
        endpoint = get_endpoint_path(request)
        org_id = get_org_id(request)
        
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        
        start_time = time.perf_counter()
        try:
            response = await func(*args, **kwargs)
            status_code = getattr(response, "status_code", 200)
            return response
        except Exception as e:
            status_code = 500
            ERROR_COUNT.labels(
                error_type=type(e).__name__,
                endpoint=endpoint,
                org_id=org_id
            ).inc()
            raise
        finally:
            duration = time.perf_counter() - start_time
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                org_id=org_id
            ).inc()
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint,
                org_id=org_id
            ).observe(duration)
    
    return wrapper


def track_db_query(operation: str):
    """Decorator to track database query metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                DB_QUERY_COUNT.labels(operation=operation).inc()
                return result
            except Exception:
                raise
            finally:
                duration = time.perf_counter() - start_time
                DB_QUERY_LATENCY.labels(operation=operation).observe(duration)
        return wrapper
    return decorator


def track_redis_operation(operation: str):
    """Decorator to track Redis operation metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start_time
                REDIS_OPERATIONS.labels(operation=operation, status=status).inc()
                REDIS_LATENCY.labels(operation=operation).observe(duration)
        return wrapper
    return decorator


# =============================================================================
# Setup function
# =============================================================================

def setup_metrics(environment: str = "development"):
    """Setup metrics with environment info."""
    APP_INFO.info({
        "version": "1.13.0",
        "environment": environment,
    })
