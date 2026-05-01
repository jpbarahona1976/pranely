# PRANELY - FIX PACK 10A.1: Gitleaks Specs E2E
## Fecha: 30 Abril 2026

---

## RESUMEN

| Antes | Después |
|-------|---------|
| 9 secretos detectados | 0 secretos detectados |
| 3 archivos con fallbacks hardcodeados | 3 archivos sin fallbacks |

---

## ARCHIVOS MODIFICADOS

### 1. `packages/frontend/e2e/bridge.spec.ts`

**ANTES (líneas 5-7):**
```typescript
const TEST_EMAIL = process.env.E2E_TEST_EMAIL || 'test@pranely.com';
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD || 'TestPassword123';
const TEST_TOKEN = process.env.E2E_TEST_TOKEN || 'test-token-placeholder';
```

**DESPUÉS:**
```typescript
// Test credentials MUST be provided via environment variables
// CI/CD should set: E2E_TEST_EMAIL, E2E_TEST_PASSWORD, E2E_TEST_TOKEN
const TEST_EMAIL = process.env.E2E_TEST_EMAIL;
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD;
const TEST_TOKEN = process.env.E2E_TEST_TOKEN;
```

---

### 2. `packages/frontend/e2e/smoke-auth.spec.ts`

**ANTES (líneas 12-14):**
```typescript
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD || 'TestPassword123';
const ALT_PASSWORD = process.env.E2E_ALT_PASSWORD || 'AltPassword456';
const WRONG_PASSWORD = process.env.E2E_WRONG_PASSWORD || 'WrongPasswordTest';
```

**DESPUÉS:**
```typescript
// Credentials MUST be provided via env vars - no hardcoded fallbacks
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD;
const ALT_PASSWORD = process.env.E2E_ALT_PASSWORD;
const WRONG_PASSWORD = process.env.E2E_WRONG_PASSWORD;
```

---

### 3. `packages/frontend/e2e/dashboard-6b-audit.spec.ts`

**ANTES (líneas 12-13):**
```typescript
const TEST_EMAIL = process.env.E2E_TEST_EMAIL || 'test@pranely.com';
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD || 'TestPassword123';
```

**DESPUÉS:**
```typescript
// Configuración via env vars - no hardcoded fallbacks
const TEST_EMAIL = process.env.E2E_TEST_EMAIL;
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD;
```

---

## VERIFICACIÓN GITLEAKS

```
$ gitleaks detect --redact --no-color

    ○
    │╲
    │ ○
    ○ ░
    ░    gitleaks

2:54PM INF 44 commits scanned.
2:54PM INF scanned ~6489239 bytes (6.49 MB) in 777ms
2:54PM INF no leaks found
```

**✅ GITLEAKS = 0**

---

## NOTAS IMPORTANTES

1. **Credenciales ahora son OBLIGATORIAS via env vars:**
   - `E2E_TEST_EMAIL`
   - `E2E_TEST_PASSWORD`
   - `E2E_ALT_PASSWORD`
   - `E2E_WRONG_PASSWORD`
   - `E2E_TEST_TOKEN`

2. **CI/CD debe configurar estas variables:**
   ```bash
   export E2E_TEST_EMAIL=test@pranely.com
   export E2E_TEST_PASSWORD=<secure-password>
   export E2E_ALT_PASSWORD=<secure-password>
   export E2E_WRONG_PASSWORD=<wrong-password>
   export E2E_TEST_TOKEN=<test-token>
   ```

3. **Los tests fallarán si las variables no están configuradas** - esto es intencional para forzar configuración correcta.

---

## CRITERIOS CUMPLIDOS

| Criterio | Estado |
|----------|--------|
| gitleaks 0 | ✅ |
| Specs sintaxis OK | ✅ |
| No fallbacks hardcodeados | ✅ |
| process.env usado | ✅ |

---

**Fix completado:** 30 Abril 2026 14:54 CST
**Archivos modificados:** 3
**Secrets removidos:** 9
