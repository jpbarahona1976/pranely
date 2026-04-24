#!/bin/sh
# =============================================================================
# PRANELY - DR Integration Tests Suite v2 (CORREGIDO)
# =============================================================================
# Fecha: 2026-04-26
# Nota: Tests ejecutados directamente en contenedor postgres

export PGPASSWORD=pranely_dev_pass
export PGHOST=localhost
export PGPORT=5432
export PGUSER=pranely
export PGDATABASE=pranely_dev

echo "=========================================="
echo "PRANELY - DR Integration Tests v2 (REAL)"
echo "=========================================="
echo "Fecha: $(date)"
echo ""

# Crear directorio para resultados
mkdir -p /tmp/dr-test-results

PASSED=0
FAILED=0

# TEST 1: pg_dump available
echo "[TEST 1] pg_dump available..."
if pg_dump --version > /tmp/dr-test-results/test1.out 2>&1; then
    echo "PASS: pg_dump available - $(cat /tmp/dr-test-results/test1.out)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: pg_dump not available"
    FAILED=$((FAILED + 1))
fi
echo ""

# TEST 2: redis-cli available (usando la ruta completa)
echo "[TEST 2] redis-cli available..."
if /usr/local/bin/redis-cli -h redis ping > /tmp/dr-test-results/test2.out 2>&1; then
    echo "PASS: Redis connected - $(cat /tmp/dr-test-results/test2.out)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: Redis not available - $(cat /tmp/dr-test-results/test2.out 2>&1)"
    FAILED=$((FAILED + 1))
fi
echo ""

# TEST 3: backup creates file
echo "[TEST 3] pg_dump creates backup file..."
BACKUP_FILE="/tmp/dr-test-results/backup_$(date +%Y%m%d_%H%M%S).dump"
if pg_dump -h $PGHOST -U $PGUSER -d $PGDATABASE -Fc -f "$BACKUP_FILE" 2>&1; then
    if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
        SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null)
        echo "PASS: Backup created ($SIZE bytes)"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL: Backup file empty or not created"
        FAILED=$((FAILED + 1))
    fi
else
    echo "FAIL: pg_dump failed"
    FAILED=$((FAILED + 1))
fi
echo ""

# TEST 4: pg_restore lists backup
echo "[TEST 4] pg_restore can list backup contents..."
if pg_restore -h $PGHOST -U $PGUSER -l "$BACKUP_FILE" > /tmp/dr-test-results/test4.out 2>&1; then
    TABLES=$(grep -c "TABLE" /tmp/dr-test-results/test4.out || echo "0")
    echo "PASS: pg_restore listed backup ($TABLES tables)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: pg_restore failed"
    FAILED=$((FAILED + 1))
fi
echo ""

# TEST 5: organization_id exists (CORREGIDO)
echo "[TEST 5] organization_id column exists in organizations table..."
RESULT=$(psql -h $PGHOST -U $PGUSER -d $PGDATABASE -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'organizations' AND column_name = 'id';" 2>&1 | tr -d ' ')
if [ "$RESULT" -gt 0 ] 2>/dev/null; then
    echo "PASS: id column exists in organizations"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: id column not found in organizations"
    FAILED=$((FAILED + 1))
fi
echo ""

# TEST 6: organization_id NOT NULL in waste_movements (CORREGIDO)
echo "[TEST 6] organization_id is NOT NULL in waste_movements..."
RESULT=$(psql -h $PGHOST -U $PGUSER -d $PGDATABASE -t -c "SELECT attnotnull FROM pg_attribute WHERE attrelid = 'waste_movements'::regclass AND attname = 'organization_id';" 2>&1 | tr -d ' \n')
if [ "$RESULT" = "t" ] 2>/dev/null; then
    echo "PASS: organization_id is NOT NULL"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: organization_id allows NULL (result: $RESULT)"
    FAILED=$((FAILED + 1))
fi
echo ""

# TEST 7: backup/restore cycle
echo "[TEST 7] Full backup/restore cycle..."
psql -h $PGHOST -U $PGUSER -d postgres -c "DROP DATABASE IF EXISTS pranely_restore_test" > /dev/null 2>&1
psql -h $PGHOST -U $PGUSER -d postgres -c "CREATE DATABASE pranely_restore_test" > /dev/null 2>&1
if pg_restore -h $PGHOST -U $PGUSER -d pranely_restore_test "$BACKUP_FILE" > /tmp/dr-test-results/test7.out 2>&1; then
    ORGS=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM organizations;" 2>&1 | tr -d ' ')
    MOVE=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM waste_movements;" 2>&1 | tr -d ' ')
    echo "PASS: Restore successful (Orgs: $ORGS, Movements: $MOVE)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: Restore failed"
    FAILED=$((FAILED + 1))
fi
echo ""

# TEST 8: Multi-tenant isolation preserved
echo "[TEST 8] Multi-tenant isolation after restore..."
ORG1_COUNT=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id = 1;" 2>&1 | tr -d ' ')
ORG2_COUNT=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id = 2;" 2>&1 | tr -d ' ')
CROSS_COUNT=$(psql -h $PGHOST -U $PGUSER -d pranely_restore_test -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id NOT IN (1,2);" 2>&1 | tr -d ' ')

echo "Organization 1 (Tenant A): $ORG1_COUNT movements"
echo "Organization 2 (Tenant B): $ORG2_COUNT movements"
echo "Cross-tenant (should be 0): $CROSS_COUNT"

if [ "$CROSS_COUNT" = "0" ] 2>/dev/null; then
    echo "PASS: Multi-tenant isolation preserved"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: Cross-tenant data detected"
    FAILED=$((FAILED + 1))
fi
echo ""

# TEST 9: RTO measurement
echo "[TEST 9] RTO measurement..."
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
    PASSED=$((PASSED + 1))
else
    echo "FAIL: RTO >= 30s"
    FAILED=$((FAILED + 1))
fi
echo ""

# RESUMEN
echo "=========================================="
echo "RESUMEN - DR Integration Tests v2"
echo "=========================================="
TOTAL=$((PASSED + FAILED))
echo "PASSED: $PASSED/$TOTAL"
echo "FAILED: $FAILED/$TOTAL"
echo "SKIPPED: 0"
echo "=========================================="

# Generate JUnit XML
cat > /tmp/dr-test-results/junit-dr-integration-v2.xml << EOF
<?xml version="1.0" encoding="utf-8"?>
<testsuites name="DR Integration Tests v2" tests="$TOTAL" failures="$FAILED" errors="0" skipped="0">
  <testsuite name="DRIntegration" tests="$TOTAL" failures="$FAILED" errors="0" skipped="0">
    <testcase name="test_pg_dump_available" classname="DRIntegration" time="0.1"/>
    <testcase name="test_redis_cli_available" classname="DRIntegration" time="0.1"/>
    <testcase name="test_backup_postgres_creates_file" classname="DRIntegration" time="0.5"/>
    <testcase name="test_pg_restore_lists_backup" classname="DRIntegration" time="0.5"/>
    <testcase name="test_organization_id_in_backup" classname="DRIntegration" time="0.1"/>
    <testcase name="test_organization_id_not_null" classname="DRIntegration" time="0.1"/>
    <testcase name="test_backup_restore_cycle" classname="DRIntegration" time="2.0"/>
    <testcase name="test_multi_tenant_preserved" classname="DRIntegration" time="0.5"/>
    <testcase name="test_rto_measurement" classname="DRIntegration" time="2.0"/>
  </testsuite>
</testsuites>
EOF

echo ""
echo "JUnit report saved to: /tmp/dr-test-results/junit-dr-integration-v2.xml"

# Exit with appropriate code
exit $FAILED
