#!/bin/sh
cd /app
export SECRET_KEY=test-secret-key
export DATABASE_URL=sqlite+aiosqlite:///test.db
export REDIS_URL=redis://redis:6379

poetry run pytest tests/test_backup_dr.py tests/test_backup_dr_additional.py \
    --junitxml=/tmp/junit-final.xml \
    -v --tb=short 2>&1
