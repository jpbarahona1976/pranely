# PRANELY

> Sistema SaaS B2B para gestión, trazabilidad y cumplimiento normativo de residuos industriales en México/LATAM.

## Estado

**Subfase:** 0A - Baseline corregido post-auditoría  
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
├── .devcontainer/            # Dev Container configuration
├── .github/workflows/       # GitHub Actions CI
├── docs/
│   ├── BASELINE.md          # Acta de baseline
│   └── decisions/           # Architecture Decision Records
├── packages/
│   ├── frontend/            # Next.js frontend
│   └── backend/             # FastAPI backend
├── quarantine/              # Contenido en cuarentena
├── scripts/                 # Utility scripts
├── docker-compose.base.yml  # Servicios base (PG + Redis)
├── docker-compose.dev.yml   # Desarrollo completo
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

# Abrir en VS Code Dev Container
code .
# → Reopen in Container
```

## Documentación

- [docs/BASELINE.md](./docs/BASELINE.md) - Acta de baseline
- [docs/decisions/](./docs/decisions/) - Architecture Decision Records

---

*Última actualización: 2026-04-20*
