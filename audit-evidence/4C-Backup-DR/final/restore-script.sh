#!/bin/sh
# Drop and recreate test database
psql -U pranely -d postgres -c "DROP DATABASE IF EXISTS pranely_restore_test"
psql -U pranely -d postgres -c "CREATE DATABASE pranely_restore_test"
# Restore
pg_restore -U pranely -d pranely_restore_test /tmp/pranely_final.dump
# Verify
echo "=== RESTORE VERIFICATION ==="
psql -U pranely -d pranely_restore_test -c "SELECT 'organizations' as tbl, COUNT(*) as cnt FROM organizations UNION ALL SELECT 'users', COUNT(*) FROM users UNION ALL SELECT 'memberships', COUNT(*) FROM memberships UNION ALL SELECT 'waste_movements', COUNT(*) FROM waste_movements"
echo "=== TENANT A (org_id=1) ==="
psql -U pranely -d pranely_restore_test -c "SELECT organization_id, COUNT(*) FROM waste_movements WHERE organization_id=1 GROUP BY organization_id"
echo "=== TENANT B (org_id=2) ==="
psql -U pranely -d pranely_restore_test -c "SELECT organization_id, COUNT(*) FROM waste_movements WHERE organization_id=2 GROUP BY organization_id"
echo "=== CROSS-TENANT ==="
psql -U pranely -d pranely_restore_test -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id NOT IN (1,2)"
