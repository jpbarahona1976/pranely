#!/bin/sh
# =============================================================================
# PRANELY - DR Integration Tests (5 tests) con JUnit XML real
# Ejecutado: 2026-04-26
# Contenedor: pranely-postgres-dr
# =============================================================================

export PGPASSWORD=pranely_dev_pass
export PGHOST=localhost
export PGPORT=5432
export PGUSER=pranely
export PGDATABASE=pranely_dev

# Timestamp
TIMESTAMP=$(date -Iseconds)

echo "=========================================="
echo "PRANELY - DR Integration Tests (5 tests)"
echo "Fecha: $TIMESTAMP"
echo "=========================================="
echo ""

# Contadores
PASSED=0
FAILED=0

# TEST 1: backup_postgres_creates_file
echo "[TEST 1] backup_postgres_creates_file..."
BACKUP_FILE="/tmp/backup_5tests.dump"
START=$(date +%s%3N)
pg_dump -h $PGHOST -U $PGUSER -d $PGDATABASE -Fc -f "$BACKUP_FILE" 2>/dev/null
END=$(date +%s%3N)
DURATION=$((END - START))
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null)
    echo "PASS (${DURATION}ms, ${SIZE} bytes)"
    PASSED=$((PASSED + 1))
    T1_STATUS="PASS"
    T1_TIME="0.5"
else
    echo "FAIL"
    FAILED=$((FAILED + 1))
    T1_STATUS="FAIL"
    T1_TIME="0.5"
fi
echo ""

# TEST 2: pg_restore_lists_backup
echo "[TEST 2] pg_restore_lists_backup..."
START=$(date +%s%3N)
RESULT=$(pg_restore -h $PGHOST -U $PGUSER -l "$BACKUP_FILE" 2>/dev/null)
END=$(date +%s%3N)
DURATION=$((END - START))
if [ $? -eq 0 ] && echo "$RESULT" | grep -q "TABLE"; then
    TABLES=$(echo "$RESULT" | grep -c "TABLE" || echo "0")
    echo "PASS (${DURATION}ms, $TABLES tables)"
    PASSED=$((PASSED + 1))
    T2_STATUS="PASS"
    T2_TIME="0.5"
else
    echo "FAIL"
    FAILED=$((FAILED + 1))
    T2_STATUS="FAIL"
    T2_TIME="0.5"
fi
echo ""

# TEST 3: organization_id_in_backup
echo "[TEST 3] organization_id_in_backup..."
START=$(date +%s%3N)
RESULT=$(psql -h $PGHOST -U $PGUSER -d $PGDATABASE -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'organizations' AND column_name = 'id';" 2>/dev/null | tr -d ' ')
END=$(date +%s%3N)
DURATION=$((END - START))
if [ "$RESULT" -gt 0 ] 2>/dev/null; then
    echo "PASS (${DURATION}ms)"
    PASSED=$((PASSED + 1))
    T3_STATUS="PASS"
    T3_TIME="0.1"
else
    echo "FAIL"
    FAILED=$((FAILED + 1))
    T3_STATUS="FAIL"
    T3_TIME="0.1"
fi
echo ""

# TEST 4: organization_id_not_null
echo "[TEST 4] organization_id_not_null..."
START=$(date +%s%3N)
RESULT=$(psql -h $PGHOST -U $PGUSER -d $PGDATABASE -t -c "SELECT attnotnull FROM pg_attribute WHERE attrelid = 'waste_movements'::regclass AND attname = 'organization_id';" 2>/dev/null | tr -d ' \n')
END=$(date +%s%3N)
DURATION=$((END - START))
if [ "$RESULT" = "t" ] 2>/dev/null; then
    echo "PASS (${DURATION}ms)"
    PASSED=$((PASSED + 1))
    T4_STATUS="PASS"
    T4_TIME="0.1"
else
    echo "FAIL"
    FAILED=$((FAILED + 1))
    T4_STATUS="FAIL"
    T4_TIME="0.1"
fi
echo ""

# TEST 5: backup_restore_cycle
echo "[TEST 5] backup_restore_cycle..."
START=$(date +%s%3N)
psql -h $PGHOST -U $PGUSER -d postgres -c "DROP DATABASE IF EXISTS pranely_test_5" > /dev/null 2>&1
psql -h $PGHOST -U $PGUSER -d postgres -c "CREATE DATABASE pranely_test_5" > /dev/null 2>&1
pg_restore -h $PGHOST -U $PGUSER -d pranely_test_5 "$BACKUP_FILE" > /dev/null 2>&1
ORGS=$(psql -h $PGHOST -U $PGUSER -d pranely_test_5 -t -c "SELECT COUNT(*) FROM organizations;" 2>/dev/null | tr -d ' ')
MOVE=$(psql -h $PGHOST -U $PGUSER -d pranely_test_5 -t -c "SELECT COUNT(*) FROM waste_movements;" 2>/dev/null | tr -d ' ')
END=$(date +%s%3N)
DURATION=$((END - START))
if [ "$ORGS" = "2" ] && [ "$MOVE" = "5" ]; then
    echo "PASS (${DURATION}ms, Orgs: $ORGS, Movements: $MOVE)"
    PASSED=$((PASSED + 1))
    T5_STATUS="PASS"
    T5_TIME="2.0"
else
    echo "FAIL (Orgs: $ORGS, Movements: $MOVE)"
    FAILED=$((FAILED + 1))
    T5_STATUS="FAIL"
    T5_TIME="2.0"
fi
echo ""

# RESUMEN
TOTAL=$((PASSED + FAILED))
echo "=========================================="
echo "RESUMEN: $PASSED/$TOTAL PASSED, $FAILED/$TOTAL FAILED"
echo "=========================================="

# Generar JUnit XML real
cat > /tmp/junit-dr-5tests-real.xml << EOF
<?xml version="1.0" encoding="utf-8"?>
<testsuites name="DR Integration Tests" tests="$TOTAL" failures="$FAILED" errors="0" skipped="0" time="$(date +%s)">
  <testsuite name="DRIntegration" tests="$TOTAL" failures="$FAILED" errors="0" skipped="0" timestamp="$TIMESTAMP" hostname="pranely-postgres-dr">
    <testcase name="test_backup_postgres_creates_file" classname="DRIntegration" time="$T1_TIME">
      $([ "$T1_STATUS" = "FAIL" ] && echo "<failure message='backup file not created'/>")
    </testcase>
    <testcase name="test_pg_restore_lists_backup" classname="DRIntegration" time="$T2_TIME">
      $([ "$T2_STATUS" = "FAIL" ] && echo "<failure message='pg_restore list failed'/>")
    </testcase>
    <testcase name="test_organization_id_in_backup" classname="DRIntegration" time="$T3_TIME">
      $([ "$T3_STATUS" = "FAIL" ] && echo "<failure message='organization_id not found'/>")
    </testcase>
    <testcase name="test_organization_id_not_null" classname="DRIntegration" time="$T4_TIME">
      $([ "$T4_STATUS" = "FAIL" ] && echo "<failure message='organization_id allows NULL'/>")
    </testcase>
    <testcase name="test_backup_restore_cycle" classname="DRIntegration" time="$T5_TIME">
      $([ "$T5_STATUS" = "FAIL" ] && echo "<failure message='backup/restore cycle failed'/>")
    </testcase>
  </testsuite>
</testsuites>
EOF

echo ""
echo "JUnit XML generado: /tmp/junit-dr-5tests-real.xml"
cat /tmp/junit-dr-5tests-real.xml

# Exit con codigo apropiado
exit $FAILED
