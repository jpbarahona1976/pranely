# ADR-0002: Stack Arquitectónico MVP - Confirmación y Consolidación

**Fecha:** 23 Abril 2026  
**Estado:** Aceptado  
**Decisor:** Principal Architect + Staff Engineer + DevSecOps Lead  
**Versión ADR base:** ADR-0001-STACK-TECNOLOGICO.md (20 Abril 2026)  
**Relación:** Fase 2A del roadmap PRANELY

---

## Resumen Ejecutivo

Este ADR consolida y confirma el stack tecnológico MVP de PRANELY basado en la inspección del repositorio activo. Se verifican las decisiones del ADR-0001 contra el código implementado y se documentan las especificaciones técnicas precisas para cada capa.

**Decisión central:** Stack confirmado como válido, sin cambios de arquitectura. Documentación de estado exacto y decisiones técnicas operativas.

---

## Contexto

PRANELY ejecuta Fase 2A del roadmap: arquitectura Stack/ADR. Se requiere:

1. Confirmar que el stack implementado coincide con las decisiones documentadas
2. Documentar las especificaciones técnicas exactas (versiones, configs)
3. Identificar gaps entre decisión y implementación
4. Proveer línea base para Fase 2B (contratos API) y 2C (deploy seguro)

**Inspección realizada:**
- `packages/backend/` - código Python/FastAPI
- `packages/frontend/` - código Next.js/React
- `docker-compose.dev.yml`, `docker-compose.base.yml`
- `pyproject.toml`, `package.json`
- Modelos SQLAlchemy, schemas Pydantic
- Dockerfiles

---

## Inventario Técnico Actual

### Backend
| Componente | Versión implementada | Estado |
|------------|---------------------|--------|
| Python | 3.12.7 | ✅ Confirmado |
| FastAPI | ^0.115.0 | ✅ Confirmado |
| SQLAlchemy | ^2.0.0 | ✅ Confirmado |
| Pydantic | ^2.9.0 | ✅ Confirmado |
| pydantic-settings | ^2.6.0 | ✅ Confirmado |
| asyncpg | ^0.30.0 | ✅ Confirmado |
| alembic | ^1.13.0 | ✅ Confirmado |
| argon2-cffi | ^23.1.0 | ✅ Confirmado |
| python-jose | ^3.3.0 | ✅ Confirmado |
| email-validator | ^2.1.0 | ✅ Confirmado |
| redis | ^5.2.0 | ✅ Confirmado |
| Poetry | 1.8.3 | ✅ Confirmado |

### Frontend
| Componente | Versión implementada | Estado |
|------------|---------------------|--------|
| Node.js | 22.13.1 | ✅ Confirmado |
| Next.js | 15.1.0 | ✅ Confirmado |
| React | 19.0.0 | ✅ Confirmado |
| TypeScript | 5.7.3 | ✅ Confirmado |
| Tailwind CSS | ^3.4.0 | ✅ Confirmado |
| pnpm | 9.12.2 | ✅ Confirmado |

### Infraestructura
| Componente | Versión | Estado |
|------------|---------|--------|
| PostgreSQL | 16-alpine | ✅ Confirmado |
| Redis | 7-alpine | ✅ Confirmado |
| Docker | multi-stage | ✅ Confirmado |

---

## Decisiones de Arquitectura Fijadas

### 1. Frontend

**Decisión:** Next.js 15 App Router + TypeScript + Tailwind CSS

**Especificaciones técnicas:**
- Runtime: Node.js 22.13.1 (`.nvmrc`)
- Framework: Next.js 15.1.0 (App Router, no Pages Router)
- Lenguaje: TypeScript 5.7.3 strict mode
- Estilos: Tailwind CSS 3.4 con shadcn/ui
- Package manager: pnpm 9.12.2
- i18n: Base ES (locale en User model), futura expansión
- Estado: AuthContext (local), sin Redux/Zustand por ahora
- API consumption: Fetch directo a FastAPI, sin tRPC por ahora

**Routing:**
```
src/app/
├── layout.tsx          # Root layout con AuthProvider
├── page.tsx           # Redirect a login/dashboard
├── login/page.tsx
├── register/page.tsx
├── dashboard/page.tsx  # Protected route
└── globals.css        # Tailwind imports
```

**Componentes:**
```
src/components/
├── LoginForm.tsx
├── RegisterForm.tsx
└── ProtectedRoute.tsx
```

**Alternativas descartadas:**
- Vite + React SPA: Descartado (no SSR, sin Next.js capabilities)
- Pages Router: Descartado (App Router es el futuro de Next.js)
- Zustand/Redux: Descartado (AuthContext suficiente para MVP)

### 2. Backend

**Decisión:** FastAPI + SQLAlchemy 2.0 + Pydantic 2.9

**Especificaciones técnicas:**
- Framework: FastAPI 0.115+
- ORM: SQLAlchemy 2.0 con async (asyncpg)
- Validación: Pydantic 2.9+
- Auth: JWT (python-jose) + Argon2 (argon2-cffi)
- Settings: pydantic-settings 2.6+
- Migrations: Alembic 1.13+
- ASGI: Uvicorn con hot reload

**Organización por routers/dominios:**
```
app/api/
├── __init__.py
├── auth.py              # POST /auth/register, /auth/login
├── deps.py              # JWT dependency
├── org_deps.py          # Organization dependency
├── employers.py         # CRUD /employers
├── transporters.py      # CRUD /transporters
├── residues.py          # CRUD /residues
├── employer_transporter_links.py  # CRUD /employer-transporter-links
└── health.py            # GET /health, /api/health
```

**Core modules:**
```
app/core/
├── __init__.py
├── config.py            # Settings singleton
├── database.py          # async engine + session
├── security.py          # Argon2 hashing
└── tokens.py            # JWT create/verify
```

**Modelos de dominio (Fase 1B):**
- Organization (multi-tenant root)
- User + Membership (auth + RBAC)
- Employer, Transporter, Residue (waste domain)
- EmployerTransporterLink (N:M relationship)
- WasteMovement (legacy, para historial)

**Schemas Pydantic:**
```
app/schemas/
├── auth.py              # Auth request/response
└── domain.py            # Domain entity schemas
```

**Alternativas descartadas:**
- NestJS: Overhead, opinionated vs FastAPI flexibility
- Django: Síncrono por defecto, menos async-native
- Flask: Menos validación automática, menos OpenAPI

### 3. Base de Datos

**Decisión:** PostgreSQL 16 (no SQLite)

**Especificaciones técnicas:**
- Engine: PostgreSQL 16-alpine
- Driver: asyncpg (async)
- ORM: SQLAlchemy 2.0 async
- Migrations: Alembic (estructura lista)
- Multi-tenancy: organization_id en todas las tablas + unique constraints por tenant

**Tablas implementadas:**
| Tabla | Primary Key | Multi-tenant | Indices |
|-------|------------|--------------|---------|
| organizations | id | - | - |
| users | id | - | email (unique) |
| memberships | id | organization_id | uq_user_org |
| waste_movements | id | organization_id | - |
| employers | id | organization_id | uq_org_rfc, ix_org_status |
| transporters | id | organization_id | uq_org_rfc, ix_org_status |
| residues | id | organization_id | ix_org_employer, ix_org_status |
| employer_transporter_links | id | organization_id | uq_org_employer_transporter, ix_org |

**Soft delete:** archived_at en Employer y Transporter (H2)

**Pendiente:**
- Alembic migrations formales (Fase 4B)
- RLS policies (Fase 3B)

**Alternativas descartadas:**
- SQLite: No multi-tenant, limitaciones concurrentes
- MongoDB: Sin transacciones ACID, diferente paradigma

### 4. Async / Workers

**Decisión:** Redis 7 + RQ (pendiente de implementación completa)

**Estado actual:**
- Redis 7 configurado en docker-compose ✅
- Dependencia redis-python en pyproject.toml ✅
- RQ workers NO implementados todavía ❌ (Fase 7A)

**Especificaciones para implementación futura:**
- Cola: RQ (Redis Queue)
- Trabajos iniciales:
  - Procesamiento de uploads
  - Extracción IA (DeepInfra-Qwen)
  - Notificaciones async
- scheduler: APScheduler para tareas recurrentes (Radar legal 07:00 MX)

**Alternativas descartadas:**
- Celery: Overhead, debugging difícil, no async-native
- RabbitMQ: Configuración compleja, overkill para MVP
- Kafka: Overkill para el volumen MVP

**Dependencias a agregar cuando se implemente:**
```toml
rq = "^1.16.0"
apscheduler = "^3.10.0"
```

### 5. Deploy

**Decisión:** Docker + VPS + Nginx

**Arquitectura de contenedores:**
```
services:
├── postgres:16-alpine    # Puerto 5432
├── redis:7-alpine        # Puerto 6379
├── backend:dev           # Puerto 8000, uvicorn --reload
└── frontend:dev          # Puerto 3000, pnpm dev
```

**Multi-stage Dockerfiles:**
- Backend: python:3.12.7-slim → poetry → uvicorn
- Frontend: node:22.13.1-alpine → pnpm → next dev

**Healthchecks:**
- Postgres: `pg_isready -U pranely -d pranely_dev`
- Redis: `redis-cli ping`
- Backend: `GET /api/health → 200 {"status":"ok"}`
- Frontend: `curl http://localhost:3000`

**Volúmenes:**
- `postgres_data:/var/lib/postgresql/data`
- `redis_data:/data`
- Bind mounts para hot reload en dev

**Entornos:**
| Entorno | Contenido | Propósito |
|---------|-----------|-----------|
| docker-compose.base.yml | Postgres + Redis | Dev mínimo |
| docker-compose.dev.yml | Postgres + Redis + Backend + Frontend | Desarrollo full |
| staging (pendiente) | Para 2C | Pre-producción |
| production (pendiente) | Para 2C | VPS/Nginx |

**Alternativas descartadas:**
- Vercel/Netlify: Para backend FastAPI no es ideal
- Docker Swarm: Overkill para VPS single
- Kubernetes: Post-MVP

---

## Decisiones Explícitamente Rechazadas

| Decisión | Razones |
|----------|---------|
| SQLite en producción | No multi-tenant, limitaciones concurrentes |
| Express.js/NestJS backend | Menos async-native que FastAPI |
| Pages Router (Next.js) | App Router es el estándar actual |
| Zustand/Redux global state | AuthContext suficiente para MVP |
| Celery para colas | Overhead, debugging difícil |
| Kubernetes para MVP | Overkill, VPS es suficiente |

---

## Gaps Identificados (No bloqueantes)

| Gap | Prioridad | Fase destino |
|-----|-----------|--------------|
| RQ workers no implementados | Media | 7A |
| Alembic migrations formales | Alta | 4B |
| RLS policies multi-tenant | Alta | 3B |
| Stripe integration | Media | 8C |
| DeepInfra-Qwen integration | Media | 7B |
| Nginx reverse proxy | Media | 2C |
| Environment staging/prod | Alta | 2C |

---

## Impacto por Capa

### Frontend
- Stack confirmado: Next.js 15 App Router ✅
- No cambios necesarios
- Ready para Fase 6 (shell/navegación)

### Backend
- Stack confirmado: FastAPI + SQLAlchemy + Pydantic ✅
- Routers organizados por dominio ✅
- Multi-tenant filters implementados ✅
- Ready para Fase 5A (auth/billing APIs)

### Base de datos
- PostgreSQL 16 confirmado ✅
- Índices y constraints multi-tenant implementados ✅
- Ready para Fase 4B (migraciones formales)

### Async
- Redis 7 configurado ✅
- RQ pendiente (Fase 7A)
- No bloquea desarrollo actual

### Deploy
- Docker Compose dev funcional ✅
- Healthchecks implementados ✅
- Ready para Fase 2C (staging/prod)

---

## Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| RQ no implementado aún | Bajo | Fase 7A planificada, no bloquea |
| Sin Alembic migrations | Medio | Fase 4B planificada, desarrollo usa create_all() |
| Sin RLS policies | Medio | Filters por org_id implementados, RLS post-MVP |
| Secrets hardcoded en .env | Alto | Gitignored, rotar antes de prod (Fase 3A) |

---

## relación con otras fases

- **Fase 2B (Contratos API):** Usa este ADR como base para definir OpenAPI specs
- **Fase 2C (Deploy seguro):** Extiende docker-compose a staging/prod con Nginx
- **Fase 3B (Authz/multi-tenant):** Implementa RLS sobre el modelo confirmado
- **Fase 4B (Migraciones):** Alembic sobre el schema SQLAlchemy confirmado
- **Fase 7A (Workers):** Implementa RQ sobre Redis configurado aquí

---

## Criterio de Implementación

Para confirmar que el stack está correctamente implementado:

```bash
# Backend
cd packages/backend && poetry --version  # 1.8.3
python -c "import fastapi, sqlalchemy, pydantic; print('OK')"  # sin errores

# Frontend
cd packages/frontend && cat .nvmrc  # 22.13.1
pnpm --version  # 9.12.2

# Docker
docker compose -f docker-compose.dev.yml ps  # 4 servicios healthy

# Health checks
curl http://localhost:8000/api/health  # {"status":"healthy"}
curl http://localhost:3000  # 200 OK (Next.js)
```

---

## Conclusión

El stack tecnológico de PRANELY está **correctamente implementado** según ADR-0001. No se requieren cambios de arquitectura en esta fase. Las decisiones están consolidadas y documentadas para guiar las fases siguientes.

**Estado:** ✅ ACEPTADO para ejecución

---

## Referencias

- ADR-0001-STACK-TECNOLOGICO.md
- docs/BASELINE.md
- docs/FASE-1B-DOMAIN-MODELS.md
- docker-compose.dev.yml
- packages/backend/pyproject.toml
- packages/frontend/package.json

---

*Documento creado durante Fase 2A del roadmap PRANELY*
*Última actualización: 2026-04-23*