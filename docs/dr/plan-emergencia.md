# PRANELY - Plan de Recuperación ante Desastres (DR)

**Versión:** 1.1  
**Fase:** 4C - Backup/DR  
**Fecha:** 2026-04-23  
**Estado:** Ejecutable
**Commit:** f0ef99114ad252f7fec99c9536e055a852726149

---

## 1. Resumen Ejecutivo

Este documento define el plan de recuperación ante desastres para PRANELY, un sistema SaaS de gestión de residuos industriales en México/LATAM. El objetivo es garantizar la continuidad del negocio con **RPO de 1 hora** y **RTO de 15 minutos**.

### 1.1 Framework de Métricas RTO

| Métrica | Definición | Target | Fórmula |
|---------|------------|--------|---------|
| **RTO-CORE** | Tiempo de ejecución de `pg_restore` + verificación de datos (excluye setup de DB) | < 30 segundos | `T_restore_end - T_restore_start` |
| **RTO-E2E** | Tiempo end-to-end completo desde detección de desastre hasta recuperación completa | < 900 segundos (15 min) | `T_recovery_complete - T_disaster_detected` |
| **RPO** | Antigüedad máxima del backup restaurable | < 2 horas | `NOW - backup_timestamp` |

### 1.2 Criterios de Éxito

| Objetivo | Meta | Medida | Status |
|----------|------|--------|--------|
| RPO (Recovery Point Objective) | 1 hora | Máximo 2h de pérdida de datos tolerable | MAX_BACKUP_AGE_HOURS=2 |
| RTO-CORE | 30 segundos | pg_restore + verificación | Medido en logs |
| RTO-E2E | 15 minutos | Tiempo total de recuperación | Medido en simulacro |

### 1.3 Logs y Evidencia

Todos los tiempos se registran en formato consistente:
```
T+n = segundos transcurridos desde inicio del proceso
Ejemplo: T+00:15 = 15 segundos después del inicio
```

Archivos de evidencia:
- `audit-evidence/4C-Backup-DR/run_*/logs/backup-run.log`
- `audit-evidence/4C-Backup-DR/run_*/logs/restore-rto.log`
- `audit-evidence/4C-Backup-DR/run_*/logs/simulacro-dr.log`
- `audit-evidence/4C-Backup-DR/run_*/logs/rto_duration.txt`

---

## 2. Arquitectura de Backup

### 2.1 Componentes Respaldados

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRANELY STACK                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐    ┌─────────┐    ┌───────────┐   ┌───────────┐  │
│  │Frontend │    │Backend  │    │ PostgreSQL│   │   Redis   │  │
│  │Next.js  │    │ FastAPI │    │    16     │   │     7     │  │
│  └─────────┘    └─────────┘    └─────┬─────┘   └─────┬─────┘  │
│                                      │               │         │
│                               ┌──────┴──────┐  ┌─────┴─────┐  │
│                               │  pg_dump    │  │  BGSAVE   │  │
│                               │  (Custom)   │  │  (RDB)    │  │
│                               └──────┬──────┘  └─────┬─────┘  │
└──────────────────────────────────────┼───────────────┼─────────┘
                                       │               │
                              ┌────────┴────────┐     │
                              │  Backup Dir     │     │
                              │  /backups/      │     │
                              │  YYYY/MM/DD/    │     │
                              │  *.dump         │     │
                              │  *.rdb          │     │
                              └─────────────────┘     │
```

### 2.2 Estrategia de Backup

| Componente | Frecuencia | Retention | Método | Formato |
|------------|------------|-----------|--------|---------|
| PostgreSQL | Cada hora (cron) | 7 días | pg_dump | Custom (-Fc) + gzip |
| Redis | Cada hora (cron) | 7 días | BGSAVE + copy | RDB binary |
| Docker Volumes | N/A | N/A | Bind mounts externos | - |

### 2.3 Estructura de Archivos

```
backups/
├── 2026/
│   └── 04/
│       └── 25/
│           ├── postgres_pranely_dev_20260425_140000.dump
│           └── redis_20260425_140000.rdb
│           ├── postgres_pranely_dev_20260425_130000.dump
│           └── redis_20260425_130000.rdb
│           └── ...
├── latest/
│   ├── postgres_pranely_dev_latest.dump -> ../2026/04/25/postgres_...
│   └── redis_latest.rdb -> ../2026/04/25/redis_...
├── logs/
│   ├── backup_20260425_140000.log
│   └── restore_20260425_143000.log
└── reports/
    └── dr_simulation_20260425_120000.txt
```

---

## 3. Procedimientos de Recovery

### 3.1 Niveles de Desastre

| Nivel | Escenario | Respuesta | RTO Estimado |
|-------|-----------|-----------|--------------|
| **L1** | Pérdida de datos menor | Restauración selectiva desde backup | 5 min |
| **L2** | Falla de base de datos | Restauración completa PG | 10 min |
| **L3** | Falla de infraestructura | Restauración completa PG + Redis | 15 min |

### 3.2 Restauración L1 (Pérdida de datos menor)

```bash
# Usar para: registro eliminado, dato corrupto
# Tiempo estimado: 5 minutos

# 1. Identificar punto de backup adecuado
ls -t backups/*/*.dump | head -1

# 2. Restaurar tabla específica (opcional)
pg_restore -h postgres -U pranely -d pranely_dev \
    --data-only \
    --table=waste_movements \
    backups/latest/postgres_latest.dump

# 3. Verificar
psql -h postgres -U pranely -d pranely_dev -c "SELECT COUNT(*) FROM waste_movements;"
```

### 3.3 Restauración L2 (Falla de base de datos)

```bash
# Usar para: PostgreSQL corrupto, disk failure
# Tiempo estimado: 10 minutos

# 1. Detener servicios
docker compose down

# 2. Ejecutar restore
./scripts/restore.sh MODE=postgres-only

# 3. Verificar
pg_isready -h postgres -U pranely -d pranely_dev
psql -h postgres -U pranely -d pranely_dev -c "SELECT COUNT(*) FROM organizations;"

# 4. Reiniciar servicios
docker compose up -d
```

### 3.4 Restauración L3 (Falla de infraestructura completa)

```bash
# Usar para: Datacenter down, ransomware
# Tiempo estimado: 15 minutos

# 1. Ejecutar restore completo
./scripts/restore.sh MODE=full

# 2. Verificar stack DR
docker compose -f docker-compose.dr.yml --profile dr up -d
docker compose -f docker-compose.dr.yml --profile dr ps

# 3. Ejecutar smoke tests
./scripts/smoke-test.sh

# 4. Switch traffic (manual)
# Actualizar DNS o load balancer
```

---

## 4. Cronogramas

### 4.1 Backup Automático (crontab)

```bash
# Editar crontab del usuario
crontab -e

# Agregar:
# Backup cada hora (RPO=1h)
0 * * * * /path/to/scripts/backup.sh >> /var/log/pranely/backup.log 2>&1

# Verificación diaria de integridad
0 3 * * * /path/to/scripts/simulacro-dr.sh rpo >> /var/log/pranely/dr_check.log 2>&1

# Simulacro mensual
0 0 1 * * /path/to/scripts/simulacro-dr.sh full >> /var/log/pranely/dr_sim.log 2>&1
```

### 4.2 Simulacro DR

| Frecuencia | Tipo | Responsable | Duración |
|------------|------|-------------|----------|
| Semanal | RPO check | CI/CD | 5 min |
| Mensual | Full DR test | DevOps | 30 min |
| Trimestral | Simulacro completo | Equipo | 2 horas |

---

## 5. Verificación y Monitoreo

### 5.1 Healthchecks de Backup

```bash
# Verificar último backup
./scripts/simulacro-dr.sh rpo

# Salida esperada:
# [INFO] RPO OK: Backup dentro de ventana de 2h
# [PASS] RPO VERIFICATION PASSED
```

### 5.2 Alertas de Fallo

| Condición | Severidad | Acción |
|-----------|-----------|--------|
| Backup falla | CRITICAL | Slack/PagerDuty: DevOps |
| Backup > 2h | HIGH | Notificación email |
| Restore falla | CRITICAL | Notificación inmediata |

### 5.3 Métricas

- `backup_duration_seconds` - Duración del backup
- `backup_size_bytes` - Tamaño del backup
- `restore_duration_seconds` - Tiempo de restauración
- `backup_age_hours` - Antigüedad del último backup
- `backup_success_rate` - Tasa de éxito de backups

---

## 6. Integridad y Validación

### 6.1 Verificación Post-Backup

Cada backup ejecuta automáticamente:

1. **pg_restore --list** - Verifica estructura del dump
2. **file command** - Verifica formato Redis RDB
3. **Checksums** - MD5/SHA256 de archivos

### 6.2 Prueba de Restauración

```bash
# Ejecutar simulacro completo
./scripts/simulacro-dr.sh full

# Criterios de éxito:
# - RPO verification: PASSED
# - RTO verification: PASSED  
# - Tables restored: > 10
# - Multi-tenancy verified: org_id filters working
```

---

## 7. Rollback y Contingencia

### 7.1 Si el Backup Falla

1. **Inmediato**: Notificar a DevOps
2. **5 min**: Verificar disco/permisos
3. **15 min**: Escalar si no se resuelve
4. **1 hora**: Plan de contingencia manual

### 7.2 Si el Restore Falla

1. **Inmediato**: No reiniciar servicios
2. **Verificar**: Logs de restore en `backups/logs/`
3. **Intentar**: Backup anterior
4. **Escalar**: Contactar DBA externo si es necesario

### 7.3 Plan de Contingencia Manual

Si todos los mecanismos automatizados fallan:

1. Conectar al servidor de base de datos directamente
2. Ejecutar pg_dump manual:
   ```bash
   PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h postgres -U pranely -d pranely_dev -Fc > emergency_backup_$(date +%Y%m%d).dump
   ```
3. Verificar integridad con `pg_restore --list`
4. Proceder con restauración manual

---

## 8. Checklist de Preparación

### 8.1 Antes del Simulacro

- [ ] Backups recientes disponibles (> 1 backup)
- [ ] Espacio en disco suficiente (> 2x tamaño DB)
- [ ] Permisos de usuario correctos
- [ ] Credenciales de base de datos accesibles
- [ ] Entorno DR verificado

### 8.2 Después del Simulacro

- [ ] RPO verificado
- [ ] RTO verificado (< 15 min)
- [ ] Multi-tenancy verificado (organization_id)
- [ ] Smoke tests passing
- [ ] Reporte generado

---

## 9. Roles y Responsabilidades

| Rol | Responsabilidad | Contacto |
|-----|----------------|----------|
| DevOps Lead | Ejecución de recuperación | juanbarahona |
| DBA | Validación de integridad | juanbarahona |
| CTO | Decisión de escalar | juanbarahona |

---

## 10. Anexos

### 10.1 Variables de Entorno Requeridas

```bash
# Requeridas para scripts DR
POSTGRES_PASSWORD=xxxxx
BACKUP_DIR=./backups
RETENTION_DAYS=7
```

### 10.2 Comandos de Emergencia

```bash
# Backup manual de emergencia
./scripts/backup.sh

# Restore rápido
./scripts/restore.sh

# Simulacro DR
./scripts/simulacro-dr.sh full
```

### 10.3 Métricas de Éxito

| Métrica | Objetivo | Mínimo Aceptable |
|---------|----------|------------------|
| Backup Success Rate | 100% | 95% |
| Restore Success Rate | 100% | 90% |
| RTO Promedio | < 10 min | < 15 min |
| RPO Real | < 1 hora | < 2 horas |

---

**Documento creado:** 2026-04-25  
**Última actualización:** 2026-04-25  
**Versión:** 1.0
