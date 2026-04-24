@echo off
REM =============================================================================
REM PRANELY - Backup/DR Tests con Coverage (Fase 4C v4)
REM Genera cobertura real
REM =============================================================================

set PRANELY_ROOT=C:\Projects\Pranely
set ENV=test
set SECRET_KEY=test-secret-key-for-testing-only-32chars
set DATABASE_URL=sqlite+aiosqlite:///file::memory:?cache=shared
set REDIS_URL=redis://localhost:6379
set DEBUG=false

cd /d C:\Projects\Pranely

REM Ejecutar tests de backup/DR con coverage
python -m pytest packages/backend/tests/test_backup_dr.py packages/backend/tests/test_backup_dr_additional.py -v --cov=. --cov-report=xml:coverage-final.xml --cov-report=term-missing --cov-branch --tb=short

echo.
echo =============================================================================
echo Cobertura de tests de backup/DR ejecutada
echo Artefactos:
echo   - coverage-final.xml
echo =============================================================================
