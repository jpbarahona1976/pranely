@echo off
cd /d C:\Projects\Pranely\packages\backend
set SECRET_KEY=test-secret-key-for-testing-only-32chars
set DATABASE_URL=sqlite+aiosqlite:///file::memory:
set REDIS_URL=redis://localhost:6379
set ENV=test
set DEBUG=false
python -m pytest tests/test_backup_dr.py -v --tb=short --cov=tests --cov-report=xml
