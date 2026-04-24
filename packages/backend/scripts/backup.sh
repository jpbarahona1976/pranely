#!/bin/bash
# =============================================================================
# PRANELY - Backup Script (Fase 4C: Backup/DR)
# PostgreSQL + Redis backup automático diario
# RPO: 1h | RTO: 15min objetivo
# =============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Configuración
# ------------------------------------------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE_DIR=$(date +%Y/%m/%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# PostgreSQL
PG_HOST="${PG_HOST:-postgres}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-pranely}"
PG_DB="${PG_DB:-pranely_dev}"
PG_BACKUP_FILE="postgres_${PG_DB}_${TIMESTAMP}.dump"

# Redis
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_CONTAINER="${REDIS_CONTAINER:-pranely-redis}"
REDIS_VOLUME_NAME="${REDIS_VOLUME_NAME:-pranely-redis-data}"
REDIS_BACKUP_FILE="redis_${TIMESTAMP}.rdb"

# Logging
LOG_FILE="${BACKUP_DIR}/logs/backup_${TIMESTAMP}.log"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

check_prereqs() {
    log "INFO" "Verificando prerrequisitos..."

    if ! command -v pg_dump &> /dev/null; then
        log "ERROR" "pg_dump no encontrado. Instalar postgresql-client."
        exit 1
    fi

    if ! command -v redis-cli &> /dev/null; then
        log "WARN" "redis-cli no encontrado. Saltando backup Redis."
        return 1
    fi

    return 0
}

init_dirs() {
    mkdir -p "${BACKUP_DIR}/${DATE_DIR}"
    mkdir -p "${BACKUP_DIR}/logs"
    mkdir -p "${BACKUP_DIR}/latest"
}

# ------------------------------------------------------------------------------
# Backup PostgreSQL
# ------------------------------------------------------------------------------
backup_postgres() {
    log "INFO" "Iniciando backup PostgreSQL..."

    local output_path="${BACKUP_DIR}/${DATE_DIR}/${PG_BACKUP_FILE}"

    # pg_dump con compresión y formato custom (permite restore selectivo)
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
        -h "${PG_HOST}" \
        -p "${PG_PORT}" \
        -U "${PG_USER}" \
        -d "${PG_DB}" \
        -Fc \
        -Z 6 \
        --verbose \
        -f "${output_path}"

    # Verificar que el backup no está vacío
    if [ ! -s "${output_path}" ]; then
        log "ERROR" "Backup PostgreSQL está vacío o falló."
        exit 1
    fi

    local file_size=$(stat -f%z "${output_path}" 2>/dev/null || stat -c%s "${output_path}" 2>/dev/null || echo "unknown")
    log "INFO" "Backup PostgreSQL completado: ${output_path} (${file_size} bytes)"

    # Crear symlink a latest
    ln -sf "../${DATE_DIR}/${PG_BACKUP_FILE}" "${BACKUP_DIR}/latest/${PG_BACKUP_FILE}"

    echo "${output_path}"
}

# ------------------------------------------------------------------------------
# Backup Redis
# ------------------------------------------------------------------------------
backup_redis() {
    log "INFO" "Iniciando backup Redis..."

    local output_path="${BACKUP_DIR}/${DATE_DIR}/${REDIS_BACKUP_FILE}"

    # Validar que el volumen de Redis esté montado (parametrizable)
    if ! docker volume ls -q 2>/dev/null | grep -q "^${REDIS_VOLUME_NAME}$"; then
        log "ERROR" "Volumen Redis ${REDIS_VOLUME_NAME} no montado. No se puede realizar backup."
        exit 1
    fi

    # Redis: forzar BGSAVE y copiar RDB
    # redis-cli BGSAVE es asíncrono, esperamos con WAIT
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" BGSAVE || {
        log "WARN" "BGSAVE falló, intentando SAVE sincrónico..."
        redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" SAVE
    }

    # Esperar a que termine el backup
    local retries=30
    while [ $retries -gt 0 ]; do
        local bgsave_status=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" LASTSAVE)
        sleep 1

        local new_status=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" LASTSAVE)
        if [ "$bgsave_status" != "$new_status" ]; then
            break
        fi
        retries=$((retries - 1))
    done

    # Copiar dump.rdb directamente desde el contenedor (método robusto)
    docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "${output_path}" 2>/dev/null || {
        log "ERROR" "No se pudo copiar dump.rdb desde ${REDIS_CONTAINER}:/data/dump.rdb"
        exit 1
    }

    if [ ! -s "${output_path}" ]; then
        log "ERROR" "Backup Redis está vacío o falló."
        exit 1
    fi

    local file_size=$(stat -f%z "${output_path}" 2>/dev/null || stat -c%s "${output_path}" 2>/dev/null || echo "unknown")
    log "INFO" "Backup Redis completado: ${output_path} (${file_size} bytes)"

    # Crear symlink a latest
    ln -sf "../${DATE_DIR}/${REDIS_BACKUP_FILE}" "${BACKUP_DIR}/latest/${REDIS_BACKUP_FILE}"

    echo "${output_path}"
}

# ------------------------------------------------------------------------------
# Cleanup antiguo
# ------------------------------------------------------------------------------
cleanup_old_backups() {
    log "INFO" "Limpiando backups con más de ${RETENTION_DAYS} días..."

    find "${BACKUP_DIR}" -type f -name "*.dump" -mtime +"${RETENTION_DAYS}" -delete
    find "${BACKUP_DIR}" -type f -name "*.rdb" -mtime +"${RETENTION_DAYS}" -delete

    log "INFO" "Cleanup completado."
}

# ------------------------------------------------------------------------------
# Verificación post-backup
# ------------------------------------------------------------------------------
verify_backup() {
    local pg_backup="$1"
    local redis_backup="${2:-}"

    log "INFO" "Verificando backups..."

    # PostgreSQL: verificar integridad
    local pg_check=$(pg_restore --dbname "${PG_DB}" -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" \
        --list "${pg_backup}" 2>&1 || echo "FAILED")

    if echo "${pg_check}" | grep -q "FAILED"; then
        log "ERROR" "Verificación PostgreSQL falló: ${pg_check}"
        return 1
    fi

    log "INFO" "PostgreSQL backup OK"

    # Redis: verificar con redis-cli --pipe
    if [ -n "${redis_backup}" ] && [ -f "${redis_backup}" ]; then
        local redis_check=$(file "${redis_backup}" 2>/dev/null || echo "unknown")
        if echo "${redis_check}" | grep -qE "(Redis|RDB data|binary)"; then
            log "INFO" "Redis backup OK"
        else
            log "WARN" "Redis backup verificación básica solo (file type: ${redis_check})"
        fi
    fi

    return 0
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    log "INFO" "=============================================="
    log "INFO" "PRANELY Backup Script - $(date)"
    log "INFO" "=============================================="

    check_prereqs || exit 0
    init_dirs

    local start_time=$(date +%s)
    local pg_backup_path=""
    local redis_backup_path=""

    # Ejecutar backups
    pg_backup_path=$(backup_postgres)

    if check_prereqs; then
        redis_backup_path=$(backup_redis)
    fi

    # Verificar
    if ! verify_backup "${pg_backup_path}" "${redis_backup_path}"; then
        log "ERROR" "Verificación de backups falló."
        exit 1
    fi

    # Cleanup
    cleanup_old_backups

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log "INFO" "=============================================="
    log "INFO" "Backup completado en ${duration}s"
    log "INFO" "PostgreSQL: ${pg_backup_path}"
    log "INFO" "Redis: ${redis_backup_path:-N/A}"
    log "INFO" "=============================================="

    # Exit 0 = success para cron
    exit 0
}

# Solo ejecutar si se llama directamente (no en import)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
