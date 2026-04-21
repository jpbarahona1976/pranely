# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

### Próximas tareas

- [ ] 1A: Sistema de Autenticación (JWT + OAuth)
- [ ] 1B: Modelos de dominio (Empresa, Residuo, Transportista)
- [ ] 1C: CRUD API endpoints

---

## [1.0.0] - 2026-04-20

### Added

#### Fase 1: Scaffold

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
- `app/main.py` - FastAPI app factory
- `app/core/config.py` - Settings con Pydantic V2
- `app/core/database.py` - SQLAlchemy async engine
- `app/api/health.py` - Health check endpoint

**Docker**
- `packages/frontend/Dockerfile` - Multi-stage Next.js
- `packages/backend/Dockerfile` - Multi-stage FastAPI

**Commit:** [`e041cd2`](https://github.com/pranely/pranely/commit/e041cd2) - 1A-1B: scaffold Next.js + FastAPI limpio

---

#### Fase 0: Fundación

##### [0C] - Gobernanza y CI/CD

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

##### [0B] - Versiones Fijadas

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

##### [0A] - Baseline Post-Cuarentena

**Estructura del monorepo**
- `packages/frontend/` - Next.js frontend
- `packages/backend/` - FastAPI backend
- `docs/BASELINE.md` - Acta de baseline
- `docs/decisions/ADR-0001-STACK-TECNOLOGICO.md` - ADR stack

**Archivos de configuración**
- `.gitignore` - Monorepo .gitignore
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

### Removed

- ~~`apps/`~~ → Migrado a `packages/`
- ~~`infra/`~~ → Placeholder (terraform/ansible vacíos)
- ~~`tests/`~~ → Sin uso en baseline
- ~~Contenido en cuarentena~~ → `quarantine/`

---

### Security

- `.gitleaks.toml` configurado para detección de secrets
- `.env` en `.gitignore`
- CODEOWNERS enforced para cambios de infra

---

## [0.0.1] - 2026-04-20

### Added

- Proyecto PRANELY inicializado
- Monorepo con estructura básica

---

[UNRELEASED]: https://github.com/pranely/pranely/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/pranely/pranely/releases/tag/v1.0.0
[0.0.1]: https://github.com/pranely/pranely/releases/tag/v0.0.1
