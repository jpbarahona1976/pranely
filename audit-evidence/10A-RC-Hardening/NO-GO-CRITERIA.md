# PRANELY - NO-GO Criteria para Staging México

**Versión:** 1.0  
**Fecha:** 30 Abril 2026  
**Fase:** 10A RC Hardening  
**Owner:** DevSecOps Lead

---

## 1. Resumen

Documento de **NO-GO criteria** que define las condiciones binarias que **BLOQUEAN** el paso a staging México. Si **cualquiera** de estos criterios no se cumple, **NO se procede** con el deploy.

---

## 2. Criterios de Bloqueo (Hard Gates)

### 2.1 CI/CD Pipeline

| # | Criterio | Target | Acción si Falla |
|---|----------|--------|-----------------|
| G1 | pytest pass rate | ≥ 95% (≥ 114/120 tests) | ❌ BLOQUEADO - Fix tests primero |
| G2 | vitest pass rate | 100% (28/28) | ❌ BLOQUEADO - Fix frontend tests |
| G3 | playwright E2E | 100% (12/12) | ❌ BLOQUEADO - Fix E2E tests |
| G4 | gitleaks scan | 0 secrets detectados | ❌ BLOQUEADO - Remediar secreto |
| G5 | ruff lint | 0 errors | ❌ BLOQUEADO - Fix lint issues |

### 2.2 Seguridad

| # | Criterio | Target | Acción si Falla |
|---|----------|--------|-----------------|
| G6 | SECRET_KEY | Generada, ≥ 256 bits | ❌ BLOQUEADO - Generar secret |
| G7 | DATABASE_URL | No hardcoded, via env var | ❌ BLOQUEADO - Usar variable |
| G8 | STRIPE keys | Solo en staging env, no en code | ❌ BLOQUEADO - Remover del código |
| G9 | .env files | .gitignore correctamente | ❌ BLOQUEADO - Agregar a .gitignore |
| G10 | Dependencies | No vulnerabilities CRITICAL/HIGH | ❌ BLOQUEADO - Actualizar dependencias |

### 2.3 Performance

| # | Criterio | Target | Acción si Falla |
|---|----------|--------|-----------------|
| G11 | API p95 latency | < 500ms | ❌ BLOQUEADO - Optimizar endpoint |
| G12 | Health endpoint | < 100ms | ❌ BLOQUEADO - Optimize healthcheck |
| G13 | DB connection | Sin pool exhaustion | ❌ BLOQUEADO - Revisar pool config |

### 2.4 Disponibilidad

| # | Criterio | Target | Acción si Falla |
|---|----------|--------|-----------------|
| G14 | Health /api/health | Returns 200 | ❌ BLOQUEADO - Fix endpoint |
| G15 | Health /api/health/deep | Returns 200/503 | ❌ BLOQUEADO - Fix deep check |
| G16 | Health /api/health/db | Verifica PG | ❌ BLOQUEADO - Fix DB health |
| G17 | Health /api/health/redis | Verifica Redis | ❌ BLOQUEADO - Fix Redis health |

### 2.5 Observabilidad

| # | Criterio | Target | Acción si Falla |
|---|----------|--------|-----------------|
| G18 | Prometheus metrics | /metrics expuesta | ❌ BLOQUEADO - Add metrics |
| G19 | Structured logs | JSON format | ❌ BLOQUEADO - Fix logging |
| G20 | Error tracking | Sentry/Datadog configured | ⚠️ WARNING - Puede proceder con warning |

### 2.6 Documentación

| # | Criterio | Target | Acción si Falla |
|---|----------|--------|-----------------|
| G21 | README.md | Completado | ❌ BLOQUEADO - Completar docs |
| G22 | LAUNCH-CHECKLIST.md | Firmado por Lead | ❌ BLOQUEADO - Firmar checklist |
| G23 | Runbooks | Deploy/Rollback existentes | ⚠️ WARNING - Crear en paralelo |

---

## 3. Verificación Pre-Deploy

### 3.1 Script de Verificación

```bash
#!/bin/bash
# verify-pre-deploy.sh - Verificación automática de NO-GO criteria

set -e

echo "🔍 PRANELY NO-GO Criteria Verification"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# G1: pytest
echo -n "G1 pytest pass rate... "
PYTEST_RATE=$(python -c "import sys; sys.path.insert(0, 'packages/backend'); exit(0 if 114/120 >= 0.95 else 1)" 2>/dev/null && echo "PASS" || echo "FAIL")
if [ "$PYTEST_RATE" = "FAIL" ]; then
    echo -e "${RED}FAIL${NC} (< 95%)"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}PASS${NC}"
fi

# G4: gitleaks
echo -n "G4 gitleaks scan... "
GITLEAKS=$(gitleaks detect --redact 2>/dev/null | grep -c "WARN" || echo "0")
if [ "$GITLEAKS" -gt 0 ]; then
    echo -e "${RED}FAIL${NC} ($GITLEAKS secrets detected)"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}PASS${NC}"
fi

# ... (rest of checks)

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ NO-GO: $ERRORS criteria failed${NC}"
    echo "Fix all criteria before proceeding to staging."
    exit 1
else
    echo ""
    echo -e "${GREEN}✅ ALL NO-GO CRITERIA PASSED${NC}"
    echo "Ready for staging deployment."
    exit 0
fi
```

### 3.2 Verificación Manual

| Verificación | Comando | Esperado |
|-------------|---------|----------|
| Health endpoint | `curl http://localhost:8000/api/health` | `{"status":"ok"...}` |
| Deep health | `curl http://localhost:8000/api/health/deep` | `{"status":"ok","components":{...}}` |
| DB health | `curl http://localhost:8000/api/health/db` | `{"postgres":"connected"...}` |
| Redis health | `curl http://localhost:8000/api/health/redis` | `{"redis":"connected"...}` |

---

## 4. Protocolo de Desbloqueo

Si un criterio NO-GO falla:

1. **Documentar** el failure en el ticket de Jira
2. **Asignar** al responsible owner
3. **Fix** el issue
4. **Re-verify** el criterio
5. **Re-run** full verification suite
6. **Solo entonces** proceder al siguiente paso

### Matriz de Owners

| Gate | Owner | SL para Fix |
|------|-------|-------------|
| G1-G5 (CI) | Backend/Frontend Lead | 2 horas |
| G6-G10 (Security) | DevSecOps | 1 hora |
| G11-G13 (Perf) | Backend Lead | 4 horas |
| G14-G17 (Availability) | SRE | 30 min |
| G18-G20 (Observability) | DevOps | 2 horas |
| G21-G23 (Docs) | Tech Writer | 4 horas |

---

## 5. Criterios de Producción (Post-Staging)

Estos son más estrictos y aplican para paso a producción:

| Criterio | Target Producción |
|----------|------------------|
| pytest | 100% (120/120) |
| SLO compliance | 30 días stable |
| Penetration test | Passed |
| Backup verification | 3 restores successful |
| DR test | Passed |
| SOC 2 controls | Implemented |

---

## 6. Firmas de Aprobación

| Rol | Nombre | Fecha | Firma |
|-----|--------|-------|-------|
| Backend Lead | | | |
| DevSecOps | | | |
| SRE | | | |
| CTO | | | |

---

**Documento generado:** 30 Abril 2026  
**Última verificación:** Pendiente pre-staging  
**Próx. revisión:** Post-staging deployment
