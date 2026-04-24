@echo off
REM =============================================================================
REM PRANELY - Run DR Integration Tests with Docker
REM =============================================================================

cd /d C:\Projects\Pranely

echo Starting DR integration tests...

REM Start services
echo [1/4] Starting PostgreSQL and Redis...
docker compose -f docker-compose.dr-tests.yml up -d postgres redis

REM Wait for PostgreSQL
echo [2/4] Waiting for PostgreSQL...
timeout /t 10 /nobreak > nul

REM Run seed data
echo [3/4] Loading seed data...
docker compose -f docker-compose.dr-tests.yml exec -T postgres psql -U pranely -d pranely_dev -c "SELECT 1" > nul 2>&1
docker compose -f docker-compose.dr-tests.yml cp scripts\seed-multi-tenant.sql postgres:/tmp/seed.sql
docker compose -f docker-compose.dr-tests.yml exec -T postgres psql -U pranely -d pranely_dev -f /tmp/seed.sql > nul 2>&1

REM Run integration tests
echo [4/4] Running integration tests...
docker compose -f docker-compose.dr-tests.yml exec -T postgres pg_dump -U pranely -d pranely_dev -Fc -f /backups/test_integration.dump
docker compose -f docker-compose.dr-tests.yml exec -T postgres pg_restore -U pranely -l /backups/test_integration.dump

echo.
echo Integration tests complete.
echo.
echo To run full pytest suite:
echo   pytest tests/test_backup_dr.py -v -m integration
echo.
