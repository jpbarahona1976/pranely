#!/bin/sh
# =============================================================================
# PRANELY - Coverage Focused on test_backup_dr.py
# =============================================================================
cd /app
export SECRET_KEY=test-secret-key
export DATABASE_URL=sqlite+aiosqlite:///test.db
export REDIS_URL=redis://redis:6379
export PG_HOST=postgres
export PG_PORT=5432
export PG_USER=pranely
export PG_DB=pranely_dev
export POSTGRES_PASSWORD=pranely_dev_pass

echo "=== Running coverage focused on test_backup_dr.py ==="
echo ""

# Ejecutar coverage SOLO en el archivo de tests de DR
poetry run pytest tests/test_backup_dr.py \
    --cov=tests.test_backup_dr \
    --cov-report=xml \
    --cov-report=term-missing \
    -v \
    --tb=short \
    -m "not integration" \
    2>&1

echo ""
echo "=== Coverage XML saved to coverage.xml ==="
