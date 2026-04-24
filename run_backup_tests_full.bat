@echo off
REM =============================================================================
REM PRANELY - Backup/DR Tests Runner (Fase 4C v4)
REM Genera junit-final.xml y coverage-final.xml
REM =============================================================================

set PRANELY_ROOT=C:\Projects\Pranely
set ENV=test
set SECRET_KEY=test-secret-key-for-testing-only-32chars
set DATABASE_URL=sqlite+aiosqlite:///file::memory:?cache=shared
set REDIS_URL=redis://localhost:6379
set DEBUG=false

cd /d C:\Projects\Pranely

REM Crear directorio de evidencia
mkdir "audit-evidence\4C-Backup-DR\run_%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%" 2>nul
set EVIDENCE_RUN=audit-evidence\4C-Backup-DR\run_latest
mkdir "%EVIDENCE_RUN%\ci-report" 2>nul
mkdir "%EVIDENCE_RUN%\logs" 2>nul

REM Ejecutar tests con coverage y junit
python -m pytest packages/backend/tests/test_backup_dr.py packages/backend/tests/test_backup_dr_additional.py -v --cov=packages.backend.tests --cov-report=xml:coverage-final.xml --cov-report=term --junit-xml:junit-final.xml --tb=short

echo.
echo =============================================================================
echo RESULTADO: Tests de backup/DR ejecutados
echo Artefactos generados:
echo   - junit-final.xml
echo   - coverage-final.xml
echo =============================================================================
