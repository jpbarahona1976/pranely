# PRANELY - Secrets Management Policy

**Versión:** 1.0  
**Fecha:** 2026-04-23  
**Estado:** Fase 3A - Implementado  
**Owner:** DevSecOps  

---

## 1. Objetivo

Definir política de gestión de secrets para PRANELY: rotación, almacenamiento, detección y remediación de secretos expuestos.

## 2. Scope

| Categoría | Secrets Cubiertos |
|-----------|-------------------|
| Authentication | JWT SECRET_KEY, API keys |
| Database | DATABASE_URL, PostgreSQL credentials |
| Cache/Queue | REDIS_URL, Redis password |
| External Services | Stripe keys, DeepInfra API keys |
| Infrastructure | TLS certificates, SSH keys |

## 3. Principios

### 3.1 Nunca Hardcodear
- ❌ No secrets en código fuente
- ❌ No secrets en docker-compose.yml valores por defecto
- ❌ No secrets en templates (.env.example)
- ✅ Usar `${VAR:?VAR required}` para producción
- ✅ Usar `.env` archivo gitignored

### 3.2 Rotación Obligatoria

| Secret | Frecuencia Rotación | Trigger |
|--------|---------------------|---------|
| JWT SECRET_KEY | 90 días | Compromiso sospechado |
| Database password | 30 días | Rotación trimestral |
| Stripe keys | Inmediato | Cambio de ambiente |
| DeepInfra API | 30 días | Revisión mensual |

### 3.3 Generación de Secrets

```bash
# Python (recomendado)
python -c "import secrets; print(secrets.token_urlsafe(64))"

# OpenSSL (alternativa)
openssl rand -base64 64
```

**Requisitos mínimos:**
- JWT SECRET_KEY: 256 bits (32 bytes) mínimo
- Database passwords: 128 bits (16 caracteres) mínimo
- API keys: 256 bits (43 caracteres base64) mínimo

## 4. Entornos

### 4.1 Desarrollo (development)
- Usar `.env` local (gitignored)
- Secrets de prueba permitidos en tests
- NO secrets reales de producción

### 4.2 Staging
- Variables de entorno CI/CD
- `.env` con prefijo `STAGING_`
- Secrets generados automáticamente en CI

### 4.3 Producción
- Secrets manager obligatorio (Vault, AWS Secrets Manager, etc.)
- CI/CD injects secrets en runtime
- Fallbacks NO permitidos en producción

## 5. Detección - Gitleaks

### 5.1 Configuración
Ver `.gitleaks.toml` para reglas específicas.

### 5.2 Ejecutar Local
```bash
# Instalar gitleaks
brew install gitleaks  # macOS
scoop install gitleaks # Windows

# Ejecutar scan
gitleaks detect --redact

# Pre-commit hook
gitleaks protect --redact
```

### 5.3 Gates CI/CD
- ❌ Commits con secrets detectados = BLOCK
- ✅ Gitleaks debe pasar antes de merge

## 6. SI UN SECRET ES EXPÜESTO

### Protocolo de Respuesta Inmediata

1. **Identificar** - ¿Qué secret? ¿Dónde?
2. **Revocar** - Invalidar inmediatamente
3. **Rotar** - Generar nuevo secret
4. **Verificar** - Confirmar compromiso de repo
5. **Documentar** - Registrar incidente
6. **Auditar** - Revisar logs de acceso

### Rotación Emergency

```bash
# 1. Generar nuevo secret
NEW_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(64))")

# 2. Actualizar en secrets manager
vault kv put secret/pranely/production SECRET_KEY=$NEW_SECRET

# 3. Deploy con nuevo secret
docker-compose -f docker-compose.prod.yml up -d

# 4. Verificar healthchecks
curl https://api.pranely.com/api/health/deep
```

## 7. Archivos Relacionados

| Archivo | Propósito |
|---------|-----------|
| `packages/backend/.env.example` | Template limpio de variables |
| `.gitleaks.toml` | Reglas de detección |
| `.gitignore` | Archivos protegidos |
| `docker-compose.*.yml` | Variables de entorno |

## 8. Checklist Rotación

- [ ] Generar secret con entropía suficiente
- [ ] Actualizar en secrets manager
- [ ] Actualizar CI/CD si aplica
- [ ] Restart servicios
- [ ] Verificar healthchecks
- [ ] Verificar auth/login funciona
- [ ] Actualizar documentación si necesario

## 9. Contacto

**Security Team:** @juanbarahona  
**Incident Response:** security@pranely.com
