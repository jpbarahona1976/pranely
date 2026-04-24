#!/bin/sh
export PGPASSWORD=pranely_dev_pass
export PGHOST=postgres
export PGUSER=pranely
export PGDATABASE=pranely_dev

echo "=== Table structure ==="
psql -h $PGHOST -U $PGUSER -d $PGDATABASE << 'EOF'
\d waste_movements
EOF

echo ""
echo "=== organization_id constraint ==="
psql -h $PGHOST -U $PGUSER -d $PGDATABASE << 'EOF'
SELECT 
    a.attname as column_name,
    a.attnotnull as is_not_null,
    format_type(a.atttypid, a.atttypmod) as data_type
FROM pg_attribute a
JOIN pg_class c ON a.attrelid = c.oid
WHERE c.relname = 'waste_movements'
AND a.attname = 'organization_id';
EOF

echo ""
echo "=== Check data ==="
psql -h $PGHOST -U $PGUSER -d $PGDATABASE << 'EOF'
SELECT organization_id, COUNT(*) FROM waste_movements GROUP BY organization_id;
EOF

echo ""
echo "=== Redis connectivity ==="
redis-cli -h redis ping
