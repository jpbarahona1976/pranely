#!/bin/sh
# Backup execution script
echo "[$(date -Iseconds)] Starting backup..."
START=$(date +%s)

# Execute backup
docker exec pranely-postgres-dr pg_dump -U pranely -d pranely_dev -Fc -f /tmp/pranely_dr_backup_final.dump
RESULT=$?

END=$(date +%s)
DURATION=$((END - START))

echo "[$(date -Iseconds)] Backup completed"
echo "Duration: ${DURATION}s"
echo "Exit code: ${RESULT}"
echo "File: /tmp/pranely_dr_backup_final.dump"

# Verify file
docker exec pranely-postgres-dr ls -la /tmp/pranely_dr_backup_final.dump

exit $RESULT
