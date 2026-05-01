"""PRANELY Observability Middleware.

FASE 9B: Middleware for automatic request metrics instrumentation.
"""
import time
from starlette.types import ASGIApp, Receive, Scope, Send
from app.observability.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    REQUEST_IN_PROGRESS,
    ERROR_COUNT,
    get_org_id,
    get_endpoint_path,
)


class MetricsMiddleware:
    """ASGI middleware for automatic Prometheus metrics."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/unknown")
        
        # Normalize path for metrics
        normalized_path = self._normalize_path(path)
        
        # Get org_id from headers/state if available
        org_id = "unknown"
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"x-org-id":
                org_id = header_value.decode()
                break

        REQUEST_IN_PROGRESS.labels(method=method, endpoint=normalized_path).inc()
        
        start_time = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            ERROR_COUNT.labels(
                error_type=type(e).__name__,
                endpoint=normalized_path,
                org_id=org_id
            ).inc()
            raise
        finally:
            duration = time.perf_counter() - start_time
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=normalized_path).dec()
            
            REQUEST_COUNT.labels(
                method=method,
                endpoint=normalized_path,
                status_code=status_code,
                org_id=org_id
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=normalized_path,
                org_id=org_id
            ).observe(duration)

    def _normalize_path(self, path: str) -> str:
        """Normalize path to avoid high cardinality."""
        parts = path.split("/")
        normalized = []
        for part in parts:
            if part.isdigit():
                normalized.append("{id}")
            elif part and all(c in "0123456789abcdef" for c in part.lower()) and len(part) >= 8:
                # Likely a UUID
                normalized.append("{uuid}")
            else:
                normalized.append(part)
        return "/".join(normalized)
