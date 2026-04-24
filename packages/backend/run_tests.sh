#!/bin/bash
cd /app
export POSTGRES_PASSWORD=pranely_dev
export PG_HOST=pranely-postgres
export PG_PORT=5432
export PG_USER=pranely
export PG_DB=pranely_dev

# Run all tests with junit output
poetry run pytest tests/test_backup_dr.py -v --tb=short --junitxml=/app/test-results/junit.xml

# Run integration tests specifically
poetry run pytest tests/test_backup_dr.py::TestBackupExecution::test_backup_postgres_creates_file -v --tb=short
poetry run pytest tests/test_backup_dr.py::TestMultiTenantIntegrity -v --tb=short
poetry run pytest tests/test_backup_dr.py::TestBackupRestoreIntegration -v --tb=short
