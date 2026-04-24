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

echo "=== Running ALL tests with coverage ==="
poetry run pytest tests/test_backup_dr.py tests/test_backup_dr_additional.py \
    --cov=tests.test_backup_dr --cov=tests.test_backup_dr_additional \
    --cov-report=xml \
    --cov-report=term \
    -v \
    --tb=short \
    2>&1
