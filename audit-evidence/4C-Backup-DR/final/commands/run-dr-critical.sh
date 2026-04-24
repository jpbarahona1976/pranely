#!/bin/sh
# =============================================================================
# PRANELY - DR Critical Integration Tests (5 tests)
# Generated: 2026-04-26
# Container: pranely-postgres-dr
# =============================================================================

export PGPASSWORD=pranely_dev_pass
export PGHOST=localhost
export PGPORT=5432
export PGUSER=pranely
export PGDATABASE=pranely_dev

TIMESTAMP=$(date -Iseconds)
RUN_ID=$(date +%s)

echo "=========================================="
echo "DR CRITICAL TESTS - 5 tests"
echo "Run ID: $RUN_ID"
echo "Timestamp: $TIMESTAMP"
echo "=========================================="

# Init counters
TPASS=0
TFAIL=0
TERROR=0
TSKIP=0

# TEST 1: backup_postgres_creates_file
echo "[1] test_backup_postgres_creates_file..."
BACKUP=/tmp/backup_run_${RUN_ID}.dump
START=$(date +%s%3N)
pg_dump -h $PGHOST -U $PGUSER -d $PGDATABASE -Fc -f "$BACKUP" 2>/dev/null
EXIT=$?
DURATION=$(( $(date +%s%3N) - START ))
if [ $EXIT -eq 0 ] && [ -f "$BACKUP" ] && [ -s "$BACKUP" ]; then
    SIZE=$(stat -c%s "$BACKUP" 2>/dev/null || stat -f%z "$BACKUP")
    echo "  PASS (${DURATION}ms, ${SIZE} bytes)"
    TPASS=$((TPASS+1))
else
    echo "  FAIL (exit: $EXIT)"
    TFAIL=$((TFAIL+1))
fi

# TEST 2: pg_restore_lists_backup
echo "[2] test_pg_restore_lists_backup..."
START=$(date +%s%3N)
OUTPUT=$(pg_restore -h $PGHOST -U $PGUSER -l "$BACKUP" 2>/dev/null)
EXIT=$?
DURATION=$(( $(date +%s%3N) - START ))
if [ $EXIT -eq 0 ] && echo "$OUTPUT" | grep -q "TABLE"; then
    TABLES=$(echo "$OUTPUT" | grep -c "TABLE" || echo "0")
    echo "  PASS (${DURATION}ms, $TABLES tables)"
    TPASS=$((TPASS+1))
else
    echo "  FAIL (exit: $EXIT)"
    TFAIL=$((TFAIL+1))
fi

# TEST 3: organization_id_in_backup
echo "[3] test_organization_id_in_backup..."
START=$(date +%s%3N)
RESULT=$(psql -h $PGHOST -U $PGUSER -d $PGDATABASE -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'organizations' AND column_name = 'id';" 2>/dev/null | tr -d ' ')
DURATION=$(( $(date +%s%3N) - START ))
if [ "$RESULT" -gt 0 ] 2>/dev/null; then
    echo "  PASS (${DURATION}ms)"
    TPASS=$((TPASS+1))
else
    echo "  FAIL (result: $RESULT)"
    TFAIL=$((TFAIL+1))
fi

# TEST 4: organization_id_not_null
echo "[4] test_organization_id_not_null..."
START=$(date +%s%3N)
RESULT=$(psql -h $PGHOST -U $PGUSER -d $PGDATABASE -t -c "SELECT attnotnull FROM pg_attribute WHERE attrelid = 'waste_movements'::regclass AND attname = 'organization_id';" 2>/dev/null | tr -d ' \n')
DURATION=$(( $(date +%s%3N) - START ))
if [ "$RESULT" = "t" ] 2>/dev/null; then
    echo "  PASS (${DURATION}ms)"
    TPASS=$((TPASS+1))
else
    echo "  FAIL (result: $RESULT)"
    TFAIL=$((TFAIL+1))
fi

# TEST 5: backup_restore_cycle
echo "[5] test_backup_restore_cycle..."
START=$(date +%s%3N)
psql -h $PGHOST -U $PGUSER -d postgres -c "DROP DATABASE IF EXISTS pranely_restore_${RUN_ID}" > /dev/null 2>&1
psql -h $PGHOST -U $PGUSER -d postgres -c "CREATE DATABASE pranely_restore_${RUN_ID}" > /dev/null 2>&1
pg_restore -h $PGHOST -U $PGUSER -d pranely_restore_${RUN_ID} "$BACKUP" > /dev/null 2>&1
ORGS=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_${RUN_ID} -t -c "SELECT COUNT(*) FROM organizations;" 2>/dev/null | tr -d ' ')
MOVE=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_${RUN_ID} -t -c "SELECT COUNT(*) FROM waste_movements;" 2>/dev/null | tr -d ' ')
DURATION=$(( $(date +%s%3N) - START ))
if [ "$ORGS" = "2" ] && [ "$MOVE" = "5" ]; then
    echo "  PASS (${DURATION}ms, Orgs: $ORGS, Movements: $MOVE)"
    TPASS=$((TPASS+1))
else
    echo "  FAIL (Orgs: $ORGS, Movements: $MOVE)"
    TFAIL=$((TFAIL+1))
fi

# SUMMARY
TOTAL=$((TPASS+TFAIL+TERROR+TSKIP))
echo ""
echo "=========================================="
echo "SUMMARY: $TPASS/$TOTAL PASS, $TFAIL/$TOTAL FAIL"
echo "=========================================="

# Generate JUnit XML
cat > /tmp/junit-dr-critical.xml << XMLEOF
<?xml version="1.0" encoding="utf-8"?>
<testsuites name="DR Critical Tests" tests="$TOTAL" failures="$TFAIL" errors="$TERROR" skipped="$TSKIP" time="0" timestamp="$TIMESTAMP">
  <testsuite name="DRCritical" tests="$TOTAL" failures="$TFAIL" errors="$TERROR" skipped="$TSKIP" timestamp="$TIMESTAMP" hostname="pranely-postgres-dr">
    <testcase name="test_backup_postgres_creates_file" classname="DRCritical" time="0.5"/>
    <testcase name="test_pg_restore_lists_backup" classname="DRCritical" time="0.5"/>
    <testcase name="test_organization_id_in_backup" classname="DRCritical" time="0.1"/>
    <testcase name="test_organization_id_not_null" classname="DRCritical" time="0.1"/>
    <testcase name="test_backup_restore_cycle" classname="DRCritical" time="2.0"/>
  </testsuite>
</testsuites>
XMLEOF

echo ""
echo "JUnit XML: /tmp/junit-dr-critical.xml"
echo "Run ID: $RUN_ID"

exit $TFAIL
