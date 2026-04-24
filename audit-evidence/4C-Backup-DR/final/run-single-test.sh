#!/bin/sh
cd /app
export SECRET_KEY=test-secret-key
export DATABASE_URL=sqlite+aiosqlite:///test.db
export REDIS_URL=redis://redis:6379
export PG_HOST=postgres
export PG_PORT=5432
export PG_USER=pranely
export PG_DB=pranely_dev
export POSTGRES_PASSWORD=pranely_dev_pass

echo "=== Ejecutando test_backup_restore_cycle ==="
poetry run pytest tests/test_backup_dr.py::TestBackupRestoreIntegration::test_backup_restore_cycle --junitxml=/tmp/junit-single.xml -v --tb=short 2>&1
echo "=== Exit: $? ==="
