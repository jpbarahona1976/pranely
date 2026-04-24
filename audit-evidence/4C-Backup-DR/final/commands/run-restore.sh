#!/bin/sh
# =============================================================================
# PRANELY - Restore + RTO Measurement
# Generated: 2026-04-26
# Container: pranely-postgres-dr
# =============================================================================

export PGPASSWORD=pranely_dev_pass
export PGHOST=localhost
export PGUSER=pranely

TIMESTAMP=$(date -Iseconds)
RUN_ID=$(date +%s)
BACKUP_FILE="/tmp/pranely_backup_1777002229.dump"

echo "=========================================="
echo "RESTORE REAL"
echo "Run ID: $RUN_ID"
echo "Timestamp: $TIMESTAMP"
echo "=========================================="

# DROP/RESTORE
echo "[RESTORE] Dropping test DB..."
psql -h $PGHOST -U $PGUSER -d postgres -c "DROP DATABASE IF EXISTS pranely_rto_test" > /dev/null 2>&1

echo "[RESTORE] Creating test DB..."
psql -h $PGHOST -U $PGUSER -d postgres -c "CREATE DATABASE pranely_rto_test" > /dev/null 2>&1

echo "[RESTORE] Starting pg_restore..."
RTO_START=$(date +%s%3N)
pg_restore -h $PGHOST -U $PGUSER -d pranely_rto_test "$BACKUP_FILE" > /tmp/restore.log 2>&1
EXIT=$?
RTO_END=$(date +%s%3N)
RTO_MS=$((RTO_END - RTO_START))
echo "Exit: $EXIT"
echo "RTO (pg_restore only): ${RTO_MS}ms"

# VERIFY
echo ""
echo "[VERIFY] Counting records..."
ORGS=$(psql -h $PGHOST -U $PGUSER -d pranely_rto_test -t -c "SELECT COUNT(*) FROM organizations;" 2>/dev/null | tr -d ' ')
USERS=$(psql -h $PGHOST -U $PGUSER -d pranely_rto_test -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
MOVE=$(psql -h $PGHOST -U $PGUSER -d pranely_rto_test -t -c "SELECT COUNT(*) FROM waste_movements;" 2>/dev/null | tr -d ' ')
echo "Organizations: $ORGS"
echo "Users: $USERS"
echo "Waste Movements: $MOVE"

# TENANT CHECK
echo ""
echo "[MULTI-TENANT] Checking org_id..."
ORG1=$(psql -h $PGHOST -U $PGUSER -d pranely_rto_test -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id = 1;" 2>/dev/null | tr -d ' ')
ORG2=$(psql -h $PGHOST -U $PGUSER -d pranely_rto_test -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id = 2;" 2>/dev/null | tr -d ' ')
CROSS=$(psql -h $PGHOST -U $PGUSER -d pranely_rto_test -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id NOT IN (1,2);" 2>/dev/null | tr -d ' ')
echo "Org 1 movements: $ORG1"
echo "Org 2 movements: $ORG2"
echo "Cross-tenant (should be 0): $CROSS"

# SAVE RTO
echo ""
echo "$RTO_MS" > /tmp/rto_duration.txt
echo "RTO saved to: /tmp/rto_duration.txt"

# SUMMARY
echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo "RTO: ${RTO_MS}ms"
echo "Organizations restored: $ORGS"
echo "Waste movements restored: $MOVE"
echo "Cross-tenant blocked: $CROSS"

exit $EXIT
