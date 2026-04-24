#!/bin/sh
cd /app
export SECRET_KEY=test-secret-key
export DATABASE_URL=postgresql+asyncpg://pranely:pranely_dev_pass@postgres:5432/pranely_dev
export REDIS_URL=redis://redis:6379
export PG_HOST=postgres
export PG_PORT=5432
export PG_USER=pranely
export PG_DB=pranely_dev
export POSTGRES_PASSWORD=pranely_dev_pass
poetry run pytest tests/test_backup_dr.py -v --cov=tests --cov-report=xml --cov-report=term --tb=short -m "integration"
