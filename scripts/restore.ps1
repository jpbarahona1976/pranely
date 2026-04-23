# =============================================================================
# PRANELY - Restore Script PowerShell (Fase 4C: Backup/DR)
# Restauración completa PostgreSQL + Redis
# RTO: 15min objetivo
# Compatible con Windows
# =============================================================================

param(
    [string]$BackupDir = ".\backups",
    [ValidateSet("full", "postgres-only", "redis-only")]
    [string]$Mode = "full",
    [switch]$SkipRedis
)

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------------------------
# Configuración
# ------------------------------------------------------------------------------
$LogDir = Join-Path $BackupDir "logs"
$RTO_START = Get-Date

# PostgreSQL
$PGHost = $env:PG_HOST ?? "localhost"
$PGPort = $env:PG_PORT ?? "5432"
$PGUser = $env:PG_USER ?? "pranely"
$PGDb = $env:PG_DB ?? "pranely_dev"

# Redis
$RedisHost = $env:REDIS_HOST ?? "localhost"
$RedisPort = $env:REDIS_PORT ?? "6379"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
function Write-Log {
    param(
        [string]$Level = "INFO",
        [string]$Message
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[${timestamp}] [${Level}] ${Message}"
    Write-Host $logLine
    
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    $logFile = Join-Path $LogDir "restore_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    Add-Content -Path $logFile -Value $logLine
}

function Get-LatestBackup {
    param([string]$Type)
    
    $extensions = @("dump", "rdb")
    $latest = $null

    foreach ($ext in $extensions) {
        $pattern = Join-Path $BackupDir "*/*.${ext}"
        $candidates = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending
        
        if ($Type -eq "postgres") {
            $latest = $candidates | Where-Object { $_.Name -like "*postgres*" } | Select-Object -First 1
        } elseif ($Type -eq "redis") {
            $latest = $candidates | Where-Object { $_.Name -like "*redis*" } | Select-Object -First 1
        }
        
        if ($latest) { break }
    }

    if (-not $latest) {
        Write-Log "ERROR" "No se encontró backup ${Type} en ${BackupDir}"
        return $null
    }

    return $latest.FullName
}

function Wait-PostgreSQLReady {
    Write-Log "INFO" "Esperando PostgreSQL listo..."
    $env:PGPASSWORD = $env:POSTGRES_PASSWORD ?? ""

    $maxRetries = 30
    for ($i = 0; $i -lt $maxRetries; $i++) {
        $result = & pg_isready -h $PGHost -p $PGPort -U $PGUser -d $PGDb 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "INFO" "PostgreSQL listo."
            return $true
        }
        Start-Sleep -Seconds 2
    }

    Write-Log "ERROR" "PostgreSQL no disponible después de 60s."
    return $false
}

function Wait-RedisReady {
    Write-Log "INFO" "Esperando Redis listo..."

    $maxRetries = 30
    for ($i = 0; $i -lt $maxRetries; $i++) {
        $pingResult = & redis-cli -h $RedisHost -p $RedisPort PING 2>&1
        if ($pingResult -match "PONG") {
            Write-Log "INFO" "Redis listo."
            return $true
        }
        Start-Sleep -Seconds 2
    }

    Write-Log "ERROR" "Redis no disponible después de 60s."
    return $false
}

function Restore-PostgreSQL {
    param([string]$BackupFile)

    Write-Log "INFO" "Iniciando restauración PostgreSQL desde: ${BackupFile}"

    if (-not (Test-Path $BackupFile)) {
        Write-Log "ERROR" "Archivo de backup no existe: ${BackupFile}"
        throw "Backup file not found"
    }

    $env:PGPASSWORD = $env:POSTGRES_PASSWORD ?? ""
    $startTime = Get-Date

    # Terminar conexiones existentes
    Write-Log "INFO" "Terminando conexiones existentes..."
    & psql -h $PGHost -p $PGPort -U $PGUser -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${PGDb}' AND pid <> pg_backend_pid();" 2>&1 | Out-Null

    # Recrear base de datos
    Write-Log "INFO" "Recreando base de datos..."
    & psql -h $PGHost -p $PGPort -U $PGUser -d postgres -c "DROP DATABASE IF EXISTS ${PGDb};" 2>&1 | Out-Null
    & psql -h $PGHost -p $PGPort -U $PGUser -d postgres -c "CREATE DATABASE ${PGDb};" 2>&1 | Out-Null

    # Restaurar backup
    Write-Log "INFO" "Restaurando backup..."
    $restoreArgs = @(
        "-h", $PGHost,
        "-p", $PGPort,
        "-U", $PGUser,
        "-d", $PGDb,
        "--clean",
        "--if-exists",
        "-v",
        $BackupFile
    )

    & pg_restore @restoreArgs 2>&1 | Tee-Object -Variable output
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR" "pg_restore falló: ${output}"
        throw "pg_restore failed"
    }

    # Verificar restauración
    $tableCountResult = & psql -h $PGHost -p $PGPort -U $PGUser -d $PGDb -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';" 2>&1
    $tableCount = [int]($tableCountResult.Trim())

    if ($tableCount -eq 0) {
        Write-Log "ERROR" "Restauración PostgreSQL falló - no se encontraron tablas."
        throw "No tables found after restore"
    }

    $duration = ((Get-Date) - $startTime).TotalSeconds
    Write-Log "INFO" "PostgreSQL restaurado. Tablas: ${tableCount}, Tiempo: ${duration}s"
}

function Restore-Redis {
    param([string]$BackupFile)

    Write-Log "INFO" "Iniciando restauración Redis desde: ${BackupFile}"

    if (-not (Test-Path $BackupFile)) {
        Write-Log "ERROR" "Archivo de backup no existe: ${BackupFile}"
        throw "Backup file not found"
    }

    # Para restaurar Redis en un entorno Docker, necesitaríamos:
    # 1. Detener el contenedor Redis
    # 2. Copiar el archivo RDB
    # 3. Reiniciar el contenedor
    # Esto es más complejo y requiere acceso Docker

    Write-Log "WARN" "Restore de Redis en PowerShell requiere Docker manual."
    Write-Log "INFO" "Para restaurar Redis manualmente:"
    Write-Log "INFO" "  1. docker stop pranely-redis"
    Write-Log "INFO" "  2. docker cp ${BackupFile} pranely-redis:/data/dump.rdb"
    Write-Log "INFO" "  3. docker start pranely-redis"
}

function Verify-Restore {
    Write-Log "INFO" "Verificando restauración completa..."

    $env:PGPASSWORD = $env:POSTGRES_PASSWORD ?? ""

    # PostgreSQL: verificar tablas
    $orgCountResult = & psql -h $PGHost -p $PGPort -U $PGUser -d $PGDb -t -c "SELECT COUNT(*) FROM organizations;" 2>&1
    Write-Log "INFO" "Organizations: ${orgCountResult}"

    $usersCountResult = & psql -h $PGHost -p $PGPort -U $PGUser -d $PGDb -t -c "SELECT COUNT(*) FROM users;" 2>&1
    Write-Log "INFO" "Users: ${usersCountResult}"

    # Redis: verificar cola (si está disponible)
    if (-not $SkipRedis) {
        $queuesResult = & redis-cli -h $RedisHost -p $RedisPort LLEN default 2>&1
        Write-Log "INFO" "RQ Queue (default): ${queuesResult}"
    }

    Write-Log "INFO" "Verificación post-restore completada."
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
function Main {
    Write-Log "INFO" "=============================================="
    Write-Log "INFO" "PRANELY Restore Script - $(Get-Date)"
    Write-Log "INFO" "Modo: ${Mode}"
    Write-Log "INFO" "=============================================="

    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }

    try {
        switch ($Mode) {
            "postgres-only" {
                if (-not (Wait-PostgreSQLReady)) { throw "PostgreSQL no disponible" }
                $pgBackup = Get-LatestBackup "postgres"
                Restore-PostgreSQL -BackupFile $pgBackup
            }
            "redis-only" {
                if (-not (Wait-RedisReady)) { throw "Redis no disponible" }
                $redisBackup = Get-LatestBackup "redis"
                Restore-Redis -BackupFile $redisBackup
            }
            "full" {
                if (-not (Wait-PostgreSQLReady)) { throw "PostgreSQL no disponible" }
                
                $pgBackup = Get-LatestBackup "postgres"
                Restore-PostgreSQL -BackupFile $pgBackup

                if (-not $SkipRedis) {
                    Restore-Redis -BackupFile (Get-LatestBackup "redis")
                }

                Verify-Restore
            }
        }

        $RTO_END = Get-Date
        $RTO_DURATION = ($RTO_END - $RTO_START).TotalSeconds

        Write-Log "INFO" "=============================================="
        Write-Log "INFO" "RESTORE COMPLETADO"
        Write-Log "INFO" "RTO: ${RTO_DURATION}s"
        Write-Log "INFO" "=============================================="

        # Verificar RTO < 15min (900s)
        if ($RTO_DURATION -gt 900) {
            Write-Log "WARN" "RTO excedió el objetivo de 15min: ${RTO_DURATION}s"
        } else {
            Write-Log "INFO" "RTO dentro del objetivo (<15min)."
        }

        exit 0
    } catch {
        Write-Log "ERROR" "Restore falló: $_"
        exit 1
    }
}

Main
