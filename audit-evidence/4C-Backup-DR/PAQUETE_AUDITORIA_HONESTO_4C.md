# PRANELY - PAQUETE DE AUDITORÍA HONESTO
## Fase 4C: Backup/DR - Estado Real del Repositorio

> **AVISO**: Este documento refleja el estado ACTUAL del repositorio sin auto-declaraciones.
> No contiene "APROBADO LIMPIO" hasta que haya evidencia objetiva verificable.

---

# SECCIÓN A: ALCANCE (AUDIT_SCOPE_4C.md)

## A.1 Identificación de Subfase

| Campo | Valor |
|-------|-------|
| **Subfase** | 4C - Backup/DR |
| **Bloque** | 4 - Datos |
| **Versión más reciente** | v1.12.0 |
| **Bloque cerrado en CHANGELOG** | 2026-04-25 |
| **Auditor宣称** | Claude Sonnet 4.6 + Nemotron (self-audit) |

## A.2 Objetivo Declarado

- RPO: 1 hora objetivo (verificable con MAX_BACKUP_AGE_HOURS=2)
- RTO: 15 minutos objetivo (trackeado en /tmp/rto_duration.txt)

## A.3 Lista Cerrada de Archivos de Fase 4C

### Scripts (ruta real: `scripts/`)

| Archivo | Ruta real | Tamaño aprox |
|---------|-----------|--------------|
| backup.sh | `scripts/backup.sh` | 7.9KB |
| backup.ps1 | `scripts/backup.ps1` | 8.5KB |
| backup-healthcheck.sh | `scripts/backup-healthcheck.sh` | 2.3KB |
| restore.sh | `scripts/restore.sh` | 10.4KB |
| restore.ps1 | `scripts/restore.ps1` | 9.0KB |
| simulacro-dr.sh | `scripts/simulacro-dr.sh` | 11.8KB |

### Docker

| Archivo | Ruta real |
|---------|----------|
| DR Compose | `docker-compose.dr.yml` (NO en subcarpeta) |

### Tests

| Archivo | Ruta real |
|---------|----------|
| Suite Backup/DR | `packages/backend/tests/test_backup_dr.py` |

### Documentación

| Archivo | Ruta real |
|---------|----------|
| Plan DR | `docs/dr/plan-emergencia.md` (subcarpeta docs/dr/) |

## A.4 Qué queda fuera explícitamente

- ❌ Evidence logs de backup/restore (no generados)
- ❌ Artifacts CI adjuntos
- ❌ Logs crudos de simulacro
- ❌ SHAs reales de commits de Fase 4C
- ❌ Reportes de seguridad (gitleaks/bandit/safety)
- ❌ Tests multi-tenant específicos para backup/restore
- ❌ RTO real medido en /tmp/rto_duration.txt

---

# SECCIÓN B: TRAZABILIDAD DE CÓDIGO (COMMITS_4C.md)

## B.1 Estado: SHAs NO disponibles

> **PROBLEMA CRÍTICO**: El repositorio no está bajo control git accesible.
> No puedo extraer SHAs reales, mensajes de commit, autores ni fechas.
> Los "xxxxxxx" en documentación anterior son placeholders inválidos.

### Lo que SÉ del repositorio (del CHANGELOG.md)

```
Versiones relacionadas:
- v1.12.0 (2026-04-25): Fase 4C Backup/DR
- v1.11.0 (2026-04-25): Fase 4B Alembic
- v1.10.0 (2026-04-24): Fase 4A Modelo datos
```

### Commits mencionados en CHANGELOG v1.12.0

| Descripción | Estado |
|------------|--------|
| config: alembic.ini formal configuration | ⚠️ Mencionado, SHA desconocido |
| env: alembic env.py with async/sync support | ⚠️ Mencionado, SHA desconocido |
| migration: 001_initial_baseline with 13 tables | ⚠️ Mencionado, SHA desconocido |
| scripts: migrate.py CLI helper (safe commands) | ⚠️ Mencionado, SHA desconocido |
| scripts: add backup/restore scripts (Fase 4C) | ⚠️ Mencionado, SHA desconocido |
| docker: add docker-compose.dr.yml | ⚠️ Mencionado, SHA desconocido |
| docs: add dr plan-emergencia.md | ⚠️ Mencionado, SHA desconocido |
| tests: add test_backup_dr.py | ⚠️ Mencionado, SHA desconocido |
| fix: rpo/rto values corrected | ⚠️ Mencionado, SHA desconocido |
| fix: restore script container params | ⚠️ Mencionado, SHA desconocido |
| fix: redis volume validation | ⚠️ Mencionado, SHA desconocido |

## B.2 PR Asociado

| Campo | Valor |
|-------|-------|
| **PR principal** | No identificado sin acceso a git |
| **Branch** | Desconocido |
| **Links** | No disponibles |

---

# SECCIÓN C: DIFF VERIFICABLE (DIFF_4C)

## C.1 Estado: Diff NO disponible

> **PROBLEMA CRÍTICO**: Sin acceso a git, no puedo generar DIFF_4C.patch.
> Lo siguiente son archivos que PUEDEN existir vs los que SÉ que existen.

### Archivos que deberían existir según CHANGELOG

```
scripts/
  backup.sh
  backup.ps1
  backup-healthcheck.sh
  restore.sh
  restore.ps1
  simulacro-dr.sh

docker-compose.dr.yml

packages/backend/tests/
  test_backup_dr.py

docs/dr/
  plan-emergencia.md
```

## C.2 Árbol ANTES (antes de Fase 4C)

Basado en CHANGELOG v1.11.0 (Fase 4B completa):

```
PRANELY/
├── scripts/
│   ├── deploy-staging.sh
│   ├── smoke-test.sh
│   ├── rollback.sh
│   └── validate-local.sh
│   (backup scripts NO existían)
├── docker-compose/
│   ├── base.yml
│   ├── dev.yml
│   ├── staging.yml
│   └── prod.yml
│   (dr.yml NO existía)
├── docs/
│   ├── BASELINE.md
│   ├── ERD.md
│   ├── NOM-151.md
│   └── migrations/
│   (docs/dr/ NO existía)
└── packages/backend/tests/
    (test_backup_dr.py NO existía)
```

## C.3 Árbol DESPUÉS (después de Fase 4C)

```
PRANELY/
├── scripts/
│   ├── deploy-staging.sh
│   ├── smoke-test.sh
│   ├── rollback.sh
│   ├── validate-local.sh
│   ├── backup.sh              ✅ nuevo
│   ├── backup.ps1             ✅ nuevo
│   ├── backup-healthcheck.sh  ✅ nuevo
│   ├── restore.sh             ✅ nuevo
│   ├── restore.ps1            ✅ nuevo
│   └── simulacro-dr.sh        ✅ nuevo
├── docker-compose.dr.yml      ✅ nuevo (raíz, NO en subcarpeta)
├── docs/dr/
│   └── plan-emergencia.md     ✅ nuevo
└── packages/backend/tests/
    └── test_backup_dr.py      ✅ nuevo
```

## C.4 Corrección de Rutas

> **CORRECCIÓN IMPORTANTE**: Las rutas son:

| Recurso | Ruta CORRECTA | Error común |
|---------|--------------|------------|
| DR Compose | `docker-compose.dr.yml` | ❌ `docker-compose/dr.yml` |
| DR Docs | `docs/dr/plan-emergencia.md` | ✅ Correcto |
| Tests | `packages/backend/tests/test_backup_dr.py` | ❌ `tests/test_backup_dr.py` |

---

# SECCIÓN D: EVIDENCIA CI (carpeta /ci/)

## D.1 Estado: NO disponible

> **DEFICENCIA**: No hay carpeta `ci/` con artifacts.

### Archivos que deberían existir para auditoría válida

| Archivo | Propósito | Estado |
|---------|----------|--------|
| ci/tests-summary.txt | Resumen de resultados | ❌ NO EXISTE |
| ci/junit.xml | Resultados estructurados | ❌ NO EXISTE |
| ci/coverage.xml | Cobertura de código | ❌ NO EXISTE |

### Afirmaciones declaradas vs realidad

| Afirmación | Declarado | Evidencia Real |
|------------|-----------|----------------|
| "17 tests PASS" | En CHANGELOG | ⚠️ Sin log adjunto |
| Cobertura 100% | Declarado | ⚠️ Sin coverage.xml |
| CI verde | Declarado | ⚠️ Sin URL de job |

### Qué SE tiene (del archivo test_backup_dr.py)

```python
# Estructura de tests detectada:
TestBackupAutomation: 4 tests
TestBackupExecution: 3 tests
TestRestoreScript: 2 tests
TestDRSimulation: 3 tests
TestMultiTenantIntegrity: 2 tests
TestDocumentation: 3 tests
---
Total declarado: 17 tests
```

> **NOTA**: El archivo de tests EXISTE en la ruta correcta. La existencia del archivo no garantiza ejecución exitosa en CI.

---

# SECCIÓN E: EVIDENCIA BACKUP/RESTORE/DR (carpeta /evidence/)

## E.1 Estado: NO disponible

> **DEFICENCIA**: No hay carpeta `evidence/` con logs de ejecución.

### Archivos que deberían existir para validar RPO/RTO

| Archivo | Propósito | Estado |
|---------|----------|--------|
| evidence/backup-run.log | Log de ejecución backup | ❌ NO EXISTE |
| evidence/restore-run.log | Log de ejecución restore | ❌ NO EXISTE |
| evidence/simulacro-dr.log | Log de simulacro DR | ❌ NO EXISTE |
| evidence/rto_duration.txt | RTO real medido | ❌ NO EXISTE |
| evidence/backup_timestamps.txt | Timestamps para RPO | ❌ NO EXISTE |

### Lo que SÉ que existe (scripts)

| Script | Ruta | Contenido verificable |
|--------|------|---------------------|
| backup-healthcheck.sh | `scripts/backup-healthcheck.sh` | MAX_BACKUP_AGE_HOURS=2 |
| restore.sh | `scripts/restore.sh` | echo "${RTO_DURATION}" > /tmp/rto_duration.txt |
| simulacro-dr.sh | `scripts/simulacro-dr.sh` | Lógica RPO/RTO |

### RPO Declarado

```bash
# En backup-healthcheck.sh
MAX_BACKUP_AGE_HOURS=2  # 1h objetivo + 1h buffer
```

### RTO Declarado

```bash
# En restore.sh
echo "${RTO_DURATION}" > /tmp/rto_duration.txt
```

> **VERIFICACIÓN PENDIENTE**: Estos valores deben ser verificados ejecutando los scripts real y midiendo tiempos.

---

# SECCIÓN F: EVIDENCIA SEGURIDAD (carpeta /security/)

## F.1 Estado: NO disponible

> **DEFICENCIA**: No hay carpeta `security/` con reportes.

### Archivos que deberían existir

| Archivo | Propósito | Estado |
|---------|----------|--------|
| security/gitleaks-report.json | Scan de secrets | ❌ NO EXISTE |
| security/bandit-report.json | SAST Python | ❌ NO EXISTE |
| security/safety-report.json | Vulnerabilidades deps | ❌ NO EXISTE |

### Afirmaciones declaradas vs realidad

| Afirmación | Declarado | Evidencia Real |
|------------|-----------|----------------|
| "gitleaks PASS" | Declarado | ⚠️ Sin reporte JSON |
| "0 secrets" | Declarado | ⚠️ Sin evidencia |
| Bandit PASS | Declarado | ⚠️ Sin reporte |

### Lo que SÉ que existe

| Recurso | Ruta |
|---------|------|
| Config gitleaks | `.gitleaks.toml` (raíz) |
| Rules gitleaks | 32+ reglas definidas |

> **VERIFICACIÓN PENDIENTE**: Ejecutar gitleaks y generar report.

---

# SECCIÓN G: AISLAMIENTO MULTI-TENANT (organization_id)

## G.1 Estado: PARCIAL

### Lo que SÉ que existe

| Recurso | Ruta |
|---------|------|
| Tests multi-org | `packages/backend/tests/test_multi_org_isolation.py` |
| Tests backup DR | `packages/backend/tests/test_backup_dr.py` |

### Tests multi-org existentes (13 tests en test_multi_org_isolation.py)

```
TestMultiOrgTenantIsolation (6 tests):
- test_user_belongs_to_both_orgs
- test_get_current_active_organization_uses_token_org_id
- test_same_user_different_org_context
- test_employer_isolation_by_org
- test_token_without_org_id_raises_403
- test_token_with_invalid_org_id_raises_403

TestMultiOrgCRUDIsolation (2 tests):
- test_create_employer_uses_token_org_id
- test_list_employers_only_returns_org_employers
```

> **PERO**: Estos tests son para API CRUD, NO para backup/restore.

### Tests de backup DR existentes (2 tests en TestMultiTenantIntegrity)

```
TestMultiTenantIntegrity:
- test_organization_id_in_backup      ⚠️ Verifica columna existe
- test_organization_id_not_null       ⚠️ Verifica NOT NULL
```

## G.2 Gap: Falta evidencia de restore multi-tenant

### Lo que NO existe

| Evidencia | Estado |
|-----------|--------|
| Test: restore con dataset org A | ❌ NO EXISTE |
| Test: restore con dataset org B | ❌ NO EXISTE |
| Test: cross-tenant restore (debe fallar) | ❌ NO EXISTE |
| Verificación conteos post-restore | ❌ NO EXISTE |

### Qué se necesitaría para cerrar el gap

```python
# test_multi_tenant_backup_restore.py (NO EXISTE)

class TestMultiTenantBackupRestore:
    async def test_restore_preserves_org_a_data(self, ...):
        """Restore debe mantener datos de org A"""
        pass
    
    async def test_restore_preserves_org_b_data(self, ...):
        """Restore debe mantener datos de org B"""
        pass
    
    async def test_cross_tenant_restore_blocked(self, ...):
        """Restore no debe permitir acceso cross-tenant"""
        pass
    
    async def test_org_counts_match_after_restore(self, ...):
        """Conteos por org_id deben ser iguales post-restore"""
        pass
```

---

# SECCIÓN H: DOCUMENTACIÓN OPERATIVA

## H.1 Estado: EXISTE pero no verificable

### Documentación existente

| Documento | Ruta | Contenido |
|-----------|------|----------|
| Plan DR | `docs/dr/plan-emergencia.md` | 9.9KB |
| Alembic Guide | `docs/migrations/alembic-guide.md` | 4.3KB |

### Consistencia de rutas

| Documento | Ruta en docs | Consistencia |
|-----------|-------------|-------------|
| Plan DR | `docs/dr/plan-emergencia.md` | ✅ Correcto |
| RPO en doc | 2h | ✅ Coincide con scripts |
| RTO en doc | 15min | ✅ Coincide con scripts |

### Runbook mínimo necesario (no existe como documento)

```
# RUNBOOK_4C.md (NO EXISTE)

## 1. Backup
```bash
./scripts/backup.sh
```
PASS: backup-{timestamp}.dump existe en backup_dir/latest

## 2. Restore
```bash
./scripts/restore.sh backup-{timestamp}.dump
```
PASS: /tmp/rto_duration.txt < 900 segundos

## 3. Simulacro DR
```bash
./scripts/simulacro-dr.sh
```
PASS: RPO check OK, RTO < 900s

## Criterios
| Criterio | Umbral | Medición |
|----------|--------|----------|
| RPO | ≤ 2 horas | MAX_BACKUP_AGE_HOURS |
| RTO | ≤ 15 min | /tmp/rto_duration.txt |
```

---

# SECCIÓN I: ESTRUCTURA DE ENTREGA REAL

## I.1 Lo que EXISTE actualmente

```
C:\Projects\Pranely\audit-evidence\4C-Backup-DR\
├── PAQUETE_AUDITORIA_4C.md     ⚠️ Auto-declaración (INVÁLIDO)
├── AUDIT_REPORT.md              ⚠️ Auto-declaración (INVÁLIDO)
├── DIFF_CONSOLIDADO.md          ⚠️ SHAs placeholder (INVÁLIDO)
├── REFERENCE.md                 ⚠️ Placeholders (INVÁLIDO)
└── SUBFASE_SCOPE.md             ⚠️ Auto-declaración (INVÁLIDO)
```

## I.2 Lo que DEBERÍA existir para auditoría válida

```
C:\Projects\Pranely\audit-evidence\4C-Backup-DR\
├── AUDIT_SCOPE_4C.md            ✅ Este documento
├── COMMITS_4C.md                ⚠️ SHAs no disponibles
├── DIFF_4C.patch                ❌ No generado
├── TREE_BEFORE.txt              ❌ No generado
├── TREE_AFTER.txt               ❌ No generado
│
├── /ci/                         ❌ Carpeta no existe
│   ├── tests-summary.txt         ❌ No existe
│   ├── junit.xml                 ❌ No existe
│   └── coverage.xml              ❌ No existe
│
├── /evidence/                   ❌ Carpeta no existe
│   ├── backup-run.log           ❌ No existe
│   ├── restore-run.log           ❌ No existe
│   ├── simulacro-dr.log          ❌ No existe
│   ├── rto_duration.txt          ❌ No existe
│   └── backup_timestamps.txt     ❌ No existe
│
├── /security/                   ❌ Carpeta no existe
│   ├── gitleaks-report.json      ❌ No existe
│   ├── bandit-report.json         ❌ No existe
│   └── safety-report.json        ❌ No existe
│
├── /tests/                      ❌ Carpeta no existe
│   └── test_multi_tenant_backup_restore.py  ❌ No existe
│
├── RUNBOOK_4C.md                ❌ No existe
└── GAPS.md                      ✅ Este documento es parte
```

---

# SECCIÓN J: RESUMEN DE GAPS

## J.1 Gaps Críticos (bloquean auditoría)

| Gap | Severidad | Evidencia faltante |
|-----|----------|-------------------|
| SHAs reales | 🔴 CRÍTICA | COMMITS_4C.md con SHA válidos |
| Artifacts CI | 🔴 CRÍTICA | /ci/ con junit.xml, coverage.xml |
| Logs de simulacro | 🔴 CRÍTICA | /evidence/ con logs crudos |
| RTO real medido | 🔴 CRÍTICA | /evidence/rto_duration.txt |
| Tests multi-tenant restore | 🔴 CRÍTICA | test_multi_tenant_backup_restore.py |

## J.2 Gaps Altos

| Gap | Severidad | Evidencia faltante |
|-----|----------|-------------------|
| Diff del PR | 🟠 ALTA | DIFF_4C.patch |
| Árbol antes/después | 🟠 ALTA | TREE_*.txt |
| Reportes seguridad | 🟠 ALTA | /security/ con reportes |
| Runbook | 🟠 ALTA | RUNBOOK_4C.md |

## J.3 Gaps Medios

| Gap | Severidad |
|-----|----------|
| URL job CI | 🟡 MEDIA |
| Links PR | 🟡 MEDIA |

---

# SECCIÓN K: DICTAMEN PRELIMINAR

## K.1 Estado actual del proyecto

| Aspecto | Evaluación |
|--------|------------|
| **Código implementado** | ✅ Existe (scripts, tests, docs) |
| **Rutas coherentes** | ✅ Corregidas en este documento |
| **Auto-declaraciones** | ❌ Eliminadas |
| **Evidencia objetiva** | ❌ NO EXISTE |

## K.2 Dictamen

```
╔════════════════════════════════════════════════════════════╗
║  DICTAMEN PRELIMINAR: PENDIENTE DE EVIDENCIA              ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  El código de Fase 4C EXISTE y PARECE correctamente        ║
║  implementado según CHANGELOG.md.                          ║
║                                                            ║
║  SIN EMBARGO, no se puede emitir dictamen formal porque:   ║
║                                                            ║
║  1. No hay SHAs trazables al código                       ║
║  2. No hay artifacts CI verificables                      ║
║  3. No hay logs crudos de simulacro                       ║
║  4. No hay evidencia de RTO real medido                   ║
║  5. No hay tests de restore multi-tenant                   ║
║                                                            ║
║  HASTA QUE ESTOS GAPS SEAN CERRADOS:                      ║
║                                                            ║
║  ⚠️ NO SE PUEDE EMITIR "APROBADO LIMPIO"                   ║
║  ⚠️ NO SE PUEDE EMITIR "APROBADO CON OBSERVACIONES"        ║
║  ⚠️ NO SE PUEDE EMITIR "RECHAZADO"                         ║
║                                                            ║
║  ÚNICO DICTAMEN POSIBLE: PENDIENTE DE EVIDENCIA           ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

## K.3 Acciones requeridas para cerrar gaps

### Para obtener SHAs reales:
```bash
# Ejecutar en el repo PRANELY
git log --oneline --all | grep -i "4C\|backup\|dr"
```

### Para generar artifacts CI:
```bash
# Ejecutar tests y guardar resultados
pytest --junitxml=ci/junit.xml --cov=app --cov-report=xml
```

### Para generar evidencia de simulacro:
```bash
# Ejecutar simulacro y capturar logs
./scripts/simulacro-dr.sh 2>&1 | tee evidence/simulacro-dr.log
```

### Para generar evidencia multi-tenant:
```bash
# Crear y ejecutar tests de restore multi-tenant
pytest tests/test_multi_tenant_backup_restore.py -v
```

---

# SECCIÓN L: CRITERIOS PARA CAMBIAR DICTAMEN

## L.1 Checklist de evidencia requerida

- [ ] SHAs reales de commits de Fase 4C en COMMITS_4C.md
- [ ] URL de job CI con commit exacto
- [ ] /ci/junit.xml con resultados de tests
- [ ] /ci/coverage.xml con porcentaje de cobertura
- [ ] /evidence/simulacro-dr.log con tiempos reales
- [ ] /evidence/rto_duration.txt con RTO medido < 15min
- [ ] /security/gitleaks-report.json sin findings
- [ ] test_multi_tenant_backup_restore.py con 4+ tests passing
- [ ] Verificación de conteos post-restore por organization_id

## L.2 Cuando todos los criterios estén cumplidos

El dictamen cambiará automáticamente a:

✅ **APROBADO LIMPIO** (si todos los criterios son verdes)
✅ **APROBADO CON OBSERVACIONES** (si hay hallazgos menores)
❌ **RECHAZADO** (si hay hallazgos críticos)

---

# SECCIÓN M: DOCUMENTO GENERADO

| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-04-25 |
| **Autor** | Claude (revisión honesta) |
| **Propósito** | Gap analysis y transparencia |
| **Dictamen** | PENDIENTE DE EVIDENCIA |

---

*Este documento es una autoevaluación honesta y NO reemplaza una auditoría externa real.*
*El implementador no puede fechar su propia subfase sin evidencia independiente.*
