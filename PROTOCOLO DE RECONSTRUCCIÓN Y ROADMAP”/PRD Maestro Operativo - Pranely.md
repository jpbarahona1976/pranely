# **PRD Maestro Operativo \- Pranely**

**Versión:** 1.0.0  
**Fecha:** 19 de abril de 2026  
**Estado:** CONGELADO \- No modificar sin RFC aprobado  
**Audiencia:** Equipo de desarrollo (Minimax M2.7), PM, QA  
**Propósito:** Define EXACTAMENTE qué producto se construye. Sirve como fuente única de verdad para implementación, validación y scope control. Minimax debe ceñirse estrictamente a este documento.

## **Resumen Ejecutivo**

Pranely.ai es una plataforma SaaS para **gestión de residuos peligrosos** compliant con NOM-052-SEMARNAT-2005 (México/LATAM). Automatiza trazabilidad de movimientos de residuos mediante OCR/IA, dashboard operativo, mobile bridge (QR+WS) y command center para admins.

**Usuarios objetivo:** Generadores de residuos (SMB/Enterprise) y Gestores/Transportistas.  
**Mercado:** México/LATAM (idioma ES/EN, moneda MXN/USD).  
**Modelo de negocio:** Freemium \+ suscripciones Stripe (Free/Pro/Enterprise).  
**MVP indispensable:** Auth → Dashboard → CRUD Waste Movements → Upload IA → Mobile Bridge → Billing callbacks.  
**Fuera de alcance MVP:** AI Copilot avanzado, Jurista full RAG, integraciones Zebra/Honeywell, multi-org avanzado.

**No-negociables:**

* Multi-tenant row-level (org\_id en todas tablas negocio).  
* Trazabilidad inmutable (audit\_logs append-only).  
* Alta disponibilidad (healthchecks, circuit breakers).  
* Seguridad nivel alto (no BYPASS\_AUTH en prod, secrets rotados).

| Rol | Descripción | Necesidades Clave | Permisos |
| :---- | :---- | :---- | :---- |
| **Owner** | Propietario SMB/Enterprise | KPIs, billing, upgrades, operadores | Full access \+ billing |
| **Admin** | Gerente operaciones | CRUD movimientos, configs, cuotas | Dashboard \+ Command Center |
| **Member** | Operador campo | Movimientos, mobile bridge, review | CRUD \+ bridge |
| **Viewer** | Contador/auditor | Reportes read-only | Dashboard view-only |
| **Director** | Admin global | Command Center full | Todo menos billing |

**Segmentos:**

* **Generator** (80% usuarios): Generan residuos, necesitan compliance NOM-052.  
* **Gestor** (20%): Transportan, necesitan validación manifiestos.

## **Casos de Uso Principales (MVP)**

**Flujo Crítico E2E:** Login → Dashboard → Upload Doc → IA Extract → Review → Approve → Mobile Bridge → Export PDF.

1. **Autenticación (5 min):** Register/Login JWT, selección plan, email verify (fase 2).  
2. **Dashboard KPIs (2 min):** Stats movimientos (pendientes/aprobados), tendencias, filtros fecha/org.  
3. **CRUD Waste Movements (10 min):** Listar/crear/editar/delete (soft-delete), export PDF.  
4. **Upload \+ IA Extraction (3-15s):** Drag-drop PDF/manifiesto → OCR Qwen32B → JSON extract → confidence score → review manual si \<90%.  
5. **Mobile Bridge (5 min):** QR session → WS sync móvil → capture campo → sync dashboard.  
6. **Command Center (10 min):** Configs sistema, operadores, cuotas/mensual, AI playground (MVP básico).  
7. **Billing (2 min):** Checkout Stripe, success/cancel callbacks, usage tracking.  
8. **Legal Radar (MVP simple):** Alertas regulatorias push (NOM-052 updates), scan manual.

**No MVP:** Onboarding wizard, email notifications, advanced reports Excel, customer portal Stripe.

## **Requisitos Funcionales (MVP Congelado)**

## **Módulos y Rutas**

| Módulo | Ruta | Descripción | Estado MVP |
| :---- | :---- | :---- | :---- |
| Landing | `/` | Público: features, pricing, CTA login/register | ✅ Indispensable |
| Auth | `/login`, `/register` | JWT Bearer, plan select | ✅ Indispensable |
| Dashboard | `/dashboard` | KPIs, tabla movimientos, filtros | ✅ Indispensable |
| Waste CRUD | `/dashboard/review/[id]`, `/dashboard/extraction` | Extract/review/verify movements | ✅ Indispensable |
| Mobile Bridge | `/dashboard/mobile-bridge` | QR+WS sync | ✅ Indispensable |
| Command Center | `/dashboard/command-center` | Configs/opers/cuotas (sin AI full) | ✅ Indispensable |
| Settings | `/dashboard/settings` | Cuenta, upgrade plan | ✅ Indispensable |
| Billing | `/billing/success`, `/billing/canceled` | Stripe callbacks | ✅ Indispensable |
| Legal Radar | `/dashboard/legal-radar` | Alertas básicas (scan manual) | ⚠️ Simplificado MVP |

## **Flujo E2E Crítico (Validar en E2E Tests)**

text

`Usuario → Landing → Login (JWT) → Dashboard (KPIs + tabla)`   
`→ Upload Doc → IA Extract (Qwen) → Review/Approve`   
`→ Mobile QR Session → WS Sync → Export PDF/Pasaporte`  
`→ Settings → Billing Checkout (Stripe)`

**Reglas de Negocio NOM-052:**

* Clasificación residuos: quantity/unit/waste\_type/confidence.  
* Estados: pending/in\_review/validated/exception/rejected/approved.  
* Inmutable post-approve (is\_immutable=true).  
* Audit log todo CRUD.

## **Datos y Modelos (Schema Fuente de Verdad)**

**Tablas Core (Postgres 16):**

* organizations: id(UUID), name, legal\_name, country(MX), plan\_tier(free/pro), stripe\_customer\_id.  
* users: id(UUID), email(unique), hashed\_password(Argon2id), role\_hint.  
* memberships: user\_id, org\_id, role(owner/admin/member/viewer).  
* waste\_movements: org\_id(FK), generator\_id, waste\_type, quantity, status(enum), confidence, file\_path, is\_immutable, archived\_at(soft-delete).  
* plans: code(unique), name, price\_usd\_min, segment(generator/gestor).  
* subscriptions: org\_id, plan\_id, status(active/past\_due), external\_id(Stripe).  
* audit\_logs: org\_id, user\_id, action, resource, payload(JSONB), created\_at (append-only).

**Índices Obligatorios:** org\_id+status, org\_id+created\_at DESC.

**Retención:** Audit 7 años, movements 5 años (S3 archive), sessions 30 días purge.

## **UX y Wireframes Conceptuales**

* **Dashboard:** Grid KPIs (movs pendientes/hoy/mes), tabla paginada (10/50), filtros fecha/status/org, search.  
* **Upload:** Drag-drop multi (max 10MB/doc), progress bar, preview extract JSON editable.  
* **Mobile Bridge:** QR code 2min expiry, WS realtime sync (position/status), offline queue.  
* **i18n:** ES/EN (next-intl), default ES (LATAM).  
* **Responsive:** Mobile-first (375px), desktop 1200px max-width.  
* **Design System:** Shadcn/UI, Tailwind, dark mode toggle.

**Métricas de Éxito (SLO Iniciales):**

| Métrica | Target MVP |
| :---- | :---- |
| Login success rate | 99% |
| IA extraction p95 | \<20s |
| Dashboard load p95 | \<2s |
| Uptime mensual | 99.5% |
| Error rate 5xx | \<1% |

## **Requisitos No Funcionales**

| Categoría | Requisito | Nivel |
| :---- | :---- | :---- |
| **Seguridad** | JWT HS256 (24h exp), RBAC+tenant filter, secrets Vault/GCP, no BYPASS\_AUTH prod, MFA admins | Alto |
| **Performance** | API p95 \<500ms, IA async RQ, Redis cache GETs, CDN assets | Medio |
| **Escalabilidad** | Stateless, horizontal scale FastAPI/Next, Cloud SQL HA | Medio |
| **Resiliencia** | Circuit breakers (DeepInfra/Stripe), retries backoff, healthchecks profundos, blue/green deploy | Alto |
| **Observabilidad** | Logs JSON (correlation\_id), Prometheus/Grafana, alertas SLO | Alto |
| **Compliance** | LFPDPPP (consentimientos), NOM-052/055, audit trail inmutable | Alto |
| **Accesibilidad** | WCAG AA (contrast 4.5:1), keyboard nav, ARIA labels | Medio |

## **Alcance Fuera de MVP (Fase 2+)**

* AI Copilot chat/action.  
* Jurista RAG full.  
* Exports Excel/API.  
* Email SMTP/Resend.  
* Multi-org users.  
* Integraciones hardware (Zebra).

## **Reglas de Implementación (Para Minimax)**

* **Congelar este PRD:** No agregar features/docs fuera de listado.  
* **Contrato API:** OpenAPI 3.0 desde FastAPI, client TS generado.  
* **Idempotencia:** POSTs con idempotency-key (Redis TTL 24h).  
* **Inmutabilidad:** Soft-delete \+ archived\_at, no DELETE físico.  
* **Validación:** Pydantic v2 schemas estrictos, optimistic locking (version field).

## **Criterios de Terminación PRD**

Este PRD se considera completo y congelado si:

* Define usuarios/roles/personas.  
* Lista módulos/rutas/flujos E2E.  
* Especifica schema DB/índices exactos.  
* Detalla reglas negocio/NOM-052.  
* Incluye UX/responsive/i18n.  
* Define SLOs/no-funcionales.  
* Marca MVP vs fase 2 explícitamente.

