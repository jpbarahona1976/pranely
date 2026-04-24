#!/bin/sh
# =============================================================================
# PRANELY - Full Test Suite 4C (Unit + Additional)
# Generated: 2026-04-26
# Container: pranely-backend
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

echo "=========================================="
echo "FULL TEST SUITE 4C"
echo "=========================================="

poetry run pytest tests/test_backup_dr.py tests/test_backup_dr_additional.py \
    --junitxml=/tmp/junit-4c-full.xml \
    --cov=tests.test_backup_dr --cov=tests.test_backup_dr_additional \
    --cov-report=xml:/tmp/coverage-final.xml \
    -v --tb=short 2>&1

echo ""
echo "JUnit: /tmp/junit-4c-full.xml"
echo "Coverage: /tmp/coverage-final.xml"
