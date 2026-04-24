#!/bin/sh
# DR Integration Tests - Ejecuta 5 tests reales y genera JUnit
cd /app
export SECRET_KEY=test-secret-key
export DATABASE_URL=sqlite+aiosqlite:///test.db
export REDIS_URL=redis://redis:6379
export PG_HOST=postgres
export PG_PORT=5432
export PG_USER=pranely
export PG_DB=pranely_dev
export POSTGRES_PASSWORD=pranely_dev_pass

# Ejecutar solo los 5 tests de integracion con JUnit output
poetry run pytest tests/test_backup_dr.py \
    -k "backup_postgres_creates_file or pg_restore_lists_backup or organization_id_in_backup or organization_id_not_null or backup_restore_cycle" \
    --junitxml=/tmp/junit-dr-5tests.xml \
    -v --tb=short 2>&1
