# PRANELY - RTO Standard

**Versión:** 1.0  
**Fecha:** 2026-04-23  
**Commit:** f0ef99114ad252f7fec99c9536e055a852726149  
**Estado:** Implementado

---

## 1. Definiciones

### 1.1 RTO-CORE (Recovery Time Objective - Core)

**Definición:** Tiempo de ejecución de `pg_restore` + verificación de datos.

**Excluye:**
- Creación de base de datos de destino
- Setup de entorno DR
- Smoke tests post-restore

**Incluye:**
- Ejecución de `pg_restore`
- Verificación de conteo de registros
- Verificación de aislamiento multi-tenant
- Validación de integridad referencial

**Target:** < 30 segundos

**Fórmula:**
```
RTO-CORE = T_restore_end - T_restore_start
```

### 1.2 RTO-E2E (Recovery Time Objective - End-to-End)

**Definición:** Tiempo end-to-end desde detección de desastre hasta recuperación completa.

**Incluye:**
- Detección de desastre
- Activación de entorno DR
- Recuperación de backup
- Verificación de datos
- Redirección de tráfico
- Smoke tests

**Target:** < 900 segundos (15 minutos)

**Fórmula:**
```
RTO-E2E = T_recovery_complete - T_disaster_detected
```

### 1.3 RPO (Recovery Point Objective)

**Definición:** Antigüedad máxima del backup restaurable.

**Target:** < 7200 segundos (2 horas)

**Fórmula:**
```
RPO = NOW - backup_timestamp
```

---

## 2. Framework de Tiempo

### 2.1 Formato de Logs

Todos los logs de DR deben usar formato consistente:

```
T+n = segundos transcurridos desde inicio del proceso
```

**Ejemplo:**
```
[T+00:00] INFO: Starting restore process
[T+00:03] CMD: pg_restore -U pranely -d pranely_restore_test backup.dump
[T+00:05] INFO: pg_restore completed
[T+00:15] STATUS: SUCCESS
```

### 2.2 Timestamp Format

```
YYYY-MM-DDTHH:MM:SSZ
```

**Ejemplo:**
```
2026-04-23T21:39:30Z
```

---

## 3. Criterios de Cumplimiento

### 3.1 RTO-CORE

| Condición | Target | Status |
|-----------|--------|--------|
| pg_restore execution | < 10s | Required |
| Data verification | < 20s | Required |
| **Total RTO-CORE** | **< 30s** | Required |

### 3.2 RTO-E2E

| Condición | Target | Status |
|-----------|--------|--------|
| Disaster detection | < 60s | Required |
| Environment activation | < 120s | Required |
| Backup retrieval | < 60s | Required |
| RTO-CORE | < 30s | Required |
| Smoke tests | < 60s | Required |
| Traffic redirect | < 60s | Required |
| **Total RTO-E2E** | **< 900s (15min)** | Required |

### 3.3 RPO

| Condición | Target | Status |
|-----------|--------|--------|
| MAX_BACKUP_AGE_HOURS | = 2 | Required |
| Backup frequency | Hourly | Required |
| **Total RPO** | **< 2 horas** | Required |

---

## 4. Verificación

### 4.1 Post-Restore Checklist

- [ ] `pg_restore` exit code = 0
- [ ] Conteo de tablas restauradas = esperado
- [ ] Conteo de registros = esperado
- [ ] Aislamiento multi-tenant verificado
- [ ] Constraints aplicados
- [ ] Foreign keys intactos
- [ ] Indices creados

### 4.2 Evidencia Requerida

Cada ejecución DR debe generar:

```
audit-evidence/4C-Backup-DR/run_YYYYMMDD_HHMMSS/
├── logs/
│   ├── backup-run.log        # T+n timestamps
│   ├── restore-rto.log      # RTO-CORE, RTO-E2E
│   ├── simulacro-dr.log     # Full simulation
│   └── rto_duration.txt    # RTO measurement
├── ci-report/
│   ├── junit.xml
│   └── coverage.xml
└── security/
    └── gitleaks-final.json
```

---

## 5. Thresholds de Alerta

| Métrica | Warning | Critical |
|---------|---------|----------|
| RTO-CORE | > 20s | > 30s |
| RTO-E2E | > 600s | > 900s |
| RPO | > 1.5h | > 2h |
| Backup size | < expected | < 1KB |

---

## 6. Implementación

### 6.1 Scripts

- `scripts/backup.sh` - Backup PostgreSQL
- `scripts/restore.sh` - Restore PostgreSQL
- `scripts/simulacro-dr.sh` - DR simulation
- `scripts/backup-healthcheck.sh` - Healthcheck con RPO

### 6.2 CI/CD

- `.github/workflows/dr-ci.yml` - DR pipeline
  - Job: unit-tests
  - Job: integration-tests
  - Job: security (gitleaks)
  - Job: dr-simulation (weekly)

### 6.3 Tests

- `packages/backend/tests/test_backup_dr.py`
  - `TestDRSimulation::test_rto_verification_logic`
  - `TestDRSimulation::test_rpo_verification_logic`

---

## 7. Historial de Mediciones

| Fecha | RTO-CORE | RTO-E2E | RPO | Status |
|-------|----------|---------|-----|--------|
| 2026-04-23 | 6s | 15s | 1.5h | ✅ COMPLIANT |

---

## 8. Referencias

- [plan-emergencia.md](./plan-emergencia.md) - Plan DR completo
- [NIST SP 800-34](https://csrc.nist.gov/publications/detail/sp/800-34/final) - Contingency Planning
- [ISO 22301](https://www.iso.org/standard/75106.html) - Business Continuity
