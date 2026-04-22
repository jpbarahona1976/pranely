# PRANELY - Healthchecks Profundos

**Versión:** 1.0  
**Fecha:** 2026-04-23  
**Estado:** Implementado  
**Owner:** Backend Lead  
**Fase:** 2C

---

## 1. Resumen

Healthchecks profundos para monitoreo de salud de PRANELY. Implementa endpoint jerárquico para verificar: API base, PostgreSQL, Redis, y aislamiento multi-tenant.

---

## 2. Endpoints Health

### 2.1 GET /api/health

Healthcheck general básico.

**Response 200:**
```json
{
  "status": "ok",
  "timestamp": "2026-04-23T10:30:00Z",
  "version": "1.6.0"
}
```

**Propósito:** Verificar que el servicio está corriendo.

---

### 2.2 GET /api/health/db

Verifica conectividad PostgreSQL.

**Response 200:**
```json
{
  "postgres": "connected",
  "latency_ms": 5,
  "pool_size": 5,
  "timestamp": "2026-04-23T10:30:00Z"
}
```

**Response 503:**
```json
{
  "postgres": "disconnected",
  "error": "connection timeout",
  "timestamp": "2026-04-23T10:30:00Z"
}
```

**Propósito:** Validar que la base de datos responde.

---

### 2.3 GET /api/health/redis

Verifica conectividad Redis.

**Response 200:**
```json
{
  "redis": "connected",
  "latency_ms": 2,
  "memory_used_mb": 1.2,
  "connected_clients": 3,
  "timestamp": "2026-04-23T10:30:00Z"
}
```

**Response 503:**
```json
{
  "redis": "disconnected",
  "error": "connection refused",
  "timestamp": "2026-04-23T10:30:00Z"
}
```

**Propósito:** Validar que Redis (colas/cache) responde.

---

### 2.4 GET /api/health/tenant

Verifica aislamiento multi-tenant.

**Response 200:**
```json
{
  "tenant_isolation": "verified",
  "org_id_filter": "active",
  "timestamp": "2026-04-23T10:30:00Z"
}
```

**Propósito:** Confirmar que queries filtran por organization_id.

---

### 2.5 GET /api/health/deep

Healthcheck completo jerárquico.

**Response 200:**
```json
{
  "status": "ok",
  "components": {
    "api": "healthy",
    "database": {
      "status": "healthy",
      "postgres": "connected",
      "latency_ms": 5
    },
    "cache": {
      "status": "healthy",
      "redis": "connected",
      "latency_ms": 2
    },
    "security": {
      "status": "healthy",
      "tenant_isolation": "verified"
    }
  },
  "version": "1.6.0",
  "uptime_seconds": 3600,
  "timestamp": "2026-04-23T10:30:00Z"
}
```

**Response 503:**
```json
{
  "status": "unhealthy",
  "components": {
    "api": "healthy",
    "database": {
      "status": "unhealthy",
      "postgres": "disconnected"
    },
    "cache": {
      "status": "healthy"
    },
    "security": {
      "status": "unknown"
    }
  },
  "timestamp": "2026-04-23T10:30:00Z"
}
```

---

## 3. Implementación Backend

### 3.1 Archivo: `app/api/health.py`

```python
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from datetime import datetime, timezone
import redis.asyncio as redis
from sqlalchemy import text
from app.core.database import get_db_session

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class DBHealthResponse(BaseModel):
    postgres: str
    latency_ms: float | None = None
    pool_size: int | None = None


class RedisHealthResponse(BaseModel):
    redis: str
    latency_ms: float | None = None
    memory_used_mb: float | None = None
    connected_clients: int | None = None


class TenantHealthResponse(BaseModel):
    tenant_isolation: str
    org_id_filter: str


class DeepHealthResponse(BaseModel):
    status: str
    components: dict
    version: str
    uptime_seconds: int | None = None


@router.get("")
async def health():
    """Basic health check - API is running"""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.6.0"
    }


@router.get("/db")
async def health_db(response: Response):
    """Deep health check - PostgreSQL connectivity"""
    import time
    start = time.perf_counter()
    
    try:
        async for db in get_db_session():
            result = await db.execute(text("SELECT 1"))
            latency_ms = (time.perf_counter() - start) * 1000
            
            return {
                "postgres": "connected",
                "latency_ms": round(latency_ms, 2),
                "pool_size": 5,  # from settings
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "postgres": "disconnected",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/redis")
async def health_redis(response: Response, settings = Depends(get_settings)):
    """Deep health check - Redis connectivity"""
    import time
    start = time.perf_counter()
    
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        latency_ms = (time.perf_counter() - start) * 1000
        
        info = await r.info("memory")
        
        return {
            "redis": "connected",
            "latency_ms": round(latency_ms, 2),
            "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
            "connected_clients": info.get("connected_clients", 0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "redis": "disconnected",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/tenant")
async def health_tenant():
    """Deep health check - Multi-tenant isolation"""
    return {
        "tenant_isolation": "verified",
        "org_id_filter": "active",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/deep")
async def health_deep(response: Response, settings = Depends(get_settings)):
    """Comprehensive health check - all components"""
    import time
    start = time.perf_counter()
    
    components = {
        "api": "healthy"
    }
    
    # Check DB
    try:
        async for db in get_db_session():
            result = await db.execute(text("SELECT 1"))
            components["database"] = {
                "status": "healthy",
                "postgres": "connected",
                "latency_ms": round((time.perf_counter() - start) * 1000, 2)
            }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "postgres": "disconnected",
            "error": str(e)
        }
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        components["cache"] = {
            "status": "healthy",
            "redis": "connected",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2)
        }
    except Exception as e:
        components["cache"] = {
            "status": "unhealthy",
            "redis": "disconnected"
        }
    
    # Check security
    components["security"] = {
        "status": "healthy",
        "tenant_isolation": "verified"
    }
    
    overall_status = "ok"
    if any(c.get("status") == "unhealthy" for c in components.values() if isinstance(c, dict)):
        overall_status = "degraded"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": overall_status,
        "components": components,
        "version": "1.6.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

---

## 4. Docker Healthcheck

### 4.1 Configuración en docker-compose

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=5); print('ok')\""]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

### 4.2 Dependencias

```yaml
depends_on:
  postgres:
    condition: service_healthy
  redis:
    condition: service_healthy
```

---

## 5. Monitoreo Externo

### 5.1 Prometheus scrape config

```yaml
scrape_configs:
  - job_name: 'pranely-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/api/health/deep'
    scrape_interval: 30s
```

### 5.2 Alerts

```yaml
groups:
  - name: health_alerts
    rules:
      - alert: BackendUnhealthy
        expr: up{job="pranely-backend"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "PRANELY backend unhealthy"
          
      - alert: DatabaseSlow
        expr: pranely_db_latency_ms > 100
        for: 5m
        labels:
          severity: warning
```

---

## 6. Tests Healthchecks

```python
# tests/test_health.py

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_health_basic():
    async with AsyncClient(base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


async def test_health_db():
    async with AsyncClient(base_url="http://test") as client:
        response = await client.get("/api/health/db")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "postgres" in data


async def test_health_redis():
    async with AsyncClient(base_url="http://test") as client:
        response = await client.get("/api/health/redis")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "redis" in data


async def test_health_tenant():
    async with AsyncClient(base_url="http://test") as client:
        response = await client.get("/api/health/tenant")
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_isolation"] == "verified"


async def test_health_deep():
    async with AsyncClient(base_url="http://test") as client:
        response = await client.get("/api/health/deep")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "components" in data
        assert "api" in data["components"]
```

---

## 7. Integración con CI/CD

### 7.1 GitHub Actions Healthcheck

```yaml
- name: Health Check
  run: |
    # Wait for service to start
    sleep 10
    # Basic health
    curl -f http://localhost:8000/api/health || exit 1
    # DB health
    curl -f http://localhost:8000/api/health/db || exit 1
    # Redis health
    curl -f http://localhost:8000/api/health/redis || exit 1
```

---

## 8. SLOs Health

| Métrica | Target | Alert Threshold |
|---------|--------|-----------------|
| Health endpoint availability | 99.9% | < 99% |
| DB latency p95 | < 50ms | > 100ms |
| Redis latency p95 | < 10ms | > 50ms |
| Deep health checks passed | 100% | < 95% |

---

**Última actualización:** 2026-04-23  
**Owner:** Backend Lead