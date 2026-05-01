# PRANELY Observability Runbook
## FASE 9B: Operations Guide

**Fecha:** 30 Abril 2026  
**Fase:** 9B Observabilidad  
**Versión:** 1.0.0

---

## Quick Start

### Levantar Stack de Observabilidad

```bash
# Levantar solo observabilidad (Prometheus + Grafana)
docker compose -f docker-compose.observability.yml up -d

# Verificar que están corriendo
docker compose -f docker-compose.observability.yml ps

# Ver logs
docker compose -f docker-compose.observability.yml logs -f prometheus
docker compose -f docker-compose.observability.yml logs -f grafana
```

### Acceder a Dashboards

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| Grafana | http://localhost:3001 | admin / admin123 |
| Prometheus | http://localhost:9090 | - |

### Acceder a Métricas del Backend

```bash
# Métricas Prometheus del API
curl http://localhost:8000/api/metrics

# Health check
curl http://localhost:8000/api/health/deep
```

---

## Validación de Métricas

### Verificar que las métricas están siendo colectadas

1. Ir a Prometheus: http://localhost:9090
2. Ir a "Status" > "Targets"
3. Verificar que `pranely-backend` está "UP"
4. Ir a "Graph" y ejecutar:
   ```promql
   up{job="pranely-backend"}
   ```

### Verificar dashboards de Grafana

1. Ir a Grafana: http://localhost:3001
2. Ir a "Dashboards" > "Browse"
3. Abrir "PRANELY - API Overview"
4. Verificar que los paneles muestran datos

---

## Alertas Comunes y Troubleshooting

### 🔴 Alert: PRANELYAPIDown

**Significado:** El API no responde

**Diagnóstico:**
```bash
# Verificar que el contenedor está corriendo
docker ps | grep pranely-backend

# Ver logs del backend
docker compose logs -f backend

# Verificar health endpoint
curl http://localhost:8000/api/health
```

**Acción:**
1. Revisar logs por errores
2. Verificar PostgreSQL: `curl http://localhost:8000/api/health/db`
3. Verificar Redis: `curl http://localhost:8000/api/health/redis`
4. Reiniciar si es necesario: `docker compose restart backend`

---

### 🟡 Alert: PRANELYAPIHighLatency (p95 > 500ms)

**Significado:** Latencia elevada

**Diagnóstico:**
```promql
# Ver endpoints más lentos
topk(10, 
  histogram_quantile(0.95, 
    sum(rate(pranely_http_request_duration_seconds_bucket[5m])) by (le, endpoint)
  )
)

# Ver tendencias
rate(pranely_http_request_duration_seconds_sum[5m]) 
  / 
rate(pranely_http_request_duration_seconds_count[5m])
```

**Acción:**
1. Identificar endpoint afectado
2. Revisar logs: `docker compose logs backend | grep <endpoint>`
3. Ver queries lentas de DB
4. Considerar caching o оптимизация

---

### 🟡 Alert: PRANELYHighErrorRate (> 1%)

**Significado:** Muchos errores 5xx

**Diagnóstico:**
```promql
# Ver errores por endpoint
sum(rate(pranely_http_requests_total{status_code=~"5.."}[5m])) by (endpoint)

# Ver errores por tipo
sum(rate(pranely_errors_total[5m])) by (error_type)
```

**Acción:**
1. Identificar endpoint con errores
2. Revisar logs para el error específico
3. Verificar servicios dependientes (DB, Redis)
4. Si es cascade failure, resolver la causa raíz

---

### 🟡 Alert: PRANELYQueueBacklog (> 100 jobs)

**Significado:** Jobs acumulados en cola

**Diagnóstico:**
```promql
# Ver tamaño de cada cola
pranely_rq_queue_size

# Ver jobs fallidos
sum(rate(pranely_rq_jobs_total{status="failed"}[1h])) by (job_name)
```

**Acción:**
1. Ver workers activos: `docker compose ps | grep worker`
2. Revisar logs de workers: `docker compose logs worker`
3. Verificar Redis connectivity
4. Aumentar workers si es necesario

---

## Maintenance Tasks

### Backup de Prometheus Data

```bash
# Crear snapshot
docker compose exec prometheus prometheus tsdb snapshot /prometheus/snapshots

# Copiar a host
docker compose cp prometheus:/prometheus/snapshots ./backups/
```

### Limpieza de Métricas Antiguas

```bash
# Reducir retention a 7 días (para desarrollo)
docker compose exec prometheus prometheus tsdb delete --help

# Ver uso de disco
docker compose exec prometheus df -h /prometheus
```

### Reiniciar Prometheus sin perder métricas

```bash
# Hacer reload de config
curl -X POST http://localhost:9090/-/reload

# O reiniciar gracefully
docker compose restart prometheus
```

---

## Health Check Commands

### API Backend
```bash
# Basic
curl -s http://localhost:8000/api/health | jq .

# Deep (todos los componentes)
curl -s http://localhost:8000/api/health/deep | jq .

# Solo DB
curl -s http://localhost:8000/api/health/db | jq .

# Solo Redis
curl -s http://localhost:8000/api/health/redis | jq .
```

### Prometheus
```bash
# Targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets'

# Rules
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups'
```

### Grafana
```bash
# Health
curl -s http://localhost:3001/api/health | jq .

# Datasources
curl -s -u admin:admin123 http://localhost:3001/api/datasources | jq .
```

---

## Troubleshooting Matrix

| Symptom | Check First | Then Check |
|---------|-------------|------------|
| No metrics in Grafana | Prometheus target UP? | Backend /metrics accessible? |
| Dashboard shows "No data" | Time range correct? | Datasource configured? |
| High latency | Database queries? | External API calls? | Queue backlog? |
| High error rate | Backend logs? | Dependency health? | Rate limiting? |
| Queue stuck | Worker running? | Redis accessible? | Job errors? |

---

## Escalation Path

1. **Level 1 (0-15 min):** Check dashboards, verify components healthy
2. **Level 2 (15-30 min):** Deep dive logs, check dependencies
3. **Level 3 (30+ min):** Escalate to backend team, consider rollback

---

## Contactos

| Role | Responsibility |
|------|----------------|
| Platform Team | Infrastructure, deployment |
| Backend Team | API, workers, jobs |
| SRE | Observability, incidents |

---

## Appendix: Useful Prometheus Queries

### Request Rate
```promql
sum(rate(pranely_http_requests_total[5m]))
```

### Error Rate
```promql
sum(rate(pranely_http_requests_total{status_code=~"5.."}[5m])) 
  / 
sum(rate(pranely_http_requests_total[5m])) * 100
```

### Latency p95
```promql
histogram_quantile(0.95, 
  sum(rate(pranely_http_request_duration_seconds_bucket[5m])) by (le)
)
```

### Top 5 Slow Endpoints
```promql
topk(5, 
  histogram_quantile(0.95, 
    sum(rate(pranely_http_request_duration_seconds_bucket[1h])) by (le, endpoint)
  )
)
```

### Request by Org (multi-tenant)
```promql
sum(rate(pranely_http_requests_total[5m])) by (org_id)
```
