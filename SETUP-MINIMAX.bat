@echo off
title = PRANELY - Configurar Minimax Chat
color 0A

echo.
echo  ============================================
echo     PRANELY - Configuracion Automatica
echo  ============================================
echo.

echo [1/3] Verificando archivos...
if not exist ".agents\skills" (
    echo ERROR: No se encontro .agents\skills
    pause
    exit /b 1
)
echo      OK - Skills encontradas

echo.
echo [2/3] Creando configuracion de VS Code...
if not exist ".vscode" mkdir ".vscode"

(
echo {
echo   "minimax.skillsFolder": ".agents^/skills",
echo   "minimax.autoLoadSkills": true,
echo   "minimax.autoReadContext": true,
echo   "minimax.contextFiles": [
echo     "PROJECT_STATE.md",
echo     "README.md",
echo     "SYSTEM_PROMPT.md"
echo   ]
echo }
) > ".vscode\settings.json"

echo      OK - Configuracion creada

echo.
echo [3/3] Subiendo cambios a GitHub...
git add .
git commit -m "Auto-config" >nul 2>&1
git push origin tmp-main >nul 2>&1

if %errorlevel% equ 0 (
    echo      OK - Subido a GitHub
) else (
    echo      ADVERTENCIA: No se pudo subir (puede que ya este actualizado)
)

echo.
echo ============================================
echo     CONFIGURACION COMPLETADA
echo ============================================
echo.
echo PASOS SIGUIENTES:
echo.
echo 1. Cierra y abre VS Code
echo 2. Abre la extension Minimax Chat
echo 3. Crea un NUEVO chat
echo.
echo Listo!
echo.
pause
