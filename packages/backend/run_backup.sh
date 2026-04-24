#!/bin/bash
# Script para ejecutar backup real y generar evidencia

set -euo pipefail

# Configuración
BACKUP_DIR="/app/backups/$(date +%Y/%m/%d)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/postgres_backup-${TIMESTAMP}.dump"

# Crear directorio
mkdir -p "${BACKUP_DIR}"

# Backup
echo "[$(date +%Y-%m-%d\ %H:%M:%S)] [BACKUP] Starting backup..."
echo "[$(date +%Y-%m-%d\ %H:%M:%S)] [BACKUP] Backup file: ${BACKUP_FILE}"

# Ejecutar pg_dump
docker exec pranely-postgres pg_dump -U pranely -d pranely_dev -Fc -f /tmp/backup.dump

# Copiar backup
docker cp pranely-postgres:/tmp/backup.dump "${BACKUP_FILE}"

# Verificar tamaño
SIZE=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}" 2>/dev/null)

echo "[$(date +%Y-%m-%d\ %H:%M:%S)] [BACKUP] Backup size: ${SIZE} bytes"
echo "[$(date +%Y-%m-%d\ %H:%M:%S)] [BACKUP] Exit code: $?"

# Generar evidencia de tablas
docker exec pranely-postgres psql -U pranely -d pranely_dev -c "\dt" > "${BACKUP_DIR}/tables-${TIMESTAMP}.txt"

# Verificar organization_id NOT NULL en waste_movements
docker exec pranely-postgres psql -U pranely -d pranely_dev -c "SELECT attname, attnotnull FROM pg_attribute WHERE attrelid='waste_movements'::regclass AND attname='organization_id';" > "${BACKUP_DIR}/org_id_check-${TIMESTAMP}.txt"

echo "[$(date +%Y-%m-%d\ %H:%M:%S)] [BACKUP] Evidence saved to ${BACKUP_DIR}"
