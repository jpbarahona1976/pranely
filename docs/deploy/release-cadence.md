# PRANELY - Release Cadence

**Versión:** 1.0  
**Fecha:** 2026-04-23  
**Estado:** Aprobado  
**Owner:** Engineering Lead  
**Fase:** 2C

---

## 1. Resumen Ejecutivo

Documento define la cadencia de releases para PRANELY: frecuencia, tipos de releases, gates de calidad, y calendario de mantenimiento.

---

## 2. Tipos de Release

### 2.1 Release Types

| Tipo | Frecuencia | Scope | Risk | Ejemplo |
|------|------------|-------|------|---------|
| **Hotfix** | Emergency | 1-2 cambios críticos | Alto | Security patch, crash fix |
| **Patch** | Weekly (Mié) | Bug fixes, minor improvements | Medio | Fix bugs, improve perf |
| **Minor** | Bi-weekly (Vie) | New features, enhancements | Bajo | New endpoint, UI improvement |
| **Major** | Monthly (1er Vie) | Breaking changes, large features | Bajo | New domain, architecture changes |

### 2.2 Release Windows

| Día | Hora (CDMX) | Actividad |
|-----|-------------|-----------|
| Lunes | 09:00 | Code freeze para minor/patch |
| Miércoles | 10:00 | Release patch (si hay cambios) |
| Viernes | 14:00 | Release minor |
| 1er Viernes | 14:00 | Release major |
| Emergencias | On-call | Hotfix (cualquier momento) |

### 2.3 Downtime Windows

**Mantenimiento planificado:**
- Martes 02:00-04:00 CDMX (8:00-10:00 UTC)
- Notificación 48h antes mínimo

**Deploy window producción:**
- Martes y Jueves 03:00-05:00 CDMX
- Ideal: mínimo tráfico

---

## 3. Cadencia Detallada

### 3.1 Weekly Cadence

```
LUNES (09:00 CDMX)
├── Code freeze minor/patch
├── Tag release branch (release/X.Y.Z)
├── Notificar equipo en #releases
└── Actualizar CHANGELOG draft

MARTES (reserva)
└── Mantenimiento si necesario

MIÉRCOLES (10:00 CDMX)
├── Verificar CI verde
├── Si hay fixes: release patch
│   ├── Tag: v1.6.1
│   ├── CHANGELOG.md
│   ├── Deploy staging
│   ├── Smoke tests
│   └── Si OK → deploy prod
└── Si no hay cambios: skip

JUEVES (reserva)
└── Deploy prod si no hacerlo Miércoles

VIERNES (14:00 CDMX)
├── Verificar CI verde
├── Release minor
│   ├── Tag: v1.7.0
│   ├── CHANGELOG.md
│   ├── Test smoke completos
│   ├── Deploy staging
│   ├── Canary 5% tráfico
│   ├── Monitor 1h
│   └── Si OK → deploy prod 100%
└── No hacer deploy después 16:00
```

### 3.2 Bi-Weekly Full Cycle

```
SEMANA 1: Development + Testing
├── Lunes: Planning + start sprint
├── Martes-Jueves: Development
├── Viernes: PR review + merge
│   └── Requerir 2 approvals
└── Sábado-Domingo: Optional hotfix

SEMANA 2: Staging + Release
├── Lunes: Deploy staging + testing
├── Martes: Bug fixes staging
├── Miércoles: Release patch (si hay)
├── Jueves: UAT + smoke tests
├── Viernes: Release minor
│   ├── 2pm: Deploy staging
│   ├── 3pm: Canary 5%
│   ├── 4pm: Full deploy
│   └── 5pm: Monitor + celebrations
└── No deploy después 4pm Viernes
```

### 3.3 Monthly Major Release

```
SEMANA -2: Feature Freeze
├── Lunes: Feature freeze
├── Martes: Start regression testing
├── Miércoles: Fix critical bugs
├── Jueves: UAT con stakeholders
└── Viernes: Release candidate tag

SEMANA -1: RC Testing
├── Lunes: RC deployed to staging
├── Martes-Jueves: Full regression
├── Miércoles: Security audit
├── Jueves: Performance testing
└── Viernes: Final RC approved

SEMANA 0: Major Release
├── Lunes: Final preparations
├── Martes: Comms sent to users
├── Miércoles: Pre-deploy backup
├── Jueves: Rollback plan ready
├── Viernes (1er del mes):
│   ├── 9am: Final checks
│   ├── 2pm: Deploy major
│   ├── 3pm: Monitor closely
│   └── 5pm: Success确认
└── Post-release: Monitor 72h closely
```

---

## 4. Gates de Calidad

### 4.1 Pre-Deploy Gates

| Gate | Criterio | Herramienta | Owner |
|------|----------|-------------|-------|
| Lint | 0 errores | ruff, ESLint | CI |
| Typecheck | 0 errores | mypy, TS | CI |
| Unit tests | >80% coverage | pytest | CI |
| Integration | All passing | pytest | CI |
| Security scan | 0 critical | Semgrep | CI |
| Secrets scan | 0 secrets | Gitleaks | CI |
| Code review | 2 approvals | GitHub | Team |
| CHANGELOG | Actualizado | Manual | Dev |

### 4.2 Staging Gates

| Gate | Criterio | Timeout | Blocker |
|------|----------|---------|---------|
| Health deep | 200 OK | 30s | Sí |
| Smoke auth | Login funciona | 30s | Sí |
| Smoke CRUD | CRUD funciona | 30s | Sí |
| Tenant isolation | No cross-data | 30s | Sí |
| Performance | p95 < 500ms | 5min | Sí |
| Load test | < 1% error rate | 10min | No |
| Manual QA | Sign-off QA | 1h | Sí |

### 4.3 Production Gates

| Gate | Criterio | Timeout | Blocker |
|------|----------|---------|---------|
| Staging passed | Todos staging gates | - | Sí |
| On-call ready | DevOps available | - | Sí |
| Communication | Users notified | - | Sí |
| Rollback ready | Scripts tested | - | Sí |
| Monitoring active | Dashboard visible | - | Sí |
| Canary | 5% tráfico OK 15min | 15min | Sí |
| Full deploy | Canary passed | - | Sí |
| Post-deploy | No regressions 1h | 1h | Sí |

---

## 5. Versionamiento

### 5.1 SemVer Strategy

```
v{Major}.{Minor}.{Patch}

Major: Breaking changes (v2.0.0)
Minor: New features (v1.7.0)
Patch: Bug fixes (v1.6.1)
```

### 5.2 Ejemplos

- v1.6.0: Minor release, nueva funcionalidad
- v1.6.1: Patch, bug fix
- v1.6.2: Patch, security fix
- v2.0.0: Major, breaking changes

### 5.3 Tags

```bash
# Minor/Patch
git tag -a v1.6.0 -m "Release 1.6.0"
git push origin v1.6.0

# Major
git tag -a v2.0.0 -m "Major release - breaking changes"
git push origin v2.0.0
```

---

## 6. Changelog Policy

### 6.1 Formato

```markdown
## [1.6.0] - 2026-04-25

> **[CATEGORÍA] Título descriptivo**

### Added
- Nueva funcionalidad X

### Changed
- Mejora existente Y

### Fixed
- Bug Z corregido

### Security
- Actualización de dependencia A
```

### 6.2 Categorías

- **BREAKING:** Cambios que rompen backward compatibility
- **FEATURE:** Nuevas funcionalidades
- **IMPROVEMENT:** Mejoras de performance/UX
- **BUGFIX:** Corrección de bugs
- **SECURITY:** Patches de seguridad
- **DEP:** Actualización de dependencias

### 6.3 Política

- Actualizar CHANGELOG.md en cada PR
- PR no mergeable si CHANGELOG no actualizado
- Revisar changelog antes de release

---

## 7. Communication Plan

### 7.1 Notificaciones

| Release Type |advance Notice | Channels |
|--------------|---------------|----------|
| Major | 2 semanas | Email + Slack + Blog |
| Minor | 1 semana | Slack #releases |
| Patch | 1 día | Slack #releases |
| Hotfix | Inmediato | Slack #incidents |

### 7.2 Templates

**Minor/Release announcement:**

```markdown
📦 PRANELY v1.7.0 Released

**Fecha:** [DATE]
**Type:** Minor
**Highlights:**
- [Feature 1]
- [Improvement 1]

**Changelog:** [LINK]
**Deploy:** [TIME] CDMX

@here any questions?
```

**Hotfix:**

```markdown
🚨 HOTFIX PRANELY v1.6.1

**Problema:** [DESCRIPTION]
**Fix:** [SOLUTION]
**Status:** DEPLOYED

No action required from users.
```

---

## 8. Calendario 2026

### 8.1 Q2 2026

| Semana | Release | Features |
|--------|---------|----------|
| Apr 28 | v1.6.0 | Fase 2C deploy |
| May 2 | v1.6.1 | Patch if needed |
| May 9 | v1.7.0 | Fase 3A secrets |
| May 16 | v1.7.1 | Patch if needed |
| May 23 | v1.8.0 | Fase 3B authz |
| May 30 | - | Memorial Day (no deploy) |
| Jun 6 | v1.8.1 | Patch if needed |
| Jun 13 | v1.9.0 | Fase 3C compliance |
| Jun 20 | v1.9.1 | Patch if needed |
| Jun 27 | v2.0.0 | Phase 4 |

### 8.2 Release Calendar

```
ENE   FEB   MAR   ABR   MAY   JUN
───────────────────────────────────
W1    W1    W1    W1    W1    W1
W2    W2    W2    W2    W2    W2
W3    W3    W3    W3    W3    W3
W4    W4    W4    W4    W4    W4
                  30: Major
                          27: Major
```

---

## 9. On-Call Schedule

### 9.1 Rotation

| Semana | Primary | Secondary |
|--------|---------|------------|
| Apr 28 - May 4 | DevOps | Backend |
| May 5 - May 11 | Backend | DevOps |
| May 12 - May 18 | DevOps | Backend |
| ... | ... | ... |

### 9.2 Responsabilidades

**Primary:**
- Aprobar/deploy releases
- Handle incidentes
- Decidir rollback

**Secondary:**
- Support primary
- Testing staging
- Documentation

---

## 10. Links Rápidos

- [Runbook Deploy](./runbook-deploy.md)
- [Healthchecks](./healthchecks.md)
- [Rollback](./rollback-procedures.md)

---

**Última actualización:** 2026-04-23  
**Owner:** Engineering Lead