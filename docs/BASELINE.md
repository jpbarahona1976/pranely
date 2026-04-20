# PRANELY - Acta de Baseline 0A

**Fecha:** 20 Abril 2026  
**Subfase:** 0A - Baseline vacío post-cuarentena  
**Estado:** ✅ Completada

---

## Acta de Creación

PRANELY es un reinicio absoluto post-cuarentena. Este documento certifica:

1. El repositorio inicia desde **cero absoluto**
2. Se detectaron dos rutas duplicadas (OneDrive + Desktop)
3. OneDrive fue puesto en cuarentena: `Pranely__QUARANTINE__2026-04-20_ONEDRIVE`
4. Desktop es ahora la ruta canónica

## Decisiones Cerradas

| # | Decisión | Valor |
|---|----------|-------|
| 1 | Nombre canónico | PRANELY |
| 2 | Ruta canónica | `C:\Users\barah\Desktop\Pranely` |
| 3 | Tipo proyecto | SaaS B2B multi-tenant |
| 4 | Monorepo | Sí, `apps/web` + `apps/api` |
| 5 | Base de datos | PostgreSQL 16 (no SQLite) |
| 6 | Frontend | Next.js 15 + TypeScript + Tailwind |
| 7 | Backend | FastAPI + Python 3.12 |
| 8 | Colas | Redis 7 + RQ |
| 9 | Containers | Dev Containers obligatorios |
| 10 | Branch principal | `main` (protegida) |

## Estructura Creada

```
pranely/
├── apps/
│   ├── web/              ✅ (vacío, crear en 0B)
│   └── api/              ✅ (vacío, crear en 0B)
├── infra/
│   ├── docker/           ✅ (vacío)
│   └── nginx/            ✅ (vacío)
├── scripts/              ✅ (vacío)
├── docs/                 ✅
│   └── BASELINE.md       ✅
├── tests/                ✅ (vacío)
├── .devcontainer/        ✅ (crear en 0B)
├── .nvmrc                ✅ (Node 22)
├── .python-version       ✅ (3.12)
├── .gitignore            ✅
├── docker-compose.base.yml   ✅
├── docker-compose.dev.yml   ✅
└── README.md             ✅
```

## Servicios Base

| Servicio | Versión | Puerto | Imagen |
|----------|---------|--------|--------|
| PostgreSQL | 16 | 5432 | postgres:16-alpine |
| Redis | 7 | 6379 | redis:7-alpine |

## Cuarentena

Contenido anterior movido a:
`C:\Users\barah\OneDrive\Desktop\Pranely__QUARANTINE__2026-04-20_ONEDRIVE`

Incluye:
- 12 skills base
- Protocolo de reconstrucción
- Artefactos de implementación 0A fallidos
- Historial Git anterior

## Criterios de Salida 0A

| Criterio | Estado |
|----------|--------|
| Git clean | ✅ |
| Monorepo base | ✅ |
| Docker compose OK | ✅ |
| Una sola ruta canónica | ✅ |
| Estructura vacía | ✅ |

---

*Documento firmado: 2026-04-20*
