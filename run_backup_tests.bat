@echo off
set PRANELY_ROOT=C:\Projects\Pranely
set ENV=test
set SECRET_KEY=test-secret-key-for-testing-only-32chars
set DATABASE_URL=sqlite+aiosqlite:///file::memory:?cache=shared
set REDIS_URL=redis://localhost:6379
set DEBUG=false
python -m pytest packages/backend/tests/test_backup_dr.py -v --tb=short
