# PRANELY - Acta de Baseline 0A

**Fecha:** 20 Abril 2026  
**Subfase:** 0A - Baseline corregido post-auditoría  
**Estado:** ✅ Completada

---

## Acta de Creación

PRANELY es un reinicio absoluto post-auditoría de estructura corrupta. Este documento certifica:

1. El repositorio inicia desde **cero absoluto post-auditoría**
2. Se eliminaron carpetas contaminantes (skills, protocolos, etc.)
3. Estructura correcta: `packages/` (no `apps/`)
4. Git inicializado limpio

## Decisiones Cerradas

| # | Decisión | Valor |
|---|----------|-------|
| 1 | Nombre canónico | PRANELY |
| 2 | Ruta canónica | `C:\Projects\Pranely` |
| 3 | Tipo proyecto | SaaS B2B multi-tenant |
| 4 | Monorepo | Sí, `packages/frontend` + `packages/backend` |
| 5 | Base de datos | PostgreSQL 16 (no SQLite) |
| 6 | Frontend | Next.js 15 + TypeScript + Tailwind |
| 7 | Backend | FastAPI + Python 3.12 |
| 8 | Colas | Redis 7 + RQ |
| 9 | Containers | Dev Containers obligatorios |
| 10 | Branch principal | `main` (protegida) |

## Estructura Creada

```
pranely/
├── .devcontainer/
│   └── devcontainer.json          ✅
├── .github/workflows/
│   └── ci-base.yml                ✅
├── docs/
│   ├── BASELINE.md                ✅
│   └── decisions/
│       └── ADR-0001-STACK-TECNOLOGICO.md ✅
├── packages/
│   ├── frontend/                   ✅ (vacío, crear en 0B)
│   └── backend/                   ✅ (vacío, crear en 0B)
├── quarantine/                    ✅
│   └── README.md
├── scripts/                       ✅
│   └── dev-init.sh
├── docker-compose.base.yml        ✅ (PostgreSQL + Redis)
├── docker-compose.dev.yml         ✅
├── .gitignore                     ✅
├── .nvmrc                         ✅ (22)
├── .python-version                ✅ (3.12)
├── LICENSE                        ✅ (MIT)
└── README.md                      ✅
```

## Servicios Base

| Servicio | Versión | Puerto | Imagen |
|----------|---------|--------|--------|
| PostgreSQL | 16 | 5432 | postgres:16-alpine |
| Redis | 7 | 6379 | redis:7-alpine |

## Criterios de Salida 0A

| Criterio | Estado |
|----------|--------|
| Git clean | ✅ |
| Monorepo base (`packages/`) | ✅ |
| Docker compose OK | ✅ |
| Dev Container config | ✅ |
| CI workflow | ✅ |
| ADR documentado | ✅ |
| Estructura exacta | ✅ |

---

*Documento firmado: 2026-04-20*
