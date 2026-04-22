"""Tests for deep healthcheck endpoints."""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_health_basic(app_client: AsyncClient):
    """Test basic health endpoint."""
    response = await app_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


async def test_health_db_connected(app_client: AsyncClient):
    """Test DB health when connected."""
    response = await app_client.get("/api/health/db")
    # Should return 200 if DB connected, 503 if not
    assert response.status_code in [200, 503]
    data = response.json()
    assert "postgres" in data
    assert "timestamp" in data
    assert data["postgres"] in ["connected", "disconnected"]


async def test_health_redis_connected(app_client: AsyncClient):
    """Test Redis health when connected."""
    response = await app_client.get("/api/health/redis")
    # Should return 200 if Redis connected, 503 if not
    assert response.status_code in [200, 503]
    data = response.json()
    assert "redis" in data
    assert "timestamp" in data
    assert data["redis"] in ["connected", "disconnected"]


async def test_health_tenant(app_client: AsyncClient):
    """Test tenant isolation health check."""
    response = await app_client.get("/api/health/tenant")
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_isolation"] == "verified"
    assert data["org_id_filter"] == "active"
    assert "timestamp" in data


async def test_health_deep(app_client: AsyncClient):
    """Test comprehensive deep health check."""
    response = await app_client.get("/api/health/deep")
    # Should return 200 if all healthy, 503 if any unhealthy
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert data["status"] in ["ok", "degraded"]
    assert "components" in data
    assert "api" in data["components"]
    assert "version" in data
    assert "timestamp" in data


async def test_health_deep_includes_all_components(app_client: AsyncClient):
    """Test that deep health includes all component checks."""
    response = await app_client.get("/api/health/deep")
    data = response.json()
    
    # All expected components
    assert "api" in data["components"]
    assert "database" in data["components"]
    assert "cache" in data["components"]
    assert "security" in data["components"]


async def test_health_deep_database_status(app_client: AsyncClient):
    """Test database status in deep health."""
    response = await app_client.get("/api/health/deep")
    data = response.json()
    
    db_component = data["components"]["database"]
    assert "status" in db_component
    assert "postgres" in db_component


async def test_health_deep_cache_status(app_client: AsyncClient):
    """Test cache (Redis) status in deep health."""
    response = await app_client.get("/api/health/deep")
    data = response.json()
    
    cache_component = data["components"]["cache"]
    assert "status" in cache_component
    assert "redis" in cache_component


async def test_health_deep_security_tenant_isolation(app_client: AsyncClient):
    """Test security component includes tenant isolation."""
    response = await app_client.get("/api/health/deep")
    data = response.json()
    
    security_component = data["components"]["security"]
    assert security_component["status"] == "healthy"
    assert security_component["tenant_isolation"] == "verified"


async def test_health_timestamp_format(app_client: AsyncClient):
    """Test that timestamp follows ISO format."""
    response = await app_client.get("/api/health")
    data = response.json()
    
    from datetime import datetime
    # Should be parseable as ISO datetime
    try:
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    except ValueError:
        pytest.fail("Timestamp not in ISO format")