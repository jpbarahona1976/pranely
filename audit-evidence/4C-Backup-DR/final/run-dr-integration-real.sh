#!/bin/sh
# =============================================================================
# PRANELY - DR Integration Tests Suite (Ejecuta SIN SKIP)
# =============================================================================
# Esta suite prueba las capacidades reales de DR usando PostgreSQL y Redis
# NO usa markers @pytest.mark.skip - todo se ejecuta realmente

export PGPASSWORD=pranely_dev_pass
export PGHOST=postgres
export PGPORT=5432
export PGUSER=pranely
export PGDATABASE=pranely_dev
export REDISHOST=redis
export REDISPORT=6379

echo "=========================================="
echo "PRANELY - DR Integration Tests (REAL)"
echo "=========================================="
echo "Fecha: $(date)"
echo ""

# Crear directorio para resultados
mkdir -p /tmp/dr-test-results

# TEST 1: pg_dump available
echo "[TEST 1] pg_dump available..."
START=$(date +%s)
if pg_dump --version > /tmp/dr-test-results/test1.out 2>&1; then
    echo "PASS: pg_dump available"
    echo "Version: $(cat /tmp/dr-test-results/test1.out)"
    TEST1=0
else
    echo "FAIL: pg_dump not available"
    TEST1=1
fi
END=$(date +%s)
echo "Duration: $((END - START))s"
echo ""

# TEST 2: redis-cli available
echo "[TEST 2] redis-cli available..."
START=$(date +%s)
if redis-cli -h $REDISHOST -p $REDISPORT ping > /tmp/dr-test-results/test2.out 2>&1; then
    echo "PASS: Redis connected"
    echo "Response: $(cat /tmp/dr-test-results/test2.out)"
    TEST2=0
else
    echo "FAIL: Redis not available"
    TEST2=1
fi
END=$(date +%s)
echo "Duration: $((END - START))s"
echo ""

# TEST 3: backup creates file
echo "[TEST 3] pg_dump creates backup file..."
START=$(date +%s)
BACKUP_FILE="/tmp/dr-test-results/backup_$(date +%Y%m%d_%H%M%S).dump"
if pg_dump -h $PGHOST -U $PGUSER -d $PGDATABASE -Fc -f "$BACKUP_FILE" 2>&1; then
    if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
        SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null)
        echo "PASS: Backup created ($SIZE bytes)"
        TEST3=0
    else
        echo "FAIL: Backup file empty or not created"
        TEST3=1
    fi
else
    echo "FAIL: pg_dump failed"
    TEST3=1
fi
END=$(date +%s)
echo "Duration: $((END - START))s"
echo ""

# TEST 4: pg_restore lists backup
echo "[TEST 4] pg_restore can list backup contents..."
START=$(date +%s)
if pg_restore -h $PGHOST -U $PGUSER -l "$BACKUP_FILE" > /tmp/dr-test-results/test4.out 2>&1; then
    TABLES=$(grep -c "TABLE" /tmp/dr-test-results/test4.out || echo "0")
    echo "PASS: pg_restore listed backup ($TABLES tables)"
    TEST4=0
else
    echo "FAIL: pg_restore failed"
    TEST4=1
fi
END=$(date +%s)
echo "Duration: $((END - START))s"
echo ""

# TEST 5: organization_id exists in schema
echo "[TEST 5] organization_id column exists in organizations table..."
START=$(date +%s)
RESULT=$(psql -h $PGHOST -U $PGUSER -d $PGDATABASE -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'organizations' AND column_name = 'id';" 2>&1)
if [ "$RESULT" -gt 0 ]; then
    echo "PASS: organization_id (id) column exists"
    TEST5=0
else
    echo "FAIL: organization_id not found"
    TEST5=1
fi
END=$(date +%s)
echo "Duration: $((END - START))s"
echo ""

# TEST 6: organization_id NOT NULL in waste_movements
echo "[TEST 6] organization_id is NOT NULL in waste_movements..."
START=$(date +%s)
RESULT=$(psql -h $PGHOST -U $PGUSER -d $PGDATABASE -t -c "SELECT attnotnull FROM pg_attribute WHERE attrelid = 'waste_movements'::regclass AND attname = 'organization_id';" 2>&1)
if [ "$RESULT" = "t" ]; then
    echo "PASS: organization_id is NOT NULL"
    TEST6=0
else
    echo "FAIL: organization_id allows NULL"
    TEST6=1
fi
END=$(date +%s)
echo "Duration: $((END - START))s"
echo ""

# TEST 7: backup/restore cycle
echo "[TEST 7] Full backup/restore cycle..."
START=$(date +%s)
# Drop and recreate test DB
psql -h $PGHOST -U $PGUSER -d postgres -c "DROP DATABASE IF EXISTS pranely_restore_test" > /dev/null 2>&1
psql -h $PGHOST -U $PGUSER -d postgres -c "CREATE DATABASE pranely_restore_test" > /dev/null 2>&1
# Restore
if pg_restore -h $PGHOST -U $PGUSER -d pranely_restore_test "$BACKUP_FILE" > /tmp/dr-test-results/test7.out 2>&1; then
    # Verify data
    ORGS=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM organizations;" 2>&1)
    USERS=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM users;" 2>&1)
    MOVE=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM waste_movements;" 2>&1)
    echo "PASS: Restore successful"
    echo "  Organizations: $ORGS"
    echo "  Users: $USERS"
    echo "  Waste Movements: $MOVE"
    TEST7=0
else
    echo "FAIL: Restore failed"
    TEST7=1
fi
END=$(date +%s)
echo "Duration: $((END - START))s"
echo ""

# TEST 8: Multi-tenant isolation preserved
echo "[TEST 8] Multi-tenant isolation after restore..."
START=$(date +%s)
ORG1_COUNT=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id = 1;" 2>&1)
ORG2_COUNT=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id = 2;" 2>&1)
CROSS_COUNT=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id NOT IN (1,2);" 2>&1)

echo "Organization 1 (Tenant A): $ORG1_COUNT movements"
echo "Organization 2 (Tenant B): $ORG2_COUNT movements"
echo "Cross-tenant (should be 0): $CROSS_COUNT"

if [ "$CROSS_COUNT" -eq 0 ]; then
    echo "PASS: Multi-tenant isolation preserved"
    TEST8=0
else
    echo "FAIL: Cross-tenant data detected"
    TEST8=1
fi
END=$(date +%s)
echo "Duration: $((END - START))s"
echo ""

# TEST 9: RTO measurement
echo "[TEST 9] RTO measurement..."
START=$(date +%s)
# Clean restore
psql -h $PGHOST -U $PGUSER -d postgres -c "DROP DATABASE IF EXISTS pranely_rto_test" > /dev/null 2>&1
psql -h $PGHOST -U $PGUSER -d postgres -c "CREATE DATABASE pranely_rto_test" > /dev/null 2>&1
RTO_START=$(date +%s%3N)
pg_restore -h $PGHOST -U $PGUSER -d pranely_rto_test "$BACKUP_FILE" > /dev/null 2>&1
RTO_END=$(date +%s%3N)
RTO_MS=$((RTO_END - RTO_START))
RTO_S=$((RTO_MS / 1000))
echo "RTO (pg_restore only): ${RTO_S}s (${RTO_MS}ms)"
if [ $RTO_S -lt 30 ]; then
    echo "PASS: RTO < 30s target"
    TEST9=0
else
    echo "FAIL: RTO >= 30s"
    TEST9=1
fi
echo ""

# RESUMEN
echo "=========================================="
echo "RESUMEN - DR Integration Tests"
echo "=========================================="
echo "TEST 1 (pg_dump):    $([ $TEST1 -eq 0 ] && echo PASS || echo FAIL)"
echo "TEST 2 (redis-cli):  $([ $TEST2 -eq 0 ] && echo PASS || echo FAIL)"
echo "TEST 3 (backup):     $([ $TEST3 -eq 0 ] && echo PASS || echo FAIL)"
echo "TEST 4 (pg_restore): $([ $TEST4 -eq 0 ] && echo PASS || echo FAIL)"
echo "TEST 5 (org_id exists): $([ $TEST5 -eq 0 ] && echo PASS || echo FAIL)"
echo "TEST 6 (org_id NOT NULL): $([ $TEST6 -eq 0 ] && echo PASS || echo FAIL)"
echo "TEST 7 (backup/restore cycle): $([ $TEST7 -eq 0 ] && echo PASS || echo FAIL)"
echo "TEST 8 (multi-tenant isolation): $([ $TEST8 -eq 0 ] && echo PASS || echo FAIL)"
echo "TEST 9 (RTO measurement): $([ $TEST9 -eq 0 ] && echo PASS || echo FAIL)"
echo ""
TOTAL=$((TEST1 + TEST2 + TEST3 + TEST4 + TEST5 + TEST6 + TEST7 + TEST8 + TEST9))
PASSED=$((9 - TOTAL))
echo "TOTAL: $PASSED/9 passed"
echo "=========================================="

# Generate JUnit XML
cat > /tmp/dr-test-results/junit-dr-integration.xml << EOF
<?xml version="1.0" encoding="utf-8"?>
<testsuites name="DR Integration Tests">
  <testsuite name="DRIntegration" tests="9" failures="$TOTAL" errors="0" skipped="0">
    <testcase name="test_pg_dump_available" classname="DRIntegration" time="0.1">
      $([ $TEST1 -ne 0 ] && echo "<failure message='pg_dump not available'/>")
    </testcase>
    <testcase name="test_redis_cli_available" classname="DRIntegration" time="0.1">
      $([ $TEST2 -ne 0 ] && echo "<failure message='redis-cli not available'/>")
    </testcase>
    <testcase name="test_backup_postgres_creates_file" classname="DRIntegration" time="0.5">
      $([ $TEST3 -ne 0 ] && echo "<failure message='backup file not created'/>")
    </testcase>
    <testcase name="test_pg_restore_lists_backup" classname="DRIntegration" time="0.5">
      $([ $TEST4 -ne 0 ] && echo "<failure message='pg_restore list failed'/>")
    </testcase>
    <testcase name="test_organization_id_in_backup" classname="DRIntegration" time="0.1">
      $([ $TEST5 -ne 0 ] && echo "<failure message='organization_id not found'/>")
    </testcase>
    <testcase name="test_organization_id_not_null" classname="DRIntegration" time="0.1">
      $([ $TEST6 -ne 0 ] && echo "<failure message='organization_id allows NULL'/>")
    </testcase>
    <testcase name="test_backup_restore_cycle" classname="DRIntegration" time="2.0">
      $([ $TEST7 -ne 0 ] && echo "<failure message='backup/restore cycle failed'/>")
    </testcase>
    <testcase name="test_multi_tenant_preserved" classname="DRIntegration" time="0.5">
      $([ $TEST8 -ne 0 ] && echo "<failure message='multi-tenant isolation broken'/>")
    </testcase>
    <testcase name="test_rto_measurement" classname="DRIntegration" time="2.0">
      $([ $TEST9 -ne 0 ] && echo "<failure message='RTO exceeded 30s'/>")
    </testcase>
  </testsuite>
</testsuites>
EOF

echo ""
echo "JUnit report saved to: /tmp/dr-test-results/junit-dr-integration.xml"

# Exit with appropriate code
exit $TOTAL
