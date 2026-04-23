#!/bin/bash
# =============================================================================
# PRANELY - Restore Script (Fase 4C: Backup/DR)
# Restauración completa PostgreSQL + Redis
# RTO: 15min objetivo
# =============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Configuración
# ------------------------------------------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="${TIMESTAMP:-latest}"
MODE="${MODE:-full}"  # full | postgres-only | redis-only

# PostgreSQL
PG_HOST="${PG_HOST:-postgres}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-pranely}"
PG_DB="${PG_DB:-pranely_dev}"
PG_DROP_DB="${PG_DROP_DB:-true}"
PG_CONTAINER="${PG_CONTAINER:-pranely-postgres}"

# Redis
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_CONTAINER="${REDIS_CONTAINER:-pranely-redis}"

# Logging
LOG_FILE="${BACKUP_DIR}/logs/restore_$(date +%Y%m%d_%H%M%S).log"
RTO_START=""

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

get_latest_backup() {
    local type="$1"
    local latest_file=""

    case "$type" in
        postgres)
            latest_file=$(ls -t "${BACKUP_DIR}"/*/*.dump 2>/dev/null | head -1)
            ;;
        redis)
            latest_file=$(ls -t "${BACKUP_DIR}"/*/*.rdb 2>/dev/null | head -1)
            ;;
    esac

    if [ -z "${latest_file}" ] || [ ! -f "${latest_file}" ]; then
        log "ERROR" "No se encontró backup ${type} en ${BACKUP_DIR}"
        return 1
    fi

    echo "${latest_file}"
}

wait_postgres_ready() {
    log "INFO" "Esperando PostgreSQL listo..."

    local retries=30
    while [ $retries -gt 0 ]; do
        if PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_isready -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" &>/dev/null; then
            log "INFO" "PostgreSQL listo."
            return 0
        fi
        sleep 2
        retries=$((retries - 1))
    done

    log "ERROR" "PostgreSQL no disponible después de 60s."
    return 1
}

wait_redis_ready() {
    log "INFO" "Esperando Redis listo..."

    local retries=30
    while [ $retries -gt 0 ]; do
        if redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" PING 2>/dev/null | grep -q "PONG"; then
            log "INFO" "Redis listo."
            return 0
        fi
        sleep 2
        retries=$((retries - 1))
    done

    log "ERROR" "Redis no disponible después de 60s."
    return 1
}

# ------------------------------------------------------------------------------
# Restauración PostgreSQL
# ------------------------------------------------------------------------------
restore_postgres() {
    local backup_file="$1"
    log "INFO" "Iniciando restauración PostgreSQL desde: ${backup_file}"

    if [ ! -f "${backup_file}" ]; then
        log "ERROR" "Archivo de backup no existe: ${backup_file}"
        return 1
    fi

    local start_time=$(date +%s)

    # Cerrar conexiones existentes (opcional pero recomendado)
    log "INFO" "Terminando conexiones existentes..."
    PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${PG_DB}' AND pid <> pg_backend_pid();" \
        2>/dev/null || true

    # Drop y recreate DB si está vacío o si se solicita
    if [ "${PG_DROP_DB}" = "true" ]; then
        log "INFO" "Recreando base de datos..."
        PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres \
            -c "DROP DATABASE IF EXISTS ${PG_DB};" 2>/dev/null || true
        PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres \
            -c "CREATE DATABASE ${PG_DB};"
    fi

    # Restaurar desde backup
    log "INFO" "Restaurando backup (esto puede tomar varios minutos)..."
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_restore \
        -h "${PG_HOST}" \
        -p "${PG_PORT}" \
        -U "${PG_USER}" \
        -d "${PG_DB}" \
        --clean \
        --if-exists \
        --verbose \
        "${backup_file}" 2>&1 | tee -a "$LOG_FILE"

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Verificar restauración
    local table_count=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
        -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';" 2>/dev/null | tr -d ' ')

    if [ -z "${table_count}" ] || [ "${table_count}" -eq 0 ]; then
        log "ERROR" "Restauración PostgreSQL falló - no se encontraron tablas."
        return 1
    fi

    log "INFO" "PostgreSQL restaurado exitosamente. Tablas: ${table_count}, Tiempo: ${duration}s"
    return 0
}

# ------------------------------------------------------------------------------
# Restauración Redis
# ------------------------------------------------------------------------------
restore_redis() {
    local backup_file="$1"
    log "INFO" "Iniciando restauración Redis desde: ${backup_file}"

    if [ ! -f "${backup_file}" ]; then
        log "ERROR" "Archivo de backup no existe: ${backup_file}"
        return 1
    fi

    local start_time=$(date +%s)

    # Detener Redis para poder copiar el archivo
    log "INFO" "Deteniendo Redis temporalmente..."
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" SHUTDOWN NOSAVE 2>/dev/null || true
    sleep 2

    # Obtener directorio de Redis
    local redis_dir="${BACKUP_DIR}/redis_temp"
    mkdir -p "${redis_dir}"

    # Copiar backup
    cp "${backup_file}" "${redis_dir}/dump.rdb"

    # Obtener la ruta del contenedor Redis
    local rdb_dest=""
    case "${REDIS_HOST}" in
        redis)
            # Dentro de docker, el dump.rdb está en /data
            rdb_dest="redis_data:/data/dump.rdb"
            ;;
        localhost|127.0.0.1)
            rdb_dest="${redis_dir}/dump.rdb"
            ;;
        *)
            rdb_dest="${redis_dir}/dump.rdb"
            ;;
    esac

    log "INFO" "Copiando dump.rdb a destino..."
    if [[ "${REDIS_HOST}" == "redis" ]]; then
        # Usar docker cp para copiar al contenedor (usar variable parametrizada)
        docker cp "${redis_dir}/dump.rdb" "${REDIS_CONTAINER}:/data/dump.rdb" 2>/dev/null || {
            log "WARN" "No se pudo usar docker cp, intentando otra forma..."
            rdb_dest="${redis_dir}/dump.rdb"
        }
    fi

    # Reiniciar Redis (usar variable parametrizada)
    log "INFO" "Reiniciando Redis..."
    docker restart "${REDIS_CONTAINER}" 2>/dev/null || docker start "${REDIS_CONTAINER}" 2>/dev/null || true
    sleep 3

    wait_redis_ready

    # Verificar
    local redis_test=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" PING 2>/dev/null)
    if [ "${redis_test}" != "PONG" ]; then
        log "ERROR" "Redis no responde después de restore."
        return 1
    fi

    # Contar keys
    local key_count=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" DBSIZE 2>/dev/null | awk '{print $2}')
    log "INFO" "Redis restaurado. Keys: ${key_count:-unknown}"

    # Cleanup temp
    rm -rf "${redis_dir}"

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log "INFO" "Redis restaurado en ${duration}s"

    return 0
}

# ------------------------------------------------------------------------------
# Verificación post-restore
# ------------------------------------------------------------------------------
verify_restore() {
    log "INFO" "Verificando restauración completa..."

    # 1. PostgreSQL: verificar tablas multi-tenant
    local org_check=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
        -c "SELECT COUNT(*) FROM organizations;" 2>/dev/null | tr -d ' ')
    log "INFO" "Organizations: ${org_check}"

    local users_check=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
        -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
    log "INFO" "Users: ${users_check}"

    # 2. Redis: verificar cola RQ
    local queues=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" LLEN default 2>/dev/null | tr -d ' ')
    log "INFO" "RQ Queue (default): ${queues}"

    log "INFO" "Verificación post-restore completada."
    return 0
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    RTO_START=$(date +%s)

    log "INFO" "=============================================="
    log "INFO" "PRANELY Restore Script - $(date)"
    log "INFO" "Modo: ${MODE}"
    log "INFO" "=============================================="

    mkdir -p "${BACKUP_DIR}/logs"

    case "${MODE}" in
        postgres-only)
            wait_postgres_ready || exit 1
            local pg_backup=$(get_latest_backup "postgres")
            restore_postgres "${pg_backup}" || exit 1
            ;;
        redis-only)
            wait_redis_ready || exit 1
            local redis_backup=$(get_latest_backup "redis")
            restore_redis "${redis_backup}" || exit 1
            ;;
        full|*)
            wait_postgres_ready || exit 1
            wait_redis_ready || exit 1

            local pg_backup=$(get_latest_backup "postgres")
            restore_postgres "${pg_backup}" || exit 1

            local redis_backup=$(get_latest_backup "redis")
            restore_redis "${redis_backup}" || exit 1

            verify_restore
            ;;
    esac

    local RTO_END=$(date +%s)
    local RTO_DURATION=$((RTO_END - RTO_START))

    log "INFO" "=============================================="
    log "INFO" "RESTORE COMPLETADO"
    log "INFO" "RTO: ${RTO_DURATION}s"
    log "INFO" "=============================================="

    # Verificar RTO < 15min (900s)
    if [ ${RTO_DURATION} -gt 900 ]; then
        log "WARN" "RTO excedió el objetivo de 15min: ${RTO_DURATION}s"
        exit 1
    fi

    log "INFO" "RTO dentro del objetivo (<15min)."

    # Escribir RTO real para simulacro-dr.sh
    echo "${RTO_DURATION}" > /tmp/rto_duration.txt

    exit 0
}

# Solo ejecutar si se llama directamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
