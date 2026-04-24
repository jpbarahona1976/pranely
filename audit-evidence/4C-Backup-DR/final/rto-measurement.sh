#!/bin/sh
echo "=== RTO MEASUREMENT ==="
echo "Starting RTO measurement..."
START=$(date +%s)
echo "START_TIME: $START"

# Restore
psql -U pranely -d postgres -c "DROP DATABASE IF EXISTS pranely_restore_test"
psql -U pranely -d postgres -c "CREATE DATABASE pranely_restore_test"
pg_restore -U pranely -d pranely_restore_test /tmp/pranely_final.dump

END=$(date +%s)
DURATION=$((END - START))
echo "END_TIME: $END"
echo "RTO_DURATION: ${DURATION}s"

if [ $DURATION -lt 30 ]; then
    echo "RTO_STATUS: COMPLIANT (< 30s)"
else
    echo "RTO_STATUS: EXCEEDED (>= 30s)"
fi
