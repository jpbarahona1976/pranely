@echo off
REM =============================================================================
REM PRANELY - Run Worker Tests (Subfase 7A)
REM =============================================================================

cd /d "%~dp0"

echo Running 7A Worker Resilient tests...
python -m pytest tests\test_workers_rq.py -v --tb=short

if errorlevel 1 (
    echo.
    echo WARNING: Some tests failed. Check output above.
    echo Integration tests may be skipped if Redis is not available.
    exit /b 1
)

echo.
echo All unit tests passed.
exit /b 0