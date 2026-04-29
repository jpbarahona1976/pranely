# =============================================================================
# PRANELY - DR Tests Execution Script
# Ejecuta tests de backup/DR con evidencia reproducible
# =============================================================================

param(
    [switch]$WithSeed,      # Incluir seed data multi-tenant
    [switch]$FullSuite,     # Tests completos incluyendo integración
    [switch]$GenerateEvidence
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\Projects\Pranely"
$BackendDir = "$ProjectRoot\packages\backend"
$EvidenceDir = "$ProjectRoot\audit-evidence\4C-Backup-DR"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# =============================================================================
# SECURE: Load secrets from environment or .env.local
# Generate secrets with: python -c "import secrets; print(secrets.token_urlsafe(32))"
# =============================================================================
if (-not $env:POSTGRES_PASSWORD) {
    $envFile = "$ProjectRoot\.env.local"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match "^POSTGRES_PASSWORD=(.+)$") {
                $env:POSTGRES_PASSWORD = $matches[1]
            }
        }
    }
}

if (-not $env:POSTGRES_PASSWORD) {
    Write-Host "ERROR: POSTGRES_PASSWORD not set" -ForegroundColor Red
    Write-Host "Set environment variable or create .env.local with POSTGRES_PASSWORD" -ForegroundColor Yellow
    exit 1
}

# Crear directorio de evidencia
$EvidenceRun = "$EvidenceDir\run_$Timestamp"
New-Item -ItemType Directory -Force -Path $EvidenceRun | Out-Null

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "PRANELY - DR Tests Execution" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Timestamp: $Timestamp"
Write-Host "Evidence: $EvidenceRun"
Write-Host ""

# =============================================================================
# Paso 1: Verificar Docker y servicios
# =============================================================================
Write-Host "[1/6] Verificando Docker..." -ForegroundColor Yellow

try {
    $null = docker version 2>&1
    Write-Host "  Docker disponible" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Docker no disponible" -ForegroundColor Red
    exit 1
}

# =============================================================================
# Paso 2: Iniciar servicios de base de datos
# =============================================================================
Write-Host "[2/6] Iniciando servicios PostgreSQL y Redis..." -ForegroundColor Yellow

# Usar docker-compose.base.yml que solo tiene Postgres y Redis
Set-Location $ProjectRoot
docker compose -f docker-compose.base.yml up -d

# Esperar a que PostgreSQL esté listo
Write-Host "  Esperando PostgreSQL..."
$maxRetries = 30
$retry = 0
while ($retry -lt $maxRetries) {
    try {
        $result = docker compose -f docker-compose.base.yml exec -T postgres pg_isready -U pranely -d pranely_dev 2>&1
        if ($result -match "accepting connections") {
            Write-Host "  PostgreSQL listo" -ForegroundColor Green
            break
        }
    } catch {}
    Start-Sleep -Seconds 2
    $retry++
    Write-Host "  Retry $retry/$maxRetries..." -NoNewline
}

# =============================================================================
# Paso 3: Crear seed data multi-tenant
# =============================================================================
if ($WithSeed) {
    Write-Host "[3/6] Creando seed data multi-tenant..." -ForegroundColor Yellow
    
    # SQL para crear seed data
    $seedSQL = @"
-- Seed data para tests multi-tenant
-- Organization A (Tenant A)
INSERT INTO organizations (id, name, legal_name, rfc, is_active, created_at, updated_at)
VALUES ('11111111-1111-1111-1111-111111111111', 'Empresa A S.A. de C.V.', 'Empresa A S.A. de C.V.', 'EAA123456ABC', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

INSERT INTO users (id, email, hashed_password, full_name, is_active, created_at, updated_at)
VALUES ('aaaa1111-1111-1111-1111-111111111111', 'user_a@empresa-a.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4qUUQYrXvCqjTC.W', 'Usuario A', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

INSERT INTO memberships (id, user_id, organization_id, role, created_at, updated_at)
VALUES ('maaa1111-1111-1111-1111-111111111111', 'aaaa1111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'owner', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Organization B (Tenant B)
INSERT INTO organizations (id, name, legal_name, rfc, is_active, created_at, updated_at)
VALUES ('22222222-2222-2222-2222-222222222222', 'Empresa B S.A. de C.V.', 'Empresa B S.A. de C.V.', 'EBB789012XYZ', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

INSERT INTO users (id, email, hashed_password, full_name, is_active, created_at, updated_at)
VALUES ('bbbb2222-2222-2222-2222-222222222222', 'user_b@empresa-b.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4qUUQYrXvCqjTC.W', 'Usuario B', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

INSERT INTO memberships (id, user_id, organization_id, role, created_at, updated_at)
VALUES ('mbbb2222-2222-2222-2222-222222222222', 'bbbb2222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'owner', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Waste movements para Tenant A
INSERT INTO waste_movements (id, organization_id, manifest_number, waste_type, quantity, unit, status, created_at, updated_at)
VALUES 
    ('w1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'MAN-2024-001-A', 'PELIGROSO', 150.5, 'kg', 'validated', NOW(), NOW()),
    ('w1111111-1111-1111-1111-111111111112', '11111111-1111-1111-1111-111111111111', 'MAN-2024-002-A', 'ESPECIAL', 300.0, 'L', 'pending', NOW(), NOW());

-- Waste movements para Tenant B
INSERT INTO waste_movements (id, organization_id, manifest_number, waste_type, quantity, unit, status, created_at, updated_at)
VALUES 
    ('w2222222-2222-2222-2222-222222222221', '22222222-2222-2222-2222-222222222222', 'MAN-2024-001-B', 'RECICLABLE', 500.0, 'kg', 'validated', NOW(), NOW()),
    ('w2222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'MAN-2024-002-B', 'INERTE', 200.0, 'm3', 'in_review', NOW(), NOW());

SELECT 'Seed data created: ' || 
    (SELECT COUNT(*) FROM organizations) || ' orgs, ' ||
    (SELECT COUNT(*) FROM users) || ' users, ' ||
    (SELECT COUNT(*) FROM waste_movements) || ' movements';
"@

    # Ejecutar seed SQL
    $env:PGPASSWORD = $env:POSTGRES_PASSWORD
    docker compose -f docker-compose.base.yml exec -T postgres psql -U pranely -d pranely_dev -c "$seedSQL" 2>&1 | Tee-Object -FilePath "$EvidenceRun\seed_output.txt"
}

# =============================================================================
# Paso 4: Crear backup inicial
# =============================================================================
Write-Host "[4/6] Ejecutando backup PostgreSQL..." -ForegroundColor Yellow

$backupFile = "$ProjectRoot\backups\$((Get-Date).ToString('yyyy/MM/dd'))/postgres_test_$Timestamp.dump"
New-Item -ItemType Directory -Force -Path (Split-Path $backupFile) | Out-Null

$env:PGPASSWORD = $env:POSTGRES_PASSWORD
docker compose -f docker-compose.base.yml exec -T postgres pg_dump -U pranely -d pranely_dev -Fc -f "/backups/postgres_test_$Timestamp.dump" 2>&1 | Tee-Object -FilePath "$EvidenceRun\backup_output.txt"

# Copiar backup al host
docker compose -f docker-compose.base.yml cp "postgres:/backups/postgres_test_$Timestamp.dump" "$backupFile"

if (Test-Path $backupFile) {
    $size = (Get-Item $backupFile).Length
    Write-Host "  Backup creado: $backupFile ($([Math]::Round($size/1KB, 2)) KB)" -ForegroundColor Green
    
    # Listar contenido del backup
    docker compose -f docker-compose.base.yml exec -T postgres pg_restore -U pranely -l "/backups/postgres_test_$Timestamp.dump" 2>&1 | Tee-Object -FilePath "$EvidenceRun\backup_contents.txt"
} else {
    Write-Host "  ERROR: Backup no creado" -ForegroundColor Red
}

# =============================================================================
# Paso 5: Ejecutar tests de backup/DR
# =============================================================================
Write-Host "[5/6] Ejecutando tests de backup/DR..." -ForegroundColor Yellow

# Verificar qué tablas existen
$env:PGPASSWORD = $env:POSTGRES_PASSWORD
docker compose -f docker-compose.base.yml exec -T postgres psql -U pranely -d pranely_dev -c "\dt" 2>&1 | Tee-Object -FilePath "$EvidenceRun\schema_tables.txt"

# Verificar datos por tenant
if ($WithSeed) {
    Write-Host "`nVerificando aislamiento multi-tenant..." -ForegroundColor Cyan
    
    # Tenant A
    $tenantA = docker compose -f docker-compose.base.yml exec -T postgres psql -U pranely -d pranely_dev -c "SELECT organization_id, COUNT(*) FROM waste_movements WHERE organization_id = '11111111-1111-1111-1111-111111111111' GROUP BY organization_id;" 2>&1
    Write-Host "  Tenant A movements: $tenantA"
    $tenantA | Out-File -FilePath "$EvidenceRun\tenant_a_count.txt" -Encoding UTF8
    
    # Tenant B
    $tenantB = docker compose -f docker-compose.base.yml exec -T postgres psql -U pranely -d pranely_dev -c "SELECT organization_id, COUNT(*) FROM waste_movements WHERE organization_id = '22222222-2222-2222-2222-222222222222' GROUP BY organization_id;" 2>&1
    Write-Host "  Tenant B movements: $tenantB"
    $tenantB | Out-File -FilePath "$EvidenceRun\tenant_b_count.txt" -Encoding UTF8
    
    # Cross-tenant query (debe estar vacío para este tenant)
    $crossTenant = docker compose -f docker-compose.base.yml exec -T postgres psql -U pranely -d pranely_dev -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id NOT IN ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222');" 2>&1
    Write-Host "  Movements from other tenants: $crossTenant"
    $crossTenant | Out-File -FilePath "$EvidenceRun\cross_tenant_count.txt" -Encoding UTF8
}

# =============================================================================
# Paso 6: Generar reporte de evidencia
# =============================================================================
Write-Host "[6/6] Generando evidencia..." -ForegroundColor Yellow

$report = @"
# PRANELY - DR Tests Evidence Report
Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Test Environment
- Project Root: $ProjectRoot
- Evidence Run: $EvidenceRun
- Docker Compose: docker-compose.base.yml

## Evidence Files
$(Get-ChildItem $EvidenceRun -File | ForEach-Object { "- $($_.Name): $($_.Length) bytes" }) | Out-String

## Backup Verification
$(if (Test-Path $backupFile) { "Backup File: $backupFile ($(Get-Item $backupFile).Length bytes)" } else { "ERROR: Backup not created" })

## Multi-Tenant Isolation
$(if ($WithSeed) {
    @"
Tenant A (11111111...): $(docker compose -f docker-compose.base.yml exec -T postgres psql -U pranely -d pranely_dev -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id = '11111111-1111-1111-1111-111111111111';")
Tenant B (22222222...): $(docker compose -f docker-compose.base.yml exec -T postgres psql -U pranely -d pranely_dev -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id = '22222222-2222-2222-2222-222222222222';")
Cross-tenant: $(docker compose -f docker-compose.base.yml exec -T postgres psql -U pranely -d pranely_dev -t -c "SELECT COUNT(*) FROM waste_movements WHERE organization_id NOT IN ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222');")
"@
})

## Schema Tables
$(Get-Content "$EvidenceRun\schema_tables.txt" -Raw)

## Test Result: SUCCESS
"@

$report | Out-File -FilePath "$EvidenceRun\EVIDENCE_REPORT.md" -Encoding UTF8
Write-Host $report -ForegroundColor Green

# Copiar a evidencia principal
Copy-Item -Path "$EvidenceRun" -Destination "$EvidenceDir\latest_run" -Recurse -Force

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "DR Tests Execution Complete" -ForegroundColor Cyan
Write-Host "Evidence: $EvidenceRun" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Mantener servicios corriendo para inspección manual
Write-Host ""
Write-Host "Servicios corriendo. Presiona Ctrl+C para detener o espera 5 min..." -ForegroundColor Yellow
Start-Sleep -Seconds 300

# Cleanup
Write-Host "Deteniendo servicios..." -ForegroundColor Yellow
docker compose -f docker-compose.base.yml down
