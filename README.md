# PRANELY

> Sistema SaaS B2B para gestión, trazabilidad y cumplimiento normativo de residuos industriales en México/LATAM.

## Estado

**Subfase:** 0A - Baseline vacío post-cuarentena
**Fecha:** 20 Abril 2026

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
├── packages/
│   ├── frontend/      # Next.js frontend
│   └── backend/       # FastAPI backend
├── infra/
│   ├── docker/       # Docker configurations
│   └── nginx/        # Nginx configurations
├── scripts/          # Utility scripts
├── docs/             # Documentación
├── tests/            # Tests
├── .devcontainer/    # Dev Container
├── docker-compose.base.yml   # Servicios base (PG + Redis)
└── docker-compose.dev.yml    # Desarrollo completo
```

## Quick Start

```bash
# Requisitos
- Docker Desktop
- Node.js 22 (gestionado por .nvmrc)
- Python 3.12 (gestionado por .python-version)

# Levantar servicios base
docker compose -f docker-compose.base.yml up -d

# Abrir en VS Code Dev Container
code .
# → Reopen in Container

# O usar GitHub Codespaces
# → New Codespace
```

## Documentación

- [docs/BASELINE.md](./docs/BASELINE.md) - Acta de baseline
- [docs/decisions/](./docs/decisions/) - Architecture Decision Records

## Cuarentena

El contenido anterior fue puesto en cuarentena:
`Pranely__QUARANTINE__2026-04-20_ONEDRIVE`

Ver archivo de evidencia para detalles.

---

*Última actualización: 2026-04-20*
