#!/bin/bash
# deploy-staging.sh - Deploy automatizado staging
# PRANELY Phase 2C

set -e

STAGING_TAG="${1:-latest}"
HEALTH_TIMEOUT=60
SMOKE_TIMEOUT=120

echo "=== PRANELY Staging Deploy ==="
echo "Tag: $STAGING_TAG"
echo "Hora: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Pull nueva imagen
log_info "[1/8] Pull imagen $STAGING_TAG..."
if docker pull pranely-backend:$STAGING_TAG; then
    log_info "Imagen descargada OK"
else
    log_error "Fallo al descargar imagen"
    exit 1
fi

# 2. Verificar backup
log_info "[2/8] Verificar backup..."
# TODO: Implementar backup pre-deploy
log_info "Backup: Saltado (pending implementation)"

# 3. Deploy green (nuevo)
log_info "[3/8] Deploy green container..."
if docker compose -f docker-compose.staging.yml up -d backend-green; then
    log_info "Green container desplegado OK"
else
    log_error "Fallo al desplegar green container"
    exit 1
fi

# 4. Healthcheck profundo
log_info "[4/8] Healthchecks profundos..."
MAX_RETRIES=5
RETRY_INTERVAL=10

for i in $(seq 1 $MAX_RETRIES); do
    echo "Intento $i/$MAX_RETRIES..."
    
    # Basic health
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        log_info "Basic health: OK"
        break
    fi
    
    if [ $i -eq $MAX_RETRIES ]; then
        log_error "Basic healthcheck falló después de $MAX_RETRIES intentos"
        exit 1
    fi
    
    sleep $RETRY_INTERVAL
done

# Deep health checks
if curl -sf http://localhost:8000/api/health/db > /dev/null 2>&1; then
    log_info "DB health: OK"
else
    log_warn "DB health: Falló (continuando...)"
fi

if curl -sf http://localhost:8000/api/health/redis > /dev/null 2>&1; then
    log_info "Redis health: OK"
else
    log_warn "Redis health: Falló (continuando...)"
fi

# 5. Smoke tests
log_info "[5/8] Smoke tests..."
SMOKE_RETRIES=3

for i in $(seq 1 $SMOKE_RETRIES); do
    echo "Smoke test intento $i/$SMOKE_RETRIES..."
    
    if python3 scripts/smoke-test.sh --env staging --timeout $SMOKE_TIMEOUT; then
        log_info "Smoke tests: OK"
        break
    fi
    
    if [ $i -eq $SMOKE_RETRIES ]; then
        log_error "Smoke tests fallaron después de $SMOKE_RETRIES intentos"
        exit 1
    fi
    
    sleep 10
done

# 6. Verificar tenant isolation
log_info "[6/8] Tenant isolation check..."
if curl -sf http://localhost:8000/api/health/tenant | grep -q "verified"; then
    log_info "Tenant isolation: OK"
else
    log_error "Tenant isolation: Falló"
    exit 1
fi

# 7. Monitorizar 5 min
log_info "[7/8] Monitorizando 5 minutos..."
for i in $(seq 1 30); do
    echo -ne "Minuto $((i * 10))s...\r"
    sleep 10
    
    # Check if still healthy
    if ! curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        log_error "Servicio cayó durante monitorización"
        exit 1
    fi
done
echo ""

# 8. Verificar logs
log_info "[8/8] Verificando errores en logs..."
ERRORS=$(docker compose -f docker-compose.staging.yml logs --tail=100 backend | grep -i error || true)
if [ -n "$ERRORS" ]; then
    log_warn "Errores encontrados en logs:"
    echo "$ERRORS"
    log_warn "Continuando (errores pueden ser benignos)"
else
    log_info "Sin errores críticos en logs"
fi

log_info ""
log_info "=== Deploy staging COMPLETADO ==="
log_info "Hora: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"