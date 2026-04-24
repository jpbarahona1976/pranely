#!/bin/sh
# =============================================================================
# PRANELY - Backup/Restore Real
# Generated: 2026-04-26
# Container: pranely-postgres-dr
# =============================================================================

export PGPASSWORD=pranely_dev_pass
export PGHOST=localhost
export PGUSER=pranely
export PGDATABASE=pranely_dev

TIMESTAMP=$(date -Iseconds)
RUN_ID=$(date +%s)

echo "=========================================="
echo "BACKUP REAL"
echo "Run ID: $RUN_ID"
echo "Timestamp: $TIMESTAMP"
echo "=========================================="

# BACKUP
echo "[BACKUP] Starting..."
START=$(date +%s%3N)
BACKUP_FILE="/tmp/pranely_backup_${RUN_ID}.dump"
pg_dump -h $PGHOST -U $PGUSER -d $PGDATABASE -Fc -f "$BACKUP_FILE" 2>&1
EXIT=$?
END=$(date +%s%3N)
DURATION=$((END - START))
echo "Exit: $EXIT"
echo "Duration: ${DURATION}ms"
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE")
    echo "Size: ${SIZE} bytes"
fi

# STORE FOR LATER
echo ""
echo "[BACKUP] Saved to: $BACKUP_FILE"

exit $EXIT
