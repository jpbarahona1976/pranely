# PRANELY - PAQUETE DE AUDITORÍA REAL
## Fase 4C: Backup/DR - Evidencia Objetiva

> **FECHA**: 2026-04-25
> **AUDITOR**: Claude (análisis objetivo)
> **ESTADO**: RECHAZADO - Hallazgos críticos encontrados

---

# SECCIÓN 1: TRAZABILIDAD DE CÓDIGO

## 1.1 SHA Real del Commit de Fase 4C

| Campo | Valor |
|-------|-------|
| **SHA** | `f0ef99114ad252f7fec99c9536e055a852726149` |
| **Autor** | DevSecOps <devsecops@pranely.dev> |
| **Fecha** | 2026-04-23 11:20:27 -0700 |
| **Mensaje** | `feat(backup-dr): fase 4C hardening 4/4 fixes APROBADO LIMPIO [closes #4C]` |
| **PR** | `#4C` |
| **Link** | https://github.com/jpbarahona1976/pranely/commit/f0ef99114ad252f7fec99c9536e055a852726149 |

## 1.2 SHA Base (antes de Fase 4C)

| Campo | Valor |
|-------|-------|
| **SHA** | `f2ea522` |
| **Mensaje** | `feat(migrations): fase 4B alembic hardened 277/277 tests [closes #4B]` |

## 1.3 Archivos del Diff (git diff f2ea522..f0ef991)

```
19 files changed, 2959 insertions(+), 6 deletions(-)

packages/backend/app/api/health.py                 |   6 +-
packages/backend/backups/2026/04/13/test_old.dump  |   1 +
packages/backend/backups/2026/04/23/postgres_recent.dump        |   1 +
packages/backend/tests/test_backup_dr.py           | 459 +++++++++++++++++++++
scripts/backup-healthcheck.sh                      |  83 ++++
scripts/backup.ps1                                 | 282 +++++++++++++
scripts/backup.sh                                  | 247 +++++++++++
scripts/restore.ps1                                | 274 ++++++++++++
scripts/restore.sh                                 | 320 ++++++++++++++
scripts/simulacro-dr.sh                            | 354 ++++++++++++++++
docker-compose.dr.yml                              | 111 +++++
docs/dr/plan-emergencia.md                         | 334 +++++++++++++++
CHANGELOG.md                                       | 128 +++++-
```

---

# SECCIÓN 2: EVIDENCIA CI - TESTS

## 2.1 Resumen de Tests (Ejecutados Localmente)

**Archivo**: `packages/backend/tests/test_backup_dr.py`
**Fecha ejecución**: 2026-04-25
**Entorno**: Windows + Python 3.12.7

```
RESULTADO: 9 failed, 11 passed, 2 skipped

═══════════════════════════════════════════════════════════════════
FAILED tests:
═══════════════════════════════════════════════════════════════════

1. test_backup_healthcheck_rpo_compliance
   - AssertionError: '2' not in '="${'
   - CAUSA: Test busca '2' después de MAX_BACKUP_AGE_HOURS pero el script usa variable

2. test_backup_retention_policy
   - AssertionError: 0.0 > 604800
   - CAUSA: Test crea archivo y compara edad, pero archivo es nuevo (0 segundos)

3. test_pg_dump_available
   - FileNotFoundError: pg_dump not found in PATH
   - CAUSA: PostgreSQL no instalado en local (esperado en CI real)

4. test_backup_postgres_creates_file
   - FileNotFoundError: pg_dump not found in PATH
   - CAUSA: PostgreSQL no instalado en local

5. test_organization_id_in_backup
   - FileNotFoundError: psql not found in PATH
   - CAUSA: PostgreSQL no instalado en local

6. test_organization_id_not_null
   - FileNotFoundError: psql not found in PATH
   - CAUSA: PostgreSQL no instalado en local

7. test_dr_plan_has_rpo_rto
   - UnicodeDecodeError: 'charmap' can't decode byte 0x81
   - CAUSA: Documento tiene caracteres UTF-8 no manejados por Windows

8. test_dr_plan_has_checklist
   - UnicodeDecodeError: 'charmap' can't decode byte 0x81
   - CAUSA: Documento tiene caracteres UTF-8 no manejados por Windows

9. test_backup_restore_cycle
   - FileNotFoundError: pg_dump not found in PATH
   - CAUSA: PostgreSQL no instalado en local

═══════════════════════════════════════════════════════════════════
SKIPPED tests:
═══════════════════════════════════════════════════════════════════

1. test_redis_cli_available
   - redis-cli not found in PATH

2. test_pg_restore_lists_backup
   - No backup files found

═══════════════════════════════════════════════════════════════════
PASSED tests:
═══════════════════════════════════════════════════════════════════

1. test_backup_script_exists ✓
2. test_backup_directory_structure ✓
3. test_restore_script_exists ✓
4. test_restore_writes_rto_duration_file ✓
5. test_dr_compose_file_exists ✓
6. test_dr_script_exists ✓
7. test_rpo_verification_logic ✓
8. test_rto_verification_logic ✓
9. test_dr_plan_exists ✓
10. test_backup_log_directory ✓
11. test_backup_reports_directory ✓
```

## 2.2 Clasificación de Fallos

| Tipo | Count | Bloqueante | Descripción |
|------|-------|-----------|-------------|
| **Ambiental** | 6 | ⚪ No | pg_dump/psql no en PATH local |
| **Test Bug** | 3 | ⚪ No | Assertions incorrectas |
| **Encoding** | 2 | 🟠 Medio | UTF-8 no manejado |
| **SKIPPED** | 2 | ⚪ No | Redis/backup no disponibles |

## 2.3 Cobertura

No disponible - pytest-cov no instalado en entorno local.

---

# SECCIÓN 3: EVIDENCIA SEGURIDAD - GITLEAKS

## 3.1 Resultado Gitleaks

```
╔══════════════════════════════════════════════════════════════╗
║  GITLEAKS SCAN RESULT                                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Commits scanned: 34                                        ║
║  Bytes scanned: ~4.48 MB in 641ms                            ║
║  Leaks found: 18                                            ║
║                                                              ║
║  ❌ AUDITORÍA RECHAZADA - SECRETOS DETECTADOS                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

## 3.2 Detalle de Leaks Encontrados

### HIGH SEVERITY - Connection Strings

| Archivo | Línea | Tipo | Descripción |
|---------|-------|------|-------------|
| `packages/backend/app/core/config.py` | 5 | connection-string | postgresql:// URL en código |
| `docker-compose.prod.yml` | 141 | pranely-redis-password | REDIS_URL expuesta |
| `docker-compose.staging.yml` | 68 | pranely-redis-password | REDIS_URL expuesta |

### MEDIUM SEVERITY - Generic Passwords (12 instances)

Los siguientes scripts déclencharon `generic-password` en líneas que usan `PGPASSWORD`:
- `scripts/backup.sh` (línea 76)
- `scripts/restore.sh` (líneas 70, 115, 122, 124, 130, 144, 241, 245)
- `scripts/simulacro-dr.sh` (líneas 194, 204, 264)

**NOTA**: Estos son FALSOS POSITIVOS - las variables `${PGPASSWORD}` son referências a entorno, no secrets hardcodeados.

---

# SECCIÓN 4: ESTRUCTURA DE ARCHIVOS

## 4.1 Árbol ANTES (commit f2ea522)

Ver archivo adjunto: `TREE_BEFORE.txt`

## 4.2 Árbol DESPUÉS (commit f0ef991)

Ver archivo adjunto: `TREE_AFTER.txt`

## 4.3 Diff Completo

Ver archivo adjunto: `DIFF_4C.patch`

---

# SECCIÓN 5: GAPS IDENTIFICADOS

## 5.1 Gaps Críticos (Bloquean Aprobación)

| Gap | Severidad | Evidencia Faltante |
|-----|----------|-------------------|
| Secrets detectados | 🔴 CRÍTICA | 18 leaks gitleaks (algunos son falsos positivos pero deben verificarse) |
| Tests fallando | 🔴 CRÍTICA | 9 failed, assertions incorrectas |
| Encoding docs | 🟠 ALTA | UTF-8 no manejado por Windows |

## 5.2 Gaps Medios

| Gap | Severidad |
|-----|----------|
| No hay junit.xml | 🟡 MEDIA |
| No hay coverage.xml | 🟡 MEDIA |
| No hay URL CI real | 🟡 MEDIA |
| No hay logs backup/restore/crudos | 🟡 MEDIA |
| No hay RTO real medido | 🟡 MEDIA |

## 5.3 Gaps Pendientes (requieren CI real)

| Gap | Descripción |
|-----|-------------|
| pg_dump/psql disponibles | Solo en Docker/CI real |
| Backup real ejecutable | Requiere PostgreSQL |
| Restore real ejecutable | Requiere PostgreSQL |
| Simulacro DR real | Requiere infraestructura completa |

---

# SECCIÓN 6: ANÁLISIS DE FALSOS POSITIVOS GITLEAKS

## 6.1 Análisis de Scripts DR

Los 12 findings en scripts .sh son **FALSOS POSITIVOS**:

```bash
# Este es un FALSO POSITIVO (gitleaks mal configurado)
PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump ...

# El secret real está en variable de entorno, no hardcodeado
# Gitleaks debería usar allowlist o regex más precisa
```

## 6.2 Recomendación

Agregar al `.gitleaks.toml`:

```toml
[allowlist]
paths = [
  'scripts/backup\.sh',
  'scripts/restore\.sh',
  'scripts/simulacro-dr\.sh',
]
regexes = [
  'PGPASSWORD="\${[^}]+}"',
]
```

---

# SECCIÓN 7: DICTAMEN FINAL

```
╔══════════════════════════════════════════════════════════════════════╗
║  DICTAMEN: RECHAZADO                                                ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  CRITERIOS CUMPLIDOS:                                                ║
║  ✓ SHA trazable: f0ef99114ad252f7fec99c9536e055a852726149            ║
║  ✓ Diff generable: DIFF_4C.patch creado                              ║
║  ✓ Árboles: TREE_BEFORE.txt, TREE_AFTER.txt creados                  ║
║  ✓ Tests ejecutables: 22 tests collected                              ║
║  ✓ Scripts existen: backup.sh, restore.sh, simulacro-dr.sh           ║
║                                                                      ║
║  CRITERIOS NO CUMPLIDOS:                                             ║
║  ✗ Gitleaks: 18 leaks encontrados                                    ║
║  ✗ Tests: 9 failed (3 bugs de test, 6 ambientales)                    ║
║  ✗ Docs: UnicodeDecodeError en plan-emergencia.md                    ║
║  ✗ CI real: Sin junit.xml, coverage.xml                              ║
║  ✗ Evidencia: Sin logs crudos, sin RTO real                           ║
║  ✗ Multi-tenant restore: No existe test dedicado                     ║
║                                                                      ║
║  HALLAZGO CRÍTICO:                                                    ║
║  - connection-string en config.py (REAL)                             ║
║  - REDIS_URL expuesta en docker-compose (REAL)                        ║
║                                                                      ║
║  HALLAZGOS MEDIOS (FALSOS POSITIVOS):                                 ║
║  - 12x PGPASSWORD en scripts (FALSO POSITIVO)                       ║
║                                                                      ║
║  ACCIONES REQUERIDAS:                                                 ║
║  1. Remover connection-string de config.py                            ║
║  2. Configurar .env para REDIS_URL                                    ║
║  3. Corregir assertions en test_backup_dr.py                         ║
║  4. Agregar encoding='utf-8' a read_text()                            ║
║  5. Configurar allowlist gitleaks para variables                       ║
║  6. Ejecutar en CI real con PostgreSQL                               ║
║  7. Generar evidencia RPO/RTO real                                   ║
║                                                                      ║
║  DICTAMEN: RECHAZADO hasta que se cumplan criterios de cierre        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

# SECCIÓN 8: ARCHIVOS ADJUNTOS

```
audit-evidence/4C-Backup-DR/
├── PAQUETE_AUDITORIA_REAL_4C.md      ← Este documento
├── COMMITS_4C.txt                   ← SHA real
├── COMMIT_F0EF991.txt                ← Detalle commit
├── DIFF_4C.patch                     ← Diff completo
├── TREE_BEFORE.txt                   ← Árbol antes
├── TREE_AFTER.txt                    ← Árbol después
├── ci/
│   └── tests-summary.txt             ← Resultado tests
├── security/
│   └── gitleaks-report.json          ← Reporte gitleaks
├── evidence/
│   └── (vacío - sin logs crudos)
└── docs/
    └── (referencia a docs/dr/)
```

---

# SECCIÓN 9: PRÓXIMOS PASOS

## 9.1 Para obtener RECHAZADO → APROBADO CON OBSERVACIONES

1. **Secrets**:
   - [ ] Remover `postgresql://pranely:changeme@localhost` de config.py
   - [ ] Mover REDIS_URL a variable de entorno en docker-compose
   - [ ] Agregar allowlist gitleaks para variables válidas

2. **Tests**:
   - [ ] Corregir `test_backup_healthcheck_rpo_compliance` assertion
   - [ ] Corregir `test_backup_retention_policy` - usar timestamps fijos
   - [ ] Agregar encoding='utf-8' a todos los `read_text()`

3. **CI Real**:
   - [ ] Ejecutar en GitHub Actions con PostgreSQL
   - [ ] Generar junit.xml
   - [ ] Generar coverage.xml

## 9.2 Para obtener APROBADO CON OBSERVACIONES → APROBADO LIMPIO

1. **Evidencia RPO/RTO**:
   - [ ] Log de backup real con timestamp
   - [ ] Log de restore real con RTO < 15min
   - [ ] Log de simulacro DR

2. **Multi-tenant**:
   - [ ] Test `test_multi_tenant_backup_restore.py`
   - [ ] Verificación conteos org_id post-restore

---

**Generado**: 2026-04-25
**Auditor**: Claude (análisis objetivo)
**Dictamen**: RECHAZADO
