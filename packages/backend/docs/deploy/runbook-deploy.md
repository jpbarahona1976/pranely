# PRANELY - Runbook Deploy Staging/Production

**Versión:** 1.0  
**Fecha:** 2026-04-23  
**Estado:** Aprobado  
**Owner:** DevOps Lead  
**Fase:** 2C

---

## 1. Resumen Ejecutivo

Este runbook documenta el procedimiento estándar de despliegue para PRANELY en entornos staging y production. Usa estrategia **blue-green** con rollback automatizado y smoke tests obligatorios post-deploy.

**Cadencia:** Bi-weekly (cada 2 semanas) o ad-hoc para hotfixes críticos.

---

## 2. Estrategia Blue-Green

### 2.1 Concepto

- **Blue:** ambiente actual en producción
- **Green:** nuevo ambiente con cambios deployados
- Traffic switch: 0% Blue → 100% Green después de validación
- Rollback: revert a 100% Blue si Green falla

### 2.2 Implementación Docker

```yaml
# docker-compose.prod.yml usa tags :blue y :green
# Azul: versión actual estable
# Verde: nueva versión a validar
```

### 2.3 Flujo Despliegue

```
┌─────────────────────────────────────────────────────────────────┐
│                    BLUE-GREEN DEPLOYMENT                        │
├─────────────────────────────────────────────────────────────────┤
│ 1. Build imagen green (nueva versión)                           │
│ 2. Deploy green en paralelo con blue                            │
│ 3. Healthchecks green: DB + Redis + API                        │
│ 4. Smoke tests green: auth + waste CRUD + tenant isolation      │
│ 5. Switch tráfico: blue 0% → green 100%                       │
│ 6. Monitorizar 15 min                                          │
│ 7. Si OK → blue se convierte en rollback target                │
│ 8. Si FAIL → rollback a blue 100%                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Pre-Requisitos

### 3.1 checklist Pre-Deploy

- [ ] CI/CD pipeline verde (lint + tests + security)
- [ ] 2 approvals en PR (CODEOWNERS enforced)
- [ ] Changelog actualizado con versión
- [ ] Secrets no hardcoded (Fase 3A pendiente, usar env vars)
- [ ] Healthchecks profundos documentados
- [ ] Rollback plan disponible
- [ ] On-call contact list actualizada

### 3.2 Variables Requeridas

```bash
# Producción (NO hardcodear, usar GitHub Secrets)
POSTGRES_PASSWORD=<secret>
SECRET_KEY=<secret>
STRIPE_SECRET_KEY=<secret>
DEEPINFRA_API_KEY=<secret>

# Staging
ENV=staging
DEBUG=false
```

---

## 4. Procedimiento Staging Deploy

### 4.1 Script Automatizado

```bash
#!/bin/bash
# deploy-staging.sh - Deploy automatizado staging

set -e

APP_NAME="pranely"
STAGING_TAG="${1:-latest}"
HEALTH_TIMEOUT=60
SMOKE_TIMEOUT=120

echo "=== PRANELY Staging Deploy ==="
echo "Tag: $STAGING_TAG"
echo "Hora: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

# 1. Pull nueva imagen
echo "[1/8] Pull imagen $STAGING_TAG..."
docker compose -f docker-compose.staging.yml pull backend

# 2. Backup volumen (si existe data)
echo "[2/8] Verificar backup..."
# TODO: Implementar backup pre-deploy

# 3. Deploy green (nuevo)
echo "[3/8] Deploy green container..."
docker compose -f docker-compose.staging.yml up -d backend

# 4. Healthcheck profundo
echo "[4/8] Healthchecks profundos..."
python3 scripts/health-check.py --env staging --timeout $HEALTH_TIMEOUT
if [ $? -ne 0 ]; then
    echo "ERROR: Healthchecks fallaron"
    exit 1
fi

# 5. Smoke tests
echo "[5/8] Smoke tests..."
python3 scripts/smoke-test.sh --env staging --timeout $SMOKE_TIMEOUT
if [ $? -ne 0 ]; then
    echo "ERROR: Smoke tests fallaron"
    exit 1
fi

# 6. Verificar tenant isolation
echo "[6/8] Tenant isolation check..."
curl -f http://localhost:8000/api/health/tenant || exit 1

# 7. Monitorizar 5 min
echo "[7/8] Monitorizando 5 minutos..."
sleep 300

# 8. Verificar logs
echo "[8/8] Verificando errores en logs..."
docker compose -f docker-compose.staging.yml logs --tail=50 backend | grep -i error && exit 1 || echo "Sin errores críticos"

echo "=== Deploy staging COMPLETADO ==="
```

### 4.2 Pasos Manuales (Fallback)

Si el script falla:

```bash
# 1. Verificar estado servicios
docker compose -f docker-compose.staging.yml ps

# 2. Ver logs
docker compose -f docker-compose.staging.yml logs -f backend

# 3. Restart manual si necesario
docker compose -f docker-compose.staging.yml restart backend

# 4. Retry healthchecks
curl -f http://localhost:8000/api/health
curl -f http://localhost:8000/api/health/db
curl -f http://localhost:8000/api/health/redis
```

---

## 5. Procedimiento Rollback

### 5.1 Triggers Rollback

Ejecutar rollback si:
- Healthchecks fallan después de 3 retries
- Smoke tests p95 > 2s
- Errors en logs > 10/minuto
- Tenant isolation roto
- 500 errors > 1%

### 5.2 Script Rollback

```bash
#!/bin/bash
# rollback-staging.sh - Rollback a versión anterior

set -e

echo "=== PRANELY Rollback ==="
echo "Iniciando rollback a versión anterior..."

# 1. Detener versión nueva
echo "[1/3] Deteniendo versión nueva..."
docker compose -f docker-compose.staging.yml stop backend

# 2. Levantar versión anterior (blue)
echo "[2/3] Levantando versión anterior..."
docker compose -f docker-compose.staging.yml up -d backend

# 3. Verificar health
echo "[3/3] Verificando health..."
sleep 10
curl -f http://localhost:8000/api/health || exit 1

echo "=== Rollback COMPLETADO ==="
```

### 5.3 Tiempo Objetivo Rollback

- **MTTR (Mean Time To Recovery):** < 15 minutos
- **RTO (Recovery Time Objective):** < 15 minutos
- **RPO (Recovery Point Objective):** < 1 hora (backup diario)

---

## 6. Smoke Tests Post-Deploy

### 6.1 Tests Obligatorios

```bash
# Auth smoke
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123" \
  | grep -q "access_token" && echo "AUTH: OK"

# CRUD smoke
curl -f http://localhost:8000/api/employers \
  -H "Authorization: Bearer $TOKEN" \
  | grep -q "data" && echo "CRUD: OK"

# Health deep
curl -f http://localhost:8000/api/health/db
curl -f http://localhost:8000/api/health/redis
curl -f http://localhost:8000/api/health/tenant

# Tenant isolation
# Crear org1 y org2, verificar no cruzan datos
```

### 6.2 Criterios Aprobación

| Test | Criterio | Timeout |
|------|----------|---------|
| Health /api/health | 200 OK | 5s |
| Health /api/health/db | postgres connected | 10s |
| Health /api/health/redis | redis connected | 10s |
| Auth login | 200 + token | 30s |
| CRUD employers | 200 + data array | 30s |
| Tenant isolation | 0 cross-org data | 30s |

---

## 7. Monitoreo Post-Deploy

### 7.1 Métricas Clave

- **Uptime:** > 99.5%
- **p95 latency:** < 500ms
- **Error rate:** < 0.1%
- **CPU usage:** < 80%
- **Memory usage:** < 90%

### 7.2 Alertas

```yaml
# Prometheus alerts
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
  for: 5m

- alert: HighLatency
  expr: histogram_quantile(0.95, http_request_duration_seconds) > 0.5
  for: 5m
```

### 7.3 Dashboard

Ver: `docs/deploy/-monitoring-dashboard.md`

---

## 8. On-Call Contactos

| Rol | Nombre | Slack | Teléfono |
|-----|--------|-------|----------|
| DevOps Lead | @juanbarahona | #devops | +52 XXX XXX XXXX |
| Backend Lead | @juanbarahona | #backend | +52 XXX XXX XXXX |
| On-call rotation | (team) | #alerts | +52 XXX XXX XXXX |

---

## 9. Checklist Despliegue Completo

### Pre-Deploy
- [ ] CI verde
- [ ] 2 approvals
- [ ] Changelog actualizado
- [ ] Secrets en GitHub Secrets
- [ ] Backup verificado

### Deploy
- [ ] Script ejecuta sin errores
- [ ] Healthchecks pasan
- [ ] Smoke tests pasan
- [ ] Tenant isolation verificado

### Post-Deploy
- [ ] Monitorear 15 minutos
- [ ] Verificar logs sin errores
- [ ] Notificar #deployments
- [ ] Actualizar runbook si hay incidencias

---

## 10. Links Rápidos

- [ADR-0002 Stack](./decisions/ADR-0002-STACK-ARQUITECTONICO-MVP.md)
- [Healthchecks](./healthchecks.md)
- [Rollback](./rollback-procedures.md)
- [Release Cadence](./release-cadence.md)
- [CI/CD](./.github/workflows/ci-base.yml)

---

**Última actualización:** 2026-04-23  
**Próxima revisión:** 2026-05-07