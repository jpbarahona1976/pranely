# =============================================================================
# PRANELY - Backup Script PowerShell (Fase 4C: Backup/DR)
# PostgreSQL + Redis backup automático diario
# RPO: 1h | RTO: 15min objetivo
# Compatible con Windows
# =============================================================================

param(
    [string]$BackupDir = ".\backups",
    [int]$RetentionDays = 7,
    [switch]$SkipRedis,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------------------------
# Configuración
# ------------------------------------------------------------------------------
$DateDir = Get-Date -Format "yyyy/MM/dd"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = Join-Path $BackupDir "logs"

# PostgreSQL
$PGHost = $env:PG_HOST ?? "localhost"
$PGPort = $env:PG_PORT ?? "5432"
$PGUser = $env:PG_USER ?? "pranely"
$PGDb = $env:PG_DB ?? "pranely_dev"
$PGBackupFile = "postgres_${PGDb}_${Timestamp}.dump"

# Redis
$RedisHost = $env:REDIS_HOST ?? "localhost"
$RedisPort = $env:REDIS_PORT ?? "6379"
$RedisBackupFile = "redis_${Timestamp}.rdb"

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
    $logFile = Join-Path $LogDir "backup_${Timestamp}.log"
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    Add-Content -Path $logFile -Value $logLine
}

function Test-Prerequisites {
    Write-Log "INFO" "Verificando prerrequisitos..."

    # Verificar pg_dump
    $pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
    if (-not $pgDump) {
        Write-Log "ERROR" "pg_dump no encontrado. Instalar PostgreSQL client."
        return $false
    }

    # Verificar redis-cli
    $redisCli = Get-Command redis-cli -ErrorAction SilentlyContinue
    if (-not $redisCli -and -not $SkipRedis) {
        Write-Log "WARN" "redis-cli no encontrado. Saltando backup Redis."
        $script:SkipRedis = $true
    }

    return $true
}

function Initialize-Directories {
    Write-Log "INFO" "Inicializando directorios..."

    $datePath = Join-Path $BackupDir $DateDir
    $latestPath = Join-Path $BackupDir "latest"

    @($datePath, $LogDir, $latestPath) | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
        }
    }
}

function Backup-PostgreSQL {
    Write-Log "INFO" "Iniciando backup PostgreSQL..."

    $datePath = Join-Path $BackupDir $DateDir
    $outputPath = Join-Path $datePath $PGBackupFile

    $env:PGPASSWORD = $env:POSTGRES_PASSWORD ?? ""

    # pg_dump con formato custom y compresión
    $pgDumpArgs = @(
        "-h", $PGHost,
        "-p", $PGPort,
        "-U", $PGUser,
        "-d", $PGDb,
        "-Fc",           # Formato custom para restore selectivo
        "-Z", "6",       # Compresión gzip nivel 6
        "-v",            # Verbose
        "-f", $outputPath
    )

    try {
        & pg_dump @pgDumpArgs 2>&1 | Tee-Object -Variable output
        $exitCode = $LASTEXITCODE
    } catch {
        Write-Log "ERROR" "pg_dump falló: $_"
        throw
    }

    if ($exitCode -ne 0) {
        Write-Log "ERROR" "pg_dump falló con código $exitCode"
        throw
    }

    if (-not (Test-Path $outputPath) -or (Get-Item $outputPath).Length -eq 0) {
        Write-Log "ERROR" "Backup PostgreSQL está vacío o falló."
        throw
    }

    $fileSize = (Get-Item $outputPath).Length
    Write-Log "INFO" "Backup PostgreSQL completado: ${outputPath} (${fileSize} bytes)"

    # Symlink a latest (PowerShell no tiene symlink nativo fácil, skip por ahora)
    # New-Item -ItemType SymbolicLink -Path (Join-Path $latestPath $PGBackupFile) -Target $outputPath -Force

    return $outputPath
}

function Backup-Redis {
    Write-Log "INFO" "Iniciando backup Redis..."

    $datePath = Join-Path $BackupDir $DateDir
    $outputPath = Join-Path $datePath $RedisBackupFile

    # Ejecutar BGSAVE en Redis
    try {
        $bgSaveResult = & redis-cli -h $RedisHost -p $RedisPort BGSAVE 2>&1
        Write-Log "INFO" "BGSAVE result: $bgSaveResult"
    } catch {
        Write-Log "WARN" "BGSAVE falló, intentando SAVE sincrónico..."
        & redis-cli -h $RedisHost -p $RedisPort SAVE 2>&1 | Out-Null
    }

    # Esperar a que termine el backup (máximo 30 segundos)
    $maxRetries = 30
    $lastSaveBefore = & redis-cli -h $RedisHost -p $RedisPort LASTSAVE
    $lastSaveAfter = $lastSaveBefore

    for ($i = 0; $i -lt $maxRetries; $i++) {
        Start-Sleep -Seconds 1
        $lastSaveAfter = & redis-cli -h $RedisHost -p $RedisPort LASTSAVE
        if ($lastSaveAfter -ne $lastSaveBefore) {
            Write-Log "INFO" "Redis BGSAVE completado"
            break
        }
    }

    # Obtener la ruta del archivo RDB
    $rdbPath = & redis-cli -h $RedisHost -p $RedisPort CONFIG GET dir | Select-Object -Last 1
    $rdbPath = Join-Path $rdbPath "dump.rdb"

    if (Test-Path $rdbPath) {
        Copy-Item -Path $rdbPath -Destination $outputPath -Force
    } else {
        Write-Log "ERROR" "No se encontró dump.rdb en ${rdbPath}"
        throw
    }

    if (-not (Test-Path $outputPath) -or (Get-Item $outputPath).Length -eq 0) {
        Write-Log "ERROR" "Backup Redis está vacío o falló."
        throw
    }

    $fileSize = (Get-Item $outputPath).Length
    Write-Log "INFO" "Backup Redis completado: ${outputPath} (${fileSize} bytes)"

    return $outputPath
}

function Remove-OldBackups {
    Write-Log "INFO" "Limpiando backups con más de ${RetentionDays} días..."

    $cutoffDate = (Get-Date).AddDays(-$RetentionDays)

    # Buscar archivos antiguos
    Get-ChildItem -Path $BackupDir -Recurse -Include "*.dump", "*.rdb" |
        Where-Object { $_.LastWriteTime -lt $cutoffDate } |
        Remove-Item -Force

    Write-Log "INFO" "Cleanup completado."
}

function Test-BackupIntegrity {
    param(
        [string]$PgBackupPath,
        [string]$RedisBackupPath
    )

    Write-Log "INFO" "Verificando backups..."

    # PostgreSQL: verificar con pg_restore --list
    $env:PGPASSWORD = $env:POSTGRES_PASSWORD ?? ""
    $listResult = & pg_restore -h $PGHost -p $PGPort -U $PGUser -d "postgres" --list $PgBackupPath 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR" "Verificación PostgreSQL falló: ${listResult}"
        return $false
    }

    Write-Log "INFO" "PostgreSQL backup OK"

    # Redis: verificación básica de archivo
    if ($RedisBackupPath -and (Test-Path $RedisBackupPath)) {
        $fileType = & file $RedisBackupPath 2>$null
        if ($fileType -match "Redis|RDB|data") {
            Write-Log "INFO" "Redis backup OK"
        } else {
            Write-Log "WARN" "Redis backup verificación básica"
        }
    }

    return $true
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
function Main {
    Write-Log "INFO" "=============================================="
    Write-Log "INFO" "PRANELY Backup Script - $(Get-Date)"
    Write-Log "INFO" "=============================================="

    $startTime = Get-Date

    try {
        if (-not (Test-Prerequisites)) {
            Write-Log "ERROR" "Prerrequisitos no cumplidos"
            exit 1
        }

        Initialize-Directories

        $pgBackupPath = Backup-PostgreSQL
        $redisBackupPath = $null

        if (-not $SkipRedis) {
            try {
                $redisBackupPath = Backup-Redis
            } catch {
                Write-Log "WARN" "Redis backup falló, continuando sin Redis: $_"
            }
        }

        if (-not (Test-BackupIntegrity -PgBackupPath $pgBackupPath -RedisBackupPath $redisBackupPath)) {
            Write-Log "ERROR" "Verificación de backups falló."
            exit 1
        }

        Remove-OldBackups

        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds

        Write-Log "INFO" "=============================================="
        Write-Log "INFO" "Backup completado en ${duration}s"
        Write-Log "INFO" "PostgreSQL: ${pgBackupPath}"
        Write-Log "INFO" "Redis: ${redisBackupPath ?? 'N/A'}"
        Write-Log "INFO" "=============================================="

        exit 0
    } catch {
        Write-Log "ERROR" "Backup falló: $_"
        exit 1
    }
}

Main
