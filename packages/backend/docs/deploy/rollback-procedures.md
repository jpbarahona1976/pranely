# PRANELY - Procedimientos Rollback

**Versión:** 1.0  
**Fecha:** 2026-04-23  
**Estado:** Aprobado  
**Owner:** DevOps Lead  
**Fase:** 2C

---

## 1. Resumen Ejecutivo

Documento de procedimientos para rollback de deployments en PRANELY. Define triggers,流程, y scripts para recuperación rápida ante fallos.

**MTTR objetivo:** < 15 minutos  
**RTO objetivo:** < 15 minutos

---

## 2. Triggers de Rollback

### 2.1 Rollback Automático

Ejecutar rollback automático si:

| Condición | Threshold | Timeout |
|-----------|-----------|---------|
| Healthchecks fallan | 3 retries | 60s |
| API Latency p95 | > 2000ms | 5min |
| Error rate 5xx | > 1% | 5min |
| Tenant isolation | cualquier fallo | inmediato |
| Service unavailable | cualquier | inmediato |

### 2.2 Rollback Manual

Ejecutar rollback manual si:

- Logs muestran errores críticos recurrentes
- Smoke tests fallan después de 3 intentos
- Alertas de Prometheus activas por > 10min
- On-call decide rollback por cualquier razón

### 2.3 No Rollback (Investigar)

No ejecutar rollback si:

- Solo warnings en logs (no errors)
- Latencia elevada pero servicio funcional
- Errors aislados en requests no críticos

---

## 3. Niveles de Rollback

### 3.1 Nivel 1: Contenedor Restart

**Cuándo:** Servicio caído, no hay cambios de código  
**Impacto:** < 1 minuto, sin pérdida de requests

```bash
# Script: rollback-l1.sh
docker compose restart backend
sleep 10
curl -f http://localhost:8000/api/health || exit 1
```

### 3.2 Nivel 2: Imagen Anterior

**Cuándo:** Nuevo build falla healthchecks  
**Impacto:** < 5 minutos, servicio vuelve a versión anterior

```bash
# Script: rollback-l2.sh
# Obtener tag anterior
PREV_TAG=$(docker images pranely-backend:dev --format "{{.CreatedAt}}" | head -2 | tail -1)
# Deploy versión anterior
docker pull pranely-backend:$PREV_TAG
docker compose up -d backend
# Verificar
sleep 30
curl -f http://localhost:8000/api/health/deep || exit 1
```

### 3.3 Nivel 3: Blue-Green Full

**Cuándo:** Green environment completamente roto  
**Impacto:** < 15 minutos, tráfico vuelve a Blue

```bash
# Script: rollback-l3.sh (blue-green)
# 1. Detener green
docker compose -f docker-compose.prod.yml stop backend-green

# 2. Asegurar blue corriendo
docker compose -f docker-compose.prod.yml start backend-blue

# 3. Verificar blue healthy
sleep 15
curl -f http://localhost:8000/api/health/deep || exit 1

# 4. Notificar equipo
curl -X POST $SLACK_WEBHOOK -d "Rollback L3 ejecutado. Blue activo."
```

---

## 4. Flujo de Rollback

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROLLBACK FLOW                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [ALERTA/INCIDENTE DETECTADO]                                  │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                          │
│  │ Evaluar impacto │                                          │
│  └────────┬────────┘                                          │
│           │                                                     │
│     ┌─────┴─────┐                                              │
│     ▼           ▼                                              │
│  CRÍTICO    NO CRÍTICO                                          │
│     │           │                                              │
│     ▼           ▼                                              │
│  ROLLBACK   INVESTIGAR                                         │
│  INMEDIATO   + MONITOR                                          │
│     │           │                                              │
│     ▼           ▼                                              │
│  ┌─────────────────────────────┐                               │
│  │      SELECCIONAR NIVEL      │                               │
│  │   L1/L2/L3 según impacto    │                               │
│  └──────────────┬──────────────┘                               │
│                 │                                              │
│                 ▼                                              │
│  ┌─────────────────────────────┐                               │
│  │      EJECUTAR ROLLBACK       │                               │
│  │   Script correspondiente      │                               │
│  └──────────────┬──────────────┘                               │
│                 │                                              │
│                 ▼                                              │
│  ┌─────────────────────────────┐                               │
│  │      VERIFICAR SERVICE       │                               │
│  │   Healthchecks + Smoke       │                               │
│  └──────────────┬──────────────┘                               │
│                 │                                              │
│          ┌─────┴─────┐                                         │
│          ▼           ▼                                         │
│       OK           FAIL                                         │
│          │           │                                         │
│          ▼           ▼                                         │
│     MONITOR       ESCALAR                                      │
│     + POSTMORTEM  + ON-CALL                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Scripts Rollback

### 5.1 Script Principal: `rollback.sh`

```bash
#!/bin/bash
# rollback.sh - Rollback automático multinivel

set -e

LEVEL="${1:-2}"
ENV="${2:-staging}"

echo "=== PRANELY Rollback ==="
echo "Level: $LEVEL"
echo "Env: $ENV"

case $LEVEL in
  1)
    echo "[L1] Restart container..."
    docker compose -f docker-compose.$ENV.yml restart backend
    sleep 10
    curl -f http://localhost:8000/api/health && echo "OK" || exit 1
    ;;
  2)
    echo "[L2] Deploy imagen anterior..."
    # Get previous image tag
    PREV_TAG=$(git describe --tags --abbrev=0)
    docker pull pranely-backend:$PREV_TAG
    docker tag pranely-backend:$PREV_TAG pranely-backend:rollback
    docker compose -f docker-compose.$ENV.yml up -d backend
    sleep 30
    python3 scripts/smoke-test.sh --env $ENV || exit 1
    ;;
  3)
    echo "[L3] Blue-green full rollback..."
    docker compose -f docker-compose.prod.yml stop backend-green
    docker compose -f docker-compose.prod.yml start backend-blue
    sleep 15
    curl -f http://localhost:8000/api/health/deep || exit 1
    ;;
  *)
    echo "Nivel inválido: 1, 2, o 3"
    exit 1
    ;;
esac

echo "=== Rollback Level $LEVEL completado ==="
```

### 5.2 Script Smoke Post-Rollback

```bash
#!/bin/bash
# smoke-after-rollback.sh

set -e

echo "=== Smoke Tests Post-Rollback ==="

# 1. Basic health
curl -f http://localhost:8000/api/health || { echo "FAIL: Basic health"; exit 1; }
echo "Basic health: OK"

# 2. DB health
curl -f http://localhost:8000/api/health/db || { echo "FAIL: DB health"; exit 1; }
echo "DB health: OK"

# 3. Redis health
curl -f http://localhost:8000/api/health/redis || { echo "FAIL: Redis health"; exit 1; }
echo "Redis health: OK"

# 4. Auth
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@pranely.test&password=admin123" \
  | jq -r '.access_token')
  
[ -z "$TOKEN" ] && { echo "FAIL: Auth"; exit 1; }
echo "Auth: OK"

# 5. CRUD test
curl -f -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/employers \
  | grep -q "data" && echo "CRUD: OK" || { echo "FAIL: CRUD"; exit 1; }

echo "=== Todos los smoke tests pasaron ==="
```

---

## 6. Rollback por Tipo de Incidente

### 6.1 Database Issue

```bash
# Si DB no conecta post-deploy
# 1. Verificar estado DB
docker compose ps postgres
docker exec pranely-postgres pg_isready -U pranely

# 2. Si DB caído: restart PostgreSQL
docker compose restart postgres

# 3. Verificar conexión backend
curl -f http://localhost:8000/api/health/db

# 4. Si sigue fallando: rollback nivel 2
./rollback.sh 2 staging
```

### 6.2 Redis Issue

```bash
# Si Redis no conecta
# 1. Verificar estado Redis
docker compose ps redis
docker exec pranely-redis redis-cli ping

# 2. Si Redis caído: restart
docker compose restart redis

# 3. Verificar backend re-conecta
curl -f http://localhost:8000/api/health/redis

# 4. Si sigue fallando: rollback nivel 1 (restart backend)
./rollback.sh 1 staging
```

### 6.3 Code/Build Issue

```bash
# Si nuevo código tiene bugs
# 1. Identificar versión buena
git log --oneline -10

# 2. Rollback nivel 2
./rollback.sh 2 staging

# 3. Verificar con smoke
./smoke-after-rollback.sh
```

### 6.4 Security Issue

```bash
# Si se detecta breach/vulnerabilidad
# 1. Rollback inmediato nivel 3
./rollback.sh 3 staging

# 2. Notificar inmediatamente
curl -X POST $SLACK_WEBHOOK -d "ALERTA: Security rollback ejecutado"

# 3. Investigar y parchear
# NO hacer deploy hasta resolver
```

---

## 7. Comunicación Durante Rollback

### 7.1 Slack Notification

```bash
# Notificar inicio rollback
curl -X POST $SLACK_WEBHOOK \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "🔴 INICIANDO ROLLBACK PRANELY",
    "attachments": [{
      "color": "danger",
      "fields": [
        {"title": "Nivel", "value": "L'$LEVEL'", "short": true},
        {"title": "Ambiente", "value": "'$ENV'", "short": true},
        {"title": "Hora", "value": "'$(date -u)'", "short": true}
      ]
    }]
  }'

# Notificar fin rollback
curl -X POST $SLACK_WEBHOOK \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "🟢 ROLLBACK COMPLETADO PRANELY",
    "attachments": [{
      "color": "good",
      "fields": [
        {"title": "Status", "value": "Servicio restaurado", "short": true},
        {"title": "Próximo paso", "value": "Investigación post-mortem", "short": true}
      ]
    }]
  }'
```

### 7.2 On-Call Escalation

Si rollback falla después de 2 intentos:

1. Notificar DevOps Lead directamente (teléfono)
2. Crear incident en PagerDuty
3. Escalar a Engineering Manager si > 30 min

---

## 8. Post-Rollback Actions

### 8.1 Checklist Post-Rollback

- [ ] Servicio restaurado y verified
- [ ] Monitoreando 30 min post-rollback
- [ ] Notificación a stakeholders enviada
- [ ] Post-mortem creado (dentro de 24h)
- [ ] Causa raíz identificada
- [ ] Fix planificado

### 8.2 Post-Mortem Template

```markdown
# Post-Mortem: Rollback [FECHA]

## Resumen
- Incident start: [TIME]
- Root cause: [CAUSE]
- Resolution: [HOW]
- Duration: [MINUTES]

## Timeline
- [HH:MM] Detección
- [HH:MM] Rollback iniciado
- [HH:MM] Servicio restaurado

## Impacto
- Usuarios afectados: [N]
- Requests fallidos: [N]
- Revenue impact: [USD]

## Causa Raíz
[EXPLICACIÓN]

## Lessons Learned
[APRENDIZAJES]

## Action Items
- [ ] [TODO]
- [ ] [TODO]
```

---

## 9. Prevención

### 9.1 Prácticas Preventivas

1. **Smoke tests obligatorios** antes de deploy
2. **Canary deployment**: 5% tráfico inicial
3. **Feature flags**: disable features sin rollback
4. **Database migrations**: backward compatible
5. **Healthchecks**: cubriendo todos los componentes
6. **Monitoreo proactivo**: alerts antes de incidentes

### 9.2 Pre-Deploy Checklist Actualizado

- [ ] Canary test (1% tráfico) por 10 min
- [ ] Baseline metrics grabadas
- [ ] Rollback script probado en staging
- [ ] On-call disponible durante deploy
- [ ] Communication plan listo

---

## 10. Links Rápidos

- [Runbook Deploy](./runbook-deploy.md)
- [Healthchecks](./healthchecks.md)
- [Release Cadence](./release-cadence.md)

---

**Última actualización:** 2026-04-23  
**Owner:** DevOps Lead