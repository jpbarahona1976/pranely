# ADR-0001: Stack Tecnológico

**Fecha:** 20 Abril 2026  
**Estado:** Aceptado  
**Decisor:** DevSecOps Lead  

---

## Contexto

PRANELY es un sistema SaaS B2B multi-tenant para gestión de residuos industriales en México/LATAM. Se requiere un stack tecnológico que soporte:
- Alta disponibilidad y escalabilidad
- Cumplimiento normativo mexicano (NOM-052-SEMARNAT-2005)
- Procesamiento asíncrono de documentos
- Integración con servicios de IA

## Decisiones

### Frontend
| Opción | Decisión | Justificación |
|--------|----------|---------------|
| React + Vite | ❌ Descartado | Mayor overhead que Next.js para SSR |
| Next.js + TypeScript | ✅ Aceptado | SSR, API routes, deployment optimizado |
| Svelte | ❌ Descartado | Ecosistema menor para enterprise |
| Vue | ❌ Descartado | Curva de aprendizaje vs beneficios |

**Decisión:** Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui

### Backend
| Opción | Decisión | Justificación |
|--------|----------|---------------|
| Express.js | ❌ Descartado | Boilerplate, validación débil |
| NestJS | ❌ Descartado | Overhead, opinionated |
| FastAPI | ✅ Aceptado | Async, Pydantic, OpenAPI automática |
| Django | ❌ Descartado | Síncrono por defecto, overhead |

**Decisión:** FastAPI + Python 3.12 + Pydantic + SQLAlchemy

### Base de Datos
| Opción | Decisión | Justificación |
|--------|----------|---------------|
| SQLite | ❌ Descartado | No multi-tenant, limitaciones concurrentes |
| MongoDB | ❌ Descartado | Sin transacciones ACID |
| PostgreSQL 16 | ✅ Aceptado | Transacciones, JSONB, full-text search |

**Decisión:** PostgreSQL 16 (no SQLite)

### Colas
| Opción | Decisión | Justificación |
|--------|----------|---------------|
| RabbitMQ | ❌ Descartado | Configuración compleja |
| Celery | ❌ Descartado | Síncrono, debugging difícil |
| Redis + RQ | ✅ Aceptado | Simple, integración Python |

**Decisión:** Redis 7 + RQ (Redis Queue)

### IA
| Opción | Decisión | Justificación |
|--------|----------|---------------|
| OpenAI | ❌ Descartado | Costo, datos sensibles |
| DeepInfra-Qwen | ✅ Aceptado | Open source, costo menor |
| Anthropic | ❌ Descartado | Solo Claude, costo |

**Decisión:** DeepInfra con modelo Qwen2.5 para análisis de residuos

### Pagos
| Opción | Decisión | Justificación |
|--------|----------|---------------|
| Stripe | ✅ Aceptado | Estándar industry, webhooks |
| Paddle | ❌ Descartado | Menor presencia en México |
| MercadoPago | ❌ Descartado | Solo LATAM, API limitada |

**Decisión:** Stripe para gestión de suscripciones

## Consecuencias

### Positivas
- Stack moderno con soporte activo
- TypeScript end-to-end (excepto API)
- Validación automática via Pydantic
- OpenAPI docs generadas automáticamente
- Workers desacoplados via Redis

### Negativas
- Dependencia de servicios externos (DeepInfra, Stripe)
- Curva de aprendizaje FastAPI
- Complejidad operacional (5+ servicios)

## Referencias

- [FastAPI Performance](https://fastapi.tiangolo.com/async/)
- [PostgreSQL vs SQLite](https://www.postgresql.org/about/)
- [RQ Redis Queue](https://python-rq.org/)
