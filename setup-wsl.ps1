# ================================================
# PRANELY.AI - Setup WSL2 + Ubuntu
# Ejecutar en PowerShell como Administrador
# =============================================

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PRANELY.AI - WSL2 Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si es Admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] Ejecutar como Administrador" -ForegroundColor Red
    exit 1
}

Write-Host "[1/5] Verificando WSL..." -ForegroundColor Yellow
$wslStatus = wsl --status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "WSL no instalado, instalando..." -ForegroundColor Yellow
} else {
    Write-Host "WSL ya instalado" -ForegroundColor Green
}

Write-Host ""
Write-Host "[2/5] Habilitando caracteristicas Windows..." -ForegroundColor Yellow
# Habilitar WSL, VirtualMachinePlatform, Hyper-V
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

Write-Host ""
Write-Host "[3/5] Descargando kernel WSL..." -ForegroundColor Yellow
wsl --update

Write-Host ""
Write-Host "[4/5] Instalando Ubuntu 24.04..." -ForegroundColor Yellow
wsl --install -d Ubuntu-24.04 --force

Write-Host ""
Write-Host "[5/5] Verificando instalacion..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
$ubuntuStatus = wsl -l -v --quiet 2>&1
Write-Host $ubuntuStatus

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  WSL2 + Ubuntu instalado!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "PROXIMOS PASOS:" -ForegroundColor Cyan
Write-Host "1. Reiniciar el equipo" -ForegroundColor White
Write-Host "2. Ejecutar: wsl" -ForegroundColor White
Write-Host "3. Crear tu usuario y contrasena de Ubuntu" -ForegroundColor White
Write-Host "4. Ejecutar el script: setup-ubuntu.sh" -ForegroundColor White
Write-Host ""
Write-Host "Descarga setup-ubuntu.sh de esta carpeta y ejecutalo" -ForegroundColor Yellow
Write-Host "dentro de Ubuntu con: bash setup-ubuntu.sh" -ForegroundColor Yellow
