# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

### Próximas tareas

- [ ] 2C: Arquitectura - Deploy seguro ✅ **PENDIENTE**

### Completado

- [x] 2A: Arquitectura - Stack/ADR ✅ **COMPLETADO**
- [x] 2B: Arquitectura - Contratos API ✅ **COMPLETADO**

---

## [1.5.0] - 2026-04-23

> **BLOQUE 2B CERRADO** ✅
> Contratos API formales documentados. Ownership asignado. Schemas nuevos testados.

### Added

#### Fase 2B: Contratos API Ownership ✅

**New Schemas** (`app/schemas/api/`)
- `common.py` - PaginationParams, ListResponse[T], ErrorResponse, ErrorDetail
- `auth.py` - LoginIn, RegisterIn, TokenOut, UserOut, OrgOut
- `employer.py` - EmployerIn, EmployerOut, EmployerListOut
- `transporter.py` - TransporterIn, TransporterOut, TransporterListOut
- `residue.py` - ResidueIn, ResidueOut, ResidueListOut
- `link.py` - LinkIn, LinkOut, LinkListOut

**Documentation** (`docs/contracts/api-contracts.md`)
- Ownership por dominio asignado
- Mapa routers/endpoints
- Ejemplos curl por endpoint
- RFC 7807 error format

**Tests** (`tests/test_api_schemas.py`)
- 30 tests para schemas nuevos
- Validación multi-tenant (organization_id en todos)
- Pydantic validation tests

**Commits:**
- `schemas: add API schemas formal contract`
- `docs: api contracts ownership v1.5.0`

---

## [1.4.0] - 2026-04-23

> **BLOQUE 2A CERRADO** ✅
> Stack tecnológico MVP confirmado. ADR-0002 creado. Sin cambios de arquitectura.

### Added

#### Fase 2A: Stack/ADR Arquitectónico ✅

**Documentation - ADR-0002** (`docs/decisions/ADR-0002-STACK-ARQUITECTONICO-MVP.md`)
- Inventario técnico completo verificado contra repo
- Decisiones fijadas: Frontend, Backend, DB, Async, Deploy
- Gaps identificados (RQ workers, Alembic, RLS)
- Relación documentada con fases 2B y 2C

**Stack confirmado:**
| Capa | Tecnología | Versión |
|------|------------|---------|
| Frontend | Next.js 15 + TypeScript + Tailwind | 15.1.0 / 5.7.3 / 3.4 |
| Backend | FastAPI + SQLAlchemy + Pydantic | 0.115+ / 2.0 / 2.9 |
| DB | PostgreSQL 16 + asyncpg | 16-alpine |
| Cola | Redis 7 + RQ | 7-alpine (RQ pendiente) |
| Auth | JWT + Argon2 | python-jose / argon2-cffi |

**Commits:**
- `ADR-0002` - docs: fase 2A complete, stack arquitectónico confirmado

---

## [1.3.0] - 2026-04-23

> **BLOQUE 1C CERRADO** ✅
> CRUD API endpoints implementados para Employer, Transporter, Residue, EmployerTransporterLink.
> Tests de integración con aislamiento multi-tenant verificados. 110 tests passing.
> Fix Docker: poetry lock regeneration + backend healthy.

### Added

#### Fase 1C: CRUD API Endpoints ✅

**Backend - Dependencies** (`app/api/org_deps.py`)
- `get_current_org` - Dependency para obtener org actual del token JWT
- `get_optional_org` - Versión opcional
- Validación de membership y existencia de organización

**Backend - Routers** (`app/api/`)
- `employers.py` - CRUD completo con filtros, búsqueda, paginación
- `transporters.py` - CRUD completo con filtros, búsqueda, paginación
- `residues.py` - CRUD completo con filtros por employer/waste_type/status
- `employer_transporter_links.py` - CRUD para relación N:M

**Endpoints implementados:**
| Recurso | Métodos |
|---------|---------|
| Employers | POST /api/employers, GET /api/employers, GET /api/employers/{id}, PATCH /api/employers/{id}, DELETE /api/employers/{id} |
| Transporters | POST /api/transporters, GET /api/transporters, GET /api/transporters/{id}, PATCH /api/transporters/{id}, DELETE /api/transporters/{id} |
| Residues | POST /api/residues, GET /api/residues, GET /api/residues/{id}, PATCH /api/residues/{id}, DELETE /api/residues/{id} |
| Links | POST /api/employer-transporter-links, GET /api/employer-transporter-links, GET /api/employer-transporter-links/{id}, PATCH /api/employer-transporter-links/{id}, DELETE /api/employer-transporter-links/{id} |

**Features:**
- Multi-tenant: todas las queries filtran por organization_id
- Soft-delete: Employer y Transporter usan archived_at
- Paginación: page, page_size, search, status_filter
- Validaciones: RFC único por tenant, employer/transporter existen
- Aislamiento cross-tenant verificado en tests

**Backend - Tests** (`tests/`)
- `test_employers_api.py` - 16 tests (CRUD + isolation)
- `test_transporters_api.py` - 12 tests (CRUD + isolation)
- `test_residues_api.py` - 13 tests (CRUD + validaciones)
- `test_employer_transporter_links_api.py` - 14 tests (CRUD + validaciones)

**Commits:**
- `15efc41` - feat(backend): fase 1C complete
- `b1ee337` - fix(docker): regenerate lock file and fix backend restart loop

---

### Fixed

#### Fase 1C: Docker Backend Fix ✅

**Problema:** Backend en restart loop por poetry.lock desincronizado con pyproject.toml

**Fixes aplicados:**
- `packages/backend/Dockerfile` - Añadido `poetry lock --no-update` antes de install
- `docker-compose.dev.yml` - Comando actualizado con lock regeneration
- `packages/backend/poetry.lock` - Regenerado para sincronizar dependencias
- `tests/conftest.py` - Variables entorno para Settings (SECRET_KEY, DATABASE_URL, REDIS_URL)
- `app/api/deps.py` - HTTPBearer(auto_error=False) para manejo correcto 401

**Evidencia Docker:**
- Status: healthy (4 servicios up)
- Healthcheck: HTTP 200 {"status":"ok"}
- 110 tests passing

---

## [1.2.0] - 2026-04-22

> **BLOQUE 1B CERRADO** ✅
> Modelos de dominio implementados: Employer, Transporter, Residue, EmployerTransporterLink.
> Schemas Pydantic listos para fase 1C. Tests unitarios y de aislamiento multi-tenant incluidos.

### Added

#### Fase 1B: Modelos de dominio ✅

**Backend - Models** (`app/models.py`)
- `Employer` - Entidad empresa/empleador con RFC, dirección, industria
- `Transporter` - Entidad transportista con license_number, vehicle_plate
- `Residue` - Entidad residuo con waste_type (NOM-052), weight_kg, volume_m3
- `EmployerTransporterLink` - Asociación N:M empleadores-transportistas
- `EntityStatus` enum: ACTIVE, INACTIVE, PENDING
- `WasteType` enum: PELIGROSO, ESPECIAL, INERTE, ORGANICO, RECICLABLE
- `WasteStatus` enum: PENDING, ACTIVE, DISPOSED, ARCHIVED
- `archived_at` - Soft delete timestamp indexing (H2)
- RFC único por tenant + indices de rendimiento (A1, A2)

**Backend - Schemas** (`app/schemas/domain.py`)
- EmployerCreate, EmployerUpdate, EmployerResponse, EmployerListResponse
- TransporterCreate, TransporterUpdate, TransporterResponse, TransporterListResponse
- ResidueCreate, ResidueUpdate, ResidueResponse, ResidueListResponse
- EmployerTransporterLink schemas
- Schemas de relaciones (EmployerWithRelations, ResidueWithEmployer, etc.)
- RFC validation con soporte para Ñ y & (H1)
- EmailStr validation (A3)

**Backend - Tests** (`tests/test_domain_models.py`)
- 42 tests passing (38 original + 4 nuevos para H1/H2)
- TestEnums: Validación de enumeraciones
- TestEmployerModel: CRUD, relaciones, constraints
- TestTransporterModel: CRUD, relaciones
- TestResidueModel: CRUD, waste_type enum
- TestEmployerTransporterLink: unique constraint
- TestMultiTenancyIsolation: Verificación de aislamiento por org_id
- TestDomainSchemas: Validación Pydantic schemas
- TestArchivedAtSoftDelete: H2 archived_at field
- TestRFCWithEnye: H1 RFC con Ñ y &

**Dependencies** (`pyproject.toml`)
- email-validator = "^2.1.0" (H3)

**Documentation** (`docs/FASE-1B-DOMAIN-MODELS.md`)
- Diagrama de entidades con relaciones
- Referencia de enumeraciones
- Notas de implementación multi-tenant

**Commits:**
- `models: add Employer, Transporter, Residue domain entities`
- `schemas: add domain entity Pydantic schemas`
- `tests: add domain models unit tests with tenant isolation`
- `fix: apply H1-H3 fixes (RFC pattern, archived_at, email-validator)`

---

## [1.1.0] - 2026-04-21

> **BLOQUE 0C/1A CERRADO** ✅
> Deuda técnica resuelta. Auditorías Minimax M2.5 + Gemini 3.1 Pro verificadas.
> Tests: 18 passed, 0 warnings. Git: working tree clean.

### Added

#### Fase 1A: Authentication (JWT + Argon2id) ✅

**Backend - Models**
- `app/models.py` - User, Organization, Membership entities
- `app/core/security.py` - Argon2id password hashing
- `app/core/tokens.py` - JWT token creation/validation

**Backend - API Endpoints**
- `app/api/auth.py` - POST /api/auth/register, POST /api/auth/login
- `app/api/deps.py` - JWT authentication dependency
- `app/schemas/auth.py` - Request/response Pydantic schemas

**Backend - Tests**
- `tests/test_auth.py` - Register/login endpoint tests
- `tests/test_security.py` - Password hashing tests
- `tests/test_tokens.py` - JWT token tests

**Frontend - Auth Flow**
- `src/contexts/AuthContext.tsx` - Auth state management
- `src/components/ProtectedRoute.tsx` - Route guard
- `src/components/LoginForm.tsx` - Login form
- `src/components/RegisterForm.tsx` - Registration form
- `src/app/login/page.tsx` - Login page
- `src/app/register/page.tsx` - Register page
- `src/app/dashboard/page.tsx` - Protected dashboard
- `src/app/page.tsx` - Redirect to login/dashboard

**Infrastructure**
- `packages/backend/.env.example` - Environment template
- `packages/backend/.env` - Development env (gitignored)
- `pyproject.toml` - argon2-cffi, python-jose, aiosqlite, psycopg2-binary

**Commits:**
- [`4ac0c53`](https://github.com/pranely/pranely/commit/4ac0c53) - fix: resolve technical debt from Fase 0C audit
- [`fe6d55c`](https://github.com/pranely/pranely/commit/fe6d55c) - feat(1A): implement JWT authentication

---

### Fixed

#### Fase 1A: Authentication Stabilization ✅

**Fixes técnicos aplicados:**
- `app/core/config.py` - Export singleton `settings = get_settings()` (ImportError)
- `app/models.py` - Replace `default_factory` with `default=_utcnow` (SQLAlchemy ArgumentError)
- `app/models.py` - Replace `datetime.utcnow` with `datetime.now(timezone.utc)` (Python 3.12 deprecation)
- `app/api/auth.py` - Align error messages to test contract
- `tests/conftest.py` - Remove redundant `event_loop` fixture (pytest-asyncio 0.24)
- `packages/backend/pyproject.toml` - Added psycopg2-binary
- `.github/workflows/ci-base.yml` - Remove `continue-on-error: true` (CI gates strict)
- `docker-compose.dev.yml` - Frontend healthcheck added

**Test Results:** 18 passed, 0 warnings

---

### Removed

- ~~`quarantine/`~~ → Eliminada definitivamente

---

## [1.0.0] - 2026-04-20

### Added

#### Fase 1: Scaffold ✅

**Next.js 15.1.0 + Tailwind**
- `package.json` - Next.js 15.1.0, React 19, Tailwind CSS, tRPC
- `next.config.js` - Configuración del proyecto
- `tailwind.config.js` - Tema Tailwind
- `postcss.config.js` - PostCSS setup
- `tsconfig.json` - TypeScript 5.7
- `Dockerfile` - Multi-stage build
- `src/app/layout.tsx` - Root layout
- `src/app/page.tsx` - Home page
- `src/app/globals.css` - Tailwind imports

**FastAPI 0.115.0 + Alembic**
- `pyproject.toml` - FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2.9
- `alembic.ini` - Configuración de migraciones
- `alembic/` - Estructura de migraciones
- `app/main.py` - FastAPI app factory (con health router)
- `app/core/config.py` - Settings con Pydantic V2
- `app/core/database.py` - SQLAlchemy async engine
- `app/api/health.py` - Health check endpoint `/api/health`

**Docker**
- `packages/frontend/Dockerfile` - Multi-stage Next.js
- `packages/backend/Dockerfile` - Multi-stage FastAPI
- `docker-compose.dev.yml` - **Modo desarrollo con hot reload**
  - `pnpm dev` para frontend
  - `uvicorn --reload` para backend
  - Volumes preservan node_modules/.venv

**Commit:** [`e041cd2`](https://github.com/pranely/pranely/commit/e041cd2) - 1A-1B: scaffold Next.js + FastAPI limpio

---

#### Fase 0: Fundación

##### [0C] - Gobernanza y CI/CD ✅

**GitHub Actions**
- `.github/workflows/ci-base.yml` - Lint, test, security, gitleaks
- `.github/workflows/ci-infra.yml` - Terraform, Docker, Ansible validation

**CODEOWNERS**
- `@juanbarahona` como owner único
- 2 approvals requeridos para cambios de infra

**Dependabot**
- `.github/dependabot.yml` - Updates semanales
- npm: Lunes, pip: Lunes, docker: Miércoles, actions: Viernes

**Gitleaks**
- `.gitleaks.toml` - Detección de secrets

**Commit:** [`f22c648`](https://github.com/pranely/pranely/commit/f22c648) - 0C: gobernanza + CI/CD base

---

##### [0B] - Versiones Fijadas ✅

**Versiones exactas**
- Node.js: **22.13.1** (`.nvmrc`)
- Python: **3.12.7** (`.python-version`)
- pnpm: **9.12.2**
- Poetry: **1.8.3**

**Docker Compose**
- `docker-compose.base.yml` - PostgreSQL 16 + Redis 7
- `docker-compose.dev.yml` - Desarrollo completo

**Dev Container**
- `.devcontainer/devcontainer.json` - Ubuntu + Node + Poetry

**Commits:**
- [`7e1faf2`](https://github.com/pranely/pranely/commit/7e1faf2) - 0B: corregir pnpm a 9.12.2
- [`3dcc231`](https://github.com/pranely/pranely/commit/3dcc231) - 0C: limpieza final

---

##### [0A] - Baseline Post-Cuarentena ✅

**Estructura del monorepo**
- `packages/frontend/` - Next.js frontend
- `packages/backend/` - FastAPI backend
- `docs/BASELINE.md` - Acta de baseline
- `docs/decisions/ADR-0001-STACK-TECNOLOGICO.md` - ADR stack

**Archivos de configuración**
- `.gitignore` - Monorepo .gitignore (incluye `next-env.d.ts`)
- `.nvmrc` - Node 22.13.1
- `.python-version` - Python 3.12.7
- `LICENSE` - MIT License
- `README.md` - Documentación principal
- `quarantine/README.md` - Doc de cuarentena

**Decisión de stack (ADR-0001)**
| Capa | Tecnología |
|------|------------|
| Frontend | Next.js 15 + TypeScript + Tailwind |
| Backend | FastAPI + Python 3.12 |
| DB | PostgreSQL 16 |
| Colas | Redis 7 + RQ |
| IA | DeepInfra-Qwen |
| Pagos | Stripe |

---

### Fixed

#### Fase 1: Estabilización

- **docker-compose.dev.yml** - Modo desarrollo con hot reload
  - Frontend: `command: pnpm dev`
  - Backend: `command: poetry install && uvicorn --reload`
  - Volumes preservan node_modules y .venv
- **.gitignore** - Agregado `next-env.d.ts` para ignorar archivo auto-generado

---

### Removed

- ~~`apps/`~~ → Migrado a `packages/`
- ~~`infra/`~~ → Placeholder (terraform/ansible vacíos)
- ~~`tests/`~~ → Sin uso en baseline

---

### Security

- `.gitleaks.toml` configurado para detección de secrets
- `.env` en `.gitignore`
- CODEOWNERS enforced para cambios de infra
- `next-env.d.ts` ignorado (evita exponer tipos internos de Next.js)

---

## [0.0.1] - 2026-04-20

### Added

- Proyecto PRANELY inicializado
- Monorepo con estructura básica

---

[UNRELEASED]: https://github.com/pranely/pranely/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/pranely/pranely/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/pranely/pranely/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/pranely/pranely/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/pranely/pranely/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/pranely/pranely/releases/tag/v1.1.0
[1.0.0]: https://github.com/pranely/pranely/releases/tag/v1.0.0
[0.0.1]: https://github.com/pranely/pranely/releases/tag/v0.0.1
