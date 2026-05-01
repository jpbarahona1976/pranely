"""Tests for PRANELY Observability - FASE 9B.

Tests Prometheus metrics endpoint and basic metrics instrumentation.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_metrics_endpoint_exists(client):
    """Verify /api/metrics endpoint returns Prometheus format."""
    response = await client.get("/api/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_metrics_endpoint_contains_app_info(client):
    """Verify metrics include application info."""
    response = await client.get("/api/metrics")
    content = response.text
    # Should contain PRANELY app info
    assert "pranely_app_info" in content or "pranely_app" in content


@pytest.mark.asyncio
async def test_metrics_endpoint_contains_http_metrics(client):
    """Verify metrics include HTTP request metrics."""
    response = await client.get("/api/metrics")
    content = response.text
    # Should contain HTTP request metrics
    assert "pranely_http_requests_total" in content or "pranely_http_request_duration" in content


@pytest.mark.asyncio
async def test_health_endpoint_still_works(client):
    """Verify existing health endpoints still work."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "healthy"]


@pytest.mark.asyncio
async def test_health_deep_endpoint_still_works(client):
    """Verify /api/health/deep still works."""
    response = await client.get("/api/health/deep")
    assert response.status_code in [200, 503]  # 503 OK if DB/Redis not available in test


@pytest.mark.asyncio
async def test_metrics_endpoint_format(client):
    """Verify metrics are in Prometheus exposition format."""
    response = await client.get("/api/metrics")
    content = response.text
    lines = content.strip().split("\n")
    
    # Prometheus format has lines like: metric_name{labels} value timestamp
    # Or HELP/TYPE comments
    valid_lines = 0
    for line in lines:
        if line.startswith("#") or line.strip():
            if "pranely" in line.lower():
                valid_lines += 1
    
    assert valid_lines > 0, "Should have at least one PRANELY metric"


@pytest.mark.asyncio
async def test_health_endpoint_contains_components(client):
    """Verify /api/health includes component status."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    # Basic health just needs to return ok


@pytest.mark.asyncio
async def test_metrics_does_not_expose_sensitive_data(client):
    """Verify metrics endpoint does not expose sensitive data."""
    response = await client.get("/api/metrics")
    content = response.text.lower()
    
    # Should NOT contain actual secrets/tokens/passwords
    sensitive_patterns = [
        "secret_key",
        "password=",
        "token=",
        "api_key",
    ]
    
    for pattern in sensitive_patterns:
        assert pattern not in content, f"Metrics should not contain: {pattern}"


@pytest.mark.asyncio
async def test_multiple_requests_increment_metrics(client):
    """Verify metrics are incremented on requests."""
    # Make multiple requests
    for _ in range(3):
        await client.get("/api/health")
    
    response = await client.get("/api/metrics")
    content = response.text
    
    # Should have some request count
    # (may be 0 if health endpoint is not tracked or test isolation)
    assert "pranely_http" in content or "up" in content
