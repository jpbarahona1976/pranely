# =============================================================================
# PRANELY - Backup Healthcheck Script (Fase 4C)
# Healthcheck para verificar estado de backups
# =============================================================================

#!/bin/bash
# Este script es usado por Docker healthcheck para verificar backups

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
MAX_BACKUP_AGE_HOURS="${MAX_BACKUP_AGE_HOURS:-2}"  # 2h = 1h RPO + 1h buffer

log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] [BACKUP-HC] $*"
}

check_latest_backup() {
    local backup_type="$1"
    local extensions=("dump" "rdb")
    local found=false
    local latest_file=""

    for ext in "${extensions[@]}"; do
        case "$backup_type" in
            postgres)
                local candidate=$(ls -t "${BACKUP_DIR}"/*/*."${ext}" 2>/dev/null | grep -i postgres | head -1)
                ;;
            redis)
                local candidate=$(ls -t "${BACKUP_DIR}"/*/*."${ext}" 2>/dev/null | grep -i redis | head -1)
                ;;
        esac

        if [ -n "${candidate}" ] && [ -f "${candidate}" ]; then
            latest_file="${candidate}"
            found=true
            break
        fi
    done

    if [ "${found}" = false ]; then
        log "ERROR: No se encontró backup ${backup_type}"
        return 1
    fi

    # Verificar antigüedad
    local backup_time=$(stat -f%m "${latest_file}" 2>/dev/null || stat -c%Y "${latest_file}" 2>/dev/null)
    local current_time=$(date +%s)
    local age_seconds=$((current_time - backup_time))
    local age_hours=$((age_seconds / 3600))

    log "Backup ${backup_type}: ${latest_file} (${age_hours}h)"

    if [ ${age_hours} -gt ${MAX_BACKUP_AGE_HOURS} ]; then
        log "ERROR: Backup ${backup_type} tiene ${age_hours}h (máximo: ${MAX_BACKUP_AGE_HOURS}h)"
        return 1
    fi

    return 0
}

# Main
main() {
    log "Iniciando backup healthcheck..."

    # Verificar PostgreSQL backup
    if ! check_latest_backup "postgres"; then
        log "FALLO: Backup PostgreSQL"
        exit 1
    fi

    # Verificar Redis backup (opcional - puede no existir si Redis está vacío)
    if check_latest_backup "redis"; then
        log "Redis backup OK"
    else
        log "WARN: No se encontró backup Redis (puede ser normal si Redis está vacío)"
    fi

    log "Healthcheck OK"
    exit 0
}

main "$@"
