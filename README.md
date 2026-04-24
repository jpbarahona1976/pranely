# PRANELY

> Sistema SaaS B2B para gestión, trazabilidad y cumplimiento normativo de residuos industriales en México/LATAM.

## Badges

| Badge | Status |
|-------|--------|
| **DR Tests** | ![DR Tests](https://github.com/pranely/pranely/actions/workflows/dr-ci.yml/badge.svg) |
| **CI Base** | ![CI Base](https://github.com/pranely/pranely/actions/workflows/ci-base.yml/badge.svg) |
| **Security** | ![Security](https://github.com/pranely/pranely/actions/workflows/ci-base.yml/badge.svg?query=security) |

## Estado

**Versión:** 1.12.2  
**Subfase:** 5A (Auth/Orgs/Billing APIs)  
**Siguiente:** 5B (Waste domain CRUD)  
**Fecha:** 23 Abril 2026

## Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | Next.js 15 + TypeScript + Tailwind |
| Backend | FastAPI + Python 3.12 |
| Base de datos | PostgreSQL 16 |
| Colas | Redis 7 + RQ |
| IA | DeepInfra-Qwen |
| Pagos | Stripe |

## Estructura del Proyecto

```
pranely/
├── .devcontainer/            # Dev Container configuration
├── .github/workflows/        # GitHub Actions CI
│   ├── ci-base.yml          # Base CI (lint, test, security)
│   └── dr-ci.yml            # DR Tests pipeline
├── audit-evidence/          # Auditoría y evidencia
├── docs/
│   ├── BASELINE.md          # Acta de baseline
│   ├── decisions/           # Architecture Decision Records
│   └── dr/                  # Disaster Recovery
│       ├── plan-emergencia.md
│       └── RTO-STANDARD.md
├── packages/
│   ├── frontend/            # Next.js frontend
│   └── backend/             # FastAPI backend
│       └── app/schemas/api/v1/  # API schemas centralizados
├── scripts/                 # Utility scripts (backup, restore, DR)
├── docker-compose.base.yml  # Servicios base (PG + Redis)
├── docker-compose.dev.yml   # Desarrollo completo
├── docker-compose.dr-tests.yml # DR tests environment
├── .gitignore
├── .nvmrc
├── .python-version
├── LICENSE
└── README.md
```

## Quick Start

```bash
# Requisitos
- Docker Desktop
- Node.js 22 (gestionado por .nvmrc)
- Python 3.12 (gestionado por .python-version)

# Levantar servicios base
docker compose -f docker-compose.base.yml up -d

# Levantar con DR tests
docker compose -f docker-compose.dr-tests.yml up -d

# Abrir en VS Code Dev Container
code .
# → Reopen in Container
```

## Tests

```bash
# Unit tests
cd packages/backend
poetry run pytest tests/test_backup_dr.py -v

# Unit tests + coverage
poetry run pytest tests/test_backup_dr.py --cov=tests --cov-report=xml --cov-report=html

# Integration tests (requiere Docker)
docker compose -f docker-compose.dr-tests.yml run --rm dr-tests
```

## DR / Backup

```bash
# Ejecutar simulacro DR
./scripts/simulacro-dr.sh full

# Backup manual
./scripts/backup.sh

# Restore
./scripts/restore.sh MODE=postgres-only
```

## Documentación

- [docs/BASELINE.md](./docs/BASELINE.md) - Acta de baseline
- [docs/decisions/](./docs/decisions/) - Architecture Decision Records
- [docs/dr/plan-emergencia.md](./docs/dr/plan-emergencia.md) - Plan DR
- [docs/dr/RTO-STANDARD.md](./docs/dr/RTO-STANDARD.md) - Estándar RTO

---

*Última actualización: 2026-04-23*
