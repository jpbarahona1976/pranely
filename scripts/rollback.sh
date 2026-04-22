#!/bin/bash
# rollback.sh - Rollback automático multinivel
# PRANELY Phase 2C

set -e

LEVEL="${1:-2}"
ENV="${2:-staging}"

echo "=== PRANELY Rollback ==="
echo "Level: $LEVEL"
echo "Env: $ENV"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

case $LEVEL in
  1)
    log_info "[L1] Restart container..."
    docker compose -f docker-compose.$ENV.yml restart backend
    sleep 10
    curl -f http://localhost:8000/api/health && echo "OK" || exit 1
    ;;
  2)
    log_info "[L2] Deploy imagen anterior..."
    # Get previous image tag
    PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "latest")
    log_info "Using tag: $PREV_TAG"
    
    docker pull pranely-backend:$PREV_TAG 2>/dev/null || true
    docker tag pranely-backend:$PREV_TAG pranely-backend:rollback 2>/dev/null || true
    docker compose -f docker-compose.$ENV.yml up -d backend
    sleep 30
    
    python3 scripts/smoke-test.sh --env $ENV || exit 1
    ;;
  3)
    log_info "[L3] Blue-green full rollback..."
    docker compose -f docker-compose.prod.yml stop backend-green 2>/dev/null || true
    docker compose -f docker-compose.prod.yml start backend-blue
    sleep 15
    curl -f http://localhost:8000/api/health/deep || exit 1
    ;;
  *)
    echo "Nivel inválido: 1, 2, o 3"
    exit 1
    ;;
esac

echo ""
log_info "=== Rollback Level $LEVEL completado ==="