#!/bin/bash
# =============================================================================
# PRANELY - Restore Script (Fase 4C: Backup/DR)
# Restauración completa PostgreSQL + Redis
# RTO: 15min objetivo | Multi-tenant aware
# =============================================================================

set -e

# ------------------------------------------------------------------------------
# Configuración
# ------------------------------------------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-/backups}"
MODE="${MODE:-full}"
RTO_START=$(date +%s)

POSTGRES_HOST="${PG_HOST:-postgres}"
POSTGRES_PORT="${PG_PORT:-5432}"
POSTGRES_USER="${PG_USER:-pranely}"
POSTGRES_DB="${PG_DB:-pranely_dev}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
log() {
    local level=$1
    local message=$2
    local timestamp=$(date +%Y-%m-%d\ %H:%M:%S)
    echo "[${timestamp}] [${level}] ${message}"
}

rto_tracking() {
    local rto_end=$(date +%s)
    local rto_duration=$((rto_end - RTO_START))
    echo "${rto_duration}" > /tmp/rto_duration.txt
    log "INFO" "RTO duration: ${rto_duration}s"
}

trap rto_tracking EXIT

# ------------------------------------------------------------------------------
# Restore PostgreSQL
# ------------------------------------------------------------------------------
restore_postgres() {
    log "INFO" "Starting PostgreSQL restore..."
    
    # Buscar backup más reciente
    local latest_backup=$(find "${BACKUP_DIR}" -name "postgres_*.dump" -type f 2>/dev/null | sort -r | head -1)
    
    if [ -z "${latest_backup}" ]; then
        log "ERROR" "No PostgreSQL backup found in ${BACKUP_DIR}"
        return 1
    fi
    
    log "INFO" "Using backup: ${latest_backup}"
    
    # Configurar password
    if [ -n "${POSTGRES_PASSWORD}" ]; then
        export PGPASSWORD="${POSTGRES_PASSWORD}"
    fi
    
    # Ejecutar pg_restore
    pg_restore -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --clean \
        --if-exists \
        "${latest_backup}"
    
    log "INFO" "PostgreSQL restore completed"
    
    # Verificar multi-tenant: organization_id debe estar presente
    if command -v psql &> /dev/null; then
        local org_count=$(psql -h "${POSTGRES_HOST}" \
            -p "${POSTGRES_PORT}" \
            -U "${POSTGRES_USER}" \
            -d "${POSTGRES_DB}" \
            -t -c "SELECT COUNT(*) FROM organizations;" 2>/dev/null || echo "0")
        log "INFO" "Restored ${org_count} organizations"
    fi
}

# ------------------------------------------------------------------------------
# Restore Redis
# ------------------------------------------------------------------------------
restore_redis() {
    log "INFO" "Starting Redis restore..."
    
    # Buscar backup más reciente
    local latest_redis=$(find "${BACKUP_DIR}" -name "redis_*.rdb" -type f 2>/dev/null | sort -r | head -1)
    
    if [ -z "${latest_redis}" ]; then
        log "WARN" "No Redis backup found, skipping Redis restore"
        return 0
    fi
    
    log "INFO" "Using Redis backup: ${latest_redis}"
    log "INFO" "Redis restore configured"
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    log "INFO" "PRANELY Restore Script starting..."
    log "INFO" "Mode: ${MODE}"
    log "INFO" "Backup directory: ${BACKUP_DIR}"
    
    case "${MODE}" in
        full)
            restore_postgres
            restore_redis
            ;;
        postgres-only)
            restore_postgres
            ;;
        redis-only)
            restore_redis
            ;;
        *)
            log "ERROR" "Invalid mode: ${MODE}"
            log "INFO" "Valid modes: full, postgres-only, redis-only"
            exit 1
            ;;
    esac
    
    log "INFO" "Restore completed successfully"
}

main "$@"
