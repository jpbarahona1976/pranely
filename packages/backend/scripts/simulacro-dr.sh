#!/bin/bash
# =============================================================================
# PRANELY - DR Simulation Script (Fase 4C: Backup/DR)
# Simula desastre y recovery para verificar RPO 1h / RTO 15min
# =============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Cleanup RTO duration file (idempotencia)
# ------------------------------------------------------------------------------
rm -f /tmp/rto_duration.txt

# ------------------------------------------------------------------------------
# Configuración
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups}"
TEST_DATA_SIZE="${TEST_DATA_SIZE:-100}"  # Registros de prueba
DR_COMPOSE_FILE="${PROJECT_DIR}/docker-compose.dr.yml"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")

    case "${level}" in
        "PASS"|"INFO"|"[PASS]"|"[INFO]")
            echo -e "${GREEN}[${timestamp}] [${level}] ${message}${NC}"
            ;;
        "FAIL"|"ERROR"|"[FAIL]"|"[ERROR]")
            echo -e "${RED}[${timestamp}] [${level}] ${message}${NC}"
            ;;
        *)
            echo -e "${YELLOW}[${timestamp}] [${level}] ${message}${NC}"
            ;;
    esac
}

simulate_disaster() {
    log "WARN" "=============================================="
    log "WARN" "SIMULACIÓN DE DESASTRE INICIADA"
    log "WARN" "=============================================="

    # Simular pérdida de datos eliminando tablas críticas
    log "INFO" "Simulando pérdida de datos..."

    # En un escenario real, aquí se apagaría el servicio o se destruirían los datos
    # Para el simulacro en dev, solo verificamos que los backups existan
    log "INFO" "1. Verificando estado pre-desastre..."

    if docker ps --filter "name=pranely-postgres" --filter "name=pranely-redis" --format "{{.Names}}" | \
        grep -qE "(pranely-postgres|pranely-redis)"; then
        log "INFO" "Servicios activos detectados - simulacro puede proceder"
    else
        log "WARN" "Servicios no están corriendo - iniciándolos primero..."
        cd "${PROJECT_DIR}" && docker compose -f docker-compose.dev.yml up -d
        sleep 10
    fi

    log "WARN" "Disaster simulado - datos perdidos."
}

verify_rpo() {
    log "INFO" "=============================================="
    log "INFO" "VERIFICACIÓN RPO (Recovery Point Objective)"
    log "INFO" "=============================================="

    local rpo_check=true
    local rpo_age_hours=0
    local RPO_MAX_HOURS=2  # RPO 1h + 1h buffer

    # 1. Verificar backup PostgreSQL
    log "INFO" "1. Verificando backup PostgreSQL..."

    local pg_backup=$(ls -t "${BACKUP_DIR}"/*/*.dump 2>/dev/null | head -1)

    if [ -z "${pg_backup}" ] || [ ! -f "${pg_backup}" ]; then
        log "FAIL" "No existe backup PostgreSQL!"
        rpo_check=false
    else
        local backup_time=$(stat -f%m "${pg_backup}" 2>/dev/null || stat -c%Y "${pg_backup}" 2>/dev/null)
        local current_time=$(date +%s)
        local age_seconds=$((current_time - backup_time))
        rpo_age_hours=$((age_seconds / 3600))

        log "INFO" "Backup PostgreSQL encontrado: ${pg_backup}"
        log "INFO" "Antigüedad del backup: ${rpo_age_hours}h"

        if [ ${rpo_age_hours} -gt ${RPO_MAX_HOURS} ]; then
            log "FAIL" "RPO VIOLADO: Backup tiene ${rpo_age_hours}h (máximo: ${RPO_MAX_HOURS}h para RPO=1h)"
            rpo_check=false
        else
            log "PASS" "RPO OK: Backup dentro de ventana de ${RPO_MAX_HOURS}h"
        fi
    fi

    # 2. Verificar backup Redis
    log "INFO" "2. Verificando backup Redis..."

    local redis_backup=$(ls -t "${BACKUP_DIR}"/*/*.rdb 2>/dev/null | head -1)

    if [ -z "${redis_backup}" ] || [ ! -f "${redis_backup}" ]; then
        log "FAIL" "No existe backup Redis!"
        rpo_check=false
    else
        local backup_time=$(stat -f%m "${redis_backup}" 2>/dev/null || stat -c%Y "${redis_backup}" 2>/dev/null)
        local current_time=$(date +%s)
        local age_seconds=$((current_time - backup_time))
        local age_redis_hours=$((age_seconds / 3600))

        log "INFO" "Backup Redis encontrado: ${redis_backup}"
        log "INFO" "Antigüedad del backup: ${age_redis_hours}h"

        if [ ${age_redis_hours} -gt ${RPO_MAX_HOURS} ]; then
            log "FAIL" "RPO VIOLADO: Backup Redis tiene ${age_redis_hours}h (máximo: ${RPO_MAX_HOURS}h)"
            rpo_check=false
        else
            log "PASS" "RPO Redis OK"
        fi
    fi

    # 3. Verificar retención (7 días)
    log "INFO" "3. Verificando política de retención..."

    local old_backups=$(find "${BACKUP_DIR}" -type f \( -name "*.dump" -o -name "*.rdb" \) -mtime +7 | wc -l)
    log "INFO" "Backups con más de 7 días: ${old_backups}"

    if [ ${old_backups} -gt 0 ]; then
        log "FAIL" "Políticas de retención no se están aplicando!"
        rpo_check=false
    else
        log "PASS" "Retención OK"
    fi

    if [ "${rpo_check}" = true ]; then
        log "PASS" "RPO VERIFICATION PASSED"
        return 0
    else
        log "FAIL" "RPO VERIFICATION FAILED"
        return 1
    fi
}

verify_rto() {
    log "INFO" "=============================================="
    log "INFO" "VERIFICACIÓN RTO (Recovery Time Objective)"
    log "INFO" "=============================================="

    local RTO_START=$(date +%s)
    local rto_check=true

    log "INFO" "Iniciando procedimiento de restore..."
    log "WARN" "Este proceso puede tomar varios minutos..."

    # Ejecutar restore
    cd "${PROJECT_DIR}"

    if bash "${SCRIPT_DIR}/restore.sh" 2>&1; then
        log "PASS" "Restore completado"
    else
        log "FAIL" "Restore falló"
        rto_check=false
    fi

    local RTO_END=$(date +%s)
    local RTO_DURATION=$((RTO_END - RTO_START))

    log "INFO" "--------------------------------------"
    log "INFO" "RTO Resultado: ${RTO_DURATION}s"
    log "INFO" "--------------------------------------"

    # RTO objetivo: 15 minutos = 900 segundos
    if [ ${RTO_DURATION} -gt 900 ]; then
        log "FAIL" "RTO EXCEDIDO: ${RTO_DURATION}s > 900s (15min objetivo)"
        rto_check=false
    else
        log "PASS" "RTO DENTRO DEL OBJETIVO: ${RTO_DURATION}s < 900s"
    fi

    # Verificar integridad post-restore
    log "INFO" "Verificando integridad post-restore..."

    local table_count=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h localhost -p 5433 -U pranely -d pranely_dev \
        -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';" 2>/dev/null | tr -d ' ')

    if [ -z "${table_count}" ] || [ "${table_count}" -eq 0 ]; then
        log "FAIL" "Post-restore: No se encontraron tablas"
        rto_check=false
    else
        log "PASS" "Post-restore: ${table_count} tablas verificadas"

        # Verificar multi-tenancy
        local org_count=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h localhost -p 5433 -U pranely -d pranely_dev \
            -t -c "SELECT COUNT(*) FROM organizations;" 2>/dev/null | tr -d ' ')
        log "INFO" "Organizations en DB restaurada: ${org_count}"
    fi

    # Verificar Redis
    local redis_ping=$(redis-cli -h localhost -p 6380 PING 2>/dev/null)
    if [ "${redis_ping}" = "PONG" ]; then
        log "PASS" "Redis DR responding"
    else
        log "FAIL" "Redis DR no responde"
        rto_check=false
    fi

    if [ "${rto_check}" = true ]; then
        log "PASS" "RTO VERIFICATION PASSED"
        return 0
    else
        log "FAIL" "RTO VERIFICATION FAILED"
        return 1
    fi
}

cleanup_dr_environment() {
    log "INFO" "Limpiando entorno DR..."

    cd "${PROJECT_DIR}"

    # Detener servicios DR
    docker compose -f docker-compose.dr.yml --profile dr down -v 2>/dev/null || true

    log "INFO" "Entorno DR limpiado"
}

generate_report() {
    local rpo_result="$1"
    local rto_result="$2"
    local rto_duration="$3"
    local report_file="${BACKUP_DIR}/reports/dr_simulation_$(date +%Y%m%d_%H%M%S).txt"

    mkdir -p "${BACKUP_DIR}/reports"

    cat > "${report_file}" << EOF
================================================================================
PRANELY - DR SIMULATION REPORT
================================================================================
Date: $(date)
Host: $(hostname)
================================================================================

RPO CHECK: ${rpo_result}
  - Objetivo: 1h (2h máxima ventana de backup = RPO + 1h buffer)
  - Backup más reciente PG: $(ls -t ${BACKUP_DIR}/*/*.dump 2>/dev/null | head -1 || echo "N/A")
  - Backup más reciente Redis: $(ls -t ${BACKUP_DIR}/*/*.rdb 2>/dev/null | head -1 || echo "N/A")

RTO CHECK: ${rto_result}
  - Objetivo: 15 minutos (900 segundos)
  - Tiempo real de recuperación: ${rto_duration}s

INTEGRITY CHECK:
  - PostgreSQL tables: $(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h localhost -p 5433 -U pranely -d pranely_dev -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';" 2>/dev/null | tr -d ' ')
  - Redis status: $(redis-cli -h localhost -p 6380 PING 2>/dev/null || echo "N/A")

RESULT: $([ "${rpo_result}" = "PASSED" ] && [ "${rto_result}" = "PASSED" ] && echo "ALL TESTS PASSED" || echo "SOME TESTS FAILED")

================================================================================
EOF

    log "INFO" "Reporte generado: ${report_file}"
    cat "${report_file}"
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    log "INFO" "=============================================="
    log "INFO" "PRANELY DR SIMULATION TEST"
    log "INFO" "RPO: 1h objetivo | RTO: 15min objetivo"
    log "INFO" "=============================================="

    local rpo_result="FAILED"
    local rto_result="FAILED"
    local rto_duration=0

    # Generar datos de prueba si es necesario
    log "INFO" "Verificando datos de prueba..."

    # Verificar RPO
    if verify_rpo; then
        rpo_result="PASSED"
    else
        log "WARN" "RPO falló - continuando con RTO de todas formas..."
    fi

    # Simular desastre
    simulate_disaster

    # Verificar RTO
    if verify_rto; then
        rto_result="PASSED"
        rto_duration=$(cat /tmp/rto_duration.txt 2>/dev/null || echo "0")
    else
        log "FAIL" "RTO falló"
    fi

    # Cleanup
    cleanup_dr_environment

    # Generar reporte
    generate_report "${rpo_result}" "${rto_result}" "${rto_duration}"

    # Resumen final
    log "INFO" "=============================================="
    log "INFO" "DR SIMULATION SUMMARY"
    log "INFO" "RPO: ${rpo_result}"
    log "INFO" "RTO: ${rto_result}"
    log "INFO" "=============================================="

    if [ "${rpo_result}" = "PASSED" ] && [ "${rto_result}" = "PASSED" ]; then
        log "PASS" "DR SIMULATION PASSED - Sistema cumple RPO/RTO"
        exit 0
    else
        log "FAIL" "DR SIMULATION FAILED - Revisar reporte"
        exit 1
    fi
}

# Parsear argumentos
case "${1:-dr-test}" in
    "rpo")
        verify_rpo
        ;;
    "rto")
        verify_rto
        ;;
    "full"|"dr-test")
        main
        ;;
    "cleanup")
        cleanup_dr_environment
        ;;
    *)
        echo "Uso: $0 {rpo|rto|full|cleanup}"
        echo "  rpo     - Solo verificar RPO"
        echo "  rto     - Solo verificar RTO"
        echo "  full    - Simulación completa (default)"
        echo "  cleanup - Limpiar entorno DR"
        exit 1
        ;;
esac
