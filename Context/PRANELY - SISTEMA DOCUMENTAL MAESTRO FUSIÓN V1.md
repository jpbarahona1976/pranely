# **PRANELY \- SISTEMA DOCUMENTAL MAESTRO FUSIÓN V1.0**

**Versión:** Fusión de Claude Sonnet 4.6, ChatGPT 5.4 Thinking, Grok 4.2 Reasoning, Gemini 3.1 Pro  
**Fecha:** 20 Abril 2026  
**Estado:** Listo para ejecución \- Documento único de verdad (Source of Truth)  
**Foco:** Reconstrucción disciplinada priorizando seguridad, estabilidad, multi-tenancy y cero regresiones 

## **1\. PRD Maestro Operativo completo**

**Resumen ejecutivo**  
PRANELY es una plataforma SaaS B2B web-responsive con bridge móvil para gestión, trazabilidad inmutable y cumplimiento normativo (NOM-052/055, LFPDPPP) de residuos industriales en México/LATAM. Usa Next.js 15 App Router (frontend), FastAPI/Python 3.12 (backend), PostgreSQL 16, Redis 7/RQ (colas), Docker/VPS/Nginx (despliegue), DeepInfra-Qwen (IA), Stripe (billing). El rebuild corrige deuda técnica (secretos expuestos, BYPASS\_AUTH=true, cero tests, regresiones cíclicas) con entorno inmutable, CICD estricto y Pranely OS persistente.

**Problema que resuelve**  
Procesos manuales fragmentados generan multas regulatorias, pérdida de manifiestos y falta de visibilidad multi-tenant. El sistema actual falla por inestabilidad (cach corrupto, 500s intermitentes), seguridad débil y ausencia de observabilidad.

**Objetivos del producto**

* Flujo E2E estable: login → dashboard → upload/IA → review → approve (99.5% uptime, p95 API \<500ms).  
* Extracción IA \>85% precisión, multi-tenancy por organizationid.  
* Mobile Bridge QR/WS para campo, Legal Radar proactivo.

**Objetivos del negocio**

* MVP production-ready en 6-8 semanas (1-2 devs).  
* 10 clientes pagadores Q3 2026, MRR inicial vía planes (Free:100 docs, Pro:2500/$299).  
* Churn \<5% por estabilidad.

**No objetivos**  
No hardware IoT, marketplace inicial, app nativa MVP, multi-país full (ES/EN i18n básico).

**Alcance MVP**  
Auth (JWT/Argon2id), Dashboard (KPIs/polling), Waste CRUD (soft-delete/audit), Upload/IA pipeline (RQ/DeepInfra), Review queue, Mobile Bridge (QR/WS), Command Center básico (quotas/operators), Billing Stripe, Legal Radar básico, Settings\[i18n ES/EN\].

**Alcance post-MVP**  
Jurista RAG full, AI Copilot, exports avanzados (Excel), SSO SAML, S3 storage.

**Perfiles de usuario** (ver \#8 para mapa RBAC).  
**JTBD:** "Quiero subir manifiesto → IA extrae → review → approve inmutable sin paperwork" (Member). "Alertas regulatorias proactivas" (Owner).

**Casos de uso principales** (ver \#9).  
**Flujos críticos:** Login-dashboard-CRUD-upload-review-approve; QR-bridge-sync; Radar-scan-alert.

**Reglas de negocio** (ver \#11).  
**RF principales:** API por dominio (auth/waste/bridge/legal/billing), WS sync, RQ async IA.  
**RNF:** Docker obligatorio, CI gates (lint/typecheck/unit/e2e/security), SLOs (p95\<500ms, MTTR\<30min), secrets manager.

**Dependencias externas** (ver \#14).  
**Riesgos:** Secretos/BYPASS (crítico → rotar/gates CI); regresiones (alto → tests históricos); latencia IA (medio → workers/retries).  
**Métricas éxito:** Uptime 99.5%, extracción IA 85%, MRR growth, 0 secrets.  
**Criterios aceptación globales:** CI verde, healthchecks OK, E2E flujos, tenant isolation, 0 BYPASS prod.  
**Supuestos/dudas:** Umbral confianza IA=0.75 (hipótesis); pricing Free/Pro validado Stripe sandbox.  
**Conflictos detectados:** RQ vs Celery (elige RQ); naming PRANELY (canónico).

## **2\. Roadmap Maestro completo con subfases 0A–10C**

**Convención:** Fase (preparación/infra A, core B, validación C). Duración total: 8 semanas. Gates: CI verde \+ 2 approvals infra \+ auditoría por subfase.

| Fase | Subfase | Objetivo | Entradas | Actividades clave | Entregables | Depend. | Riesgos | Criterio salida | Valida (Negocio/Prod/Ingeniería/QA/Seg) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 0 Reinicio | 0A Limpieza | Repo limpio, baseline | Repo actual | Cuarentena legacy/SQLite, estructura monorepo | .gitignore, carpetas, quarantine | Ninguna | Deuda oculta | Git clean, gitleaks=0 | Aprobación founders/scope/estructura/CI base/secretos OK |
| 0 | 0B Entorno inmutable | Docker/DevContainers | 0A | Versiones fijas (Node22/Python3.12/PG16/Redis7), compose.dev | docker-compose.dev.yml, .devcontainer.json | 0A | Works-on-my-machine | `docker compose up` OK 4 servicios | Velocidad/Consistencia/bootstrap/smoke/no-contenedor |
| 0 | 0C Gobernanza | CICD/branch protection | 0B | Gates lint/typecheck/unit/security, 2 approvals infra | .github/workflows/ci.yml, protection main | 0B | Merges directos | PR test pasa/rechaza inválido | Control/priorización/flujo/puerta calidad/control cambios |
| 1 Producto | 1A Alcance/PRD | Normalizar scope | Contexto fuente | Naming PRANELY, P0-P3 backlog | PRD refinado | Fase 0 | Scope creep | Alcance MVP aprobado | Valor/usuarios/factibilidad/alcance testeable/sensible ID |
| 1 | 1B RBAC/usuarios | Mapa permisos | 1A | Modelos users/orgs/memberships, matriz RBAC | Mapa permisos, seed data | 1A | Permisos laxos | RBAC tests OK | Segmento/journeys/claims/middleware/least privilege |
| 1 | 1C Priorización casos | Backlog maestro | 1B | Casos E2E P0-P3, dependencias | Lista priorizada | 1B | Sobrecarga MVP | Backlog congelado | Impacto/secuencia dependencias/cobertura viable/crítica primero |
| 2 Arquitectura | 2A Stack/ADR | Fijar decisiones | 1C | Frontend/Backend/DB/Async/Deploy | ADR stack | 1C | Rediseño innecesario | ADR aprobado | Costo/escalabilidad/blueprint/entornos/superficies |
| 2 | 2B Contratos API | Ownership endpoints | 2A | Mapa routers/dominios, OpenAPI | Contrato por dominio | 2A | Coupling | Contratos firmados | Trazabilidad/experiencia/ownership/puntos control |
| 2 | 2C Deploy seguro | Estrategia release | 2B | Blue-green/canary, rollback, healthchecks | Runbook deploy | 2B | Downtime | Smoke post-deploy OK | Continuidad/release cadence/automatización/smoke hardening |
| 3 Seguridad | 3A Secretos | Remediar críticos | 2C | Rotación JWT/Stripe/DeepInfra, manager | Baseline secrets | 2C | Compromiso cuentas | 0 secrets, rotados | Confianza/riesgo reducido/config segura/pruebas auth/hallazgos |
| 3 | 3B Authz/multi-tenant | Isolation RBAC | 3A | JWT claims, middleware orgid/role | Policy acceso | 3A | Fuga datos | Tests isolation OK | Cuentas enterprise/permisos claros/middleware/tests negativas |
| 3 | 3C Compliance mínimo | NOM/LFPDPPP | 3B | Retención, consentimientos, ARCO | Backlog regulatorio | 3B | Incumplimiento | Evidencia legal OK | Ventas B2B/requisitos legales/campos eventos/data governance |
| 4 Datos | 4A Modelo datos | Normalizar entidades | 3C | ERD waste/audit/billing | Modelo funcional | 3C | Deuda estructural | ERD validado | Reportabilidad/consistencia/esquema/fixtures/auditoría |
| 4 | 4B Migraciones | Alembic formal | 4A | Baseline incremental, expand/contract | Estrategia migraciones | 4A | Ruptura datos | Migración/rollback OK | Continuidad/cambios seguros/versionado/migración/rollback |
| 4 | 4C Backup/DR | Recuperación probada | 4B | Automático diario, simulacro RPO1h/RTO15min | Plan DR | 4B | Pérdida datos | Restore exitoso | SLA/scripts/simulacro/recuperación |
| 5 Backend Core | 5A Auth/orgs/billing | APIs base estables | 4C | Routers auth/orgs/billing | APIs auth/billing | 4C | Login roto | Smoke auth verde | Acceso/monetización/API estable/regression/auth robusta |
| 5 | 5B Waste domain | CRUD approve/archive | 5A | wastemovements/stats, soft-delete | Dominio waste | 5A | Core roto | E2E waste OK | Operación diaria/flujo principal/performance/casos/errors |
| 5 | 5C Upload/review | Pipeline documental | 5B | Upload/ingest/review queue/estados | Pipeline robusto | 5B | Docs inconsistentes | Estados confiables | Productividad/revisión/contratos/colas/files seguros |
| 6 Frontend Core | 6A Shell/navegación | Layout/sidebar/i18n | 5A | App Router/guards/auth flow | Frontend base | 5A | Bloqueos acceso | Login-dashboard fluido | Demostrabilidad/UX base/rutas seguras/smoke token |
| 6 | 6B Dashboard | KPIs/tabla/polling | 5B | Stats/movements/actions | Dashboard modular | 5B | Regresiones | Dashboard sin errores | Visibilidad/valor inmediato/performance UI/flujos críticos |
| 6 | 6C Review/extraction | Flujo UI docs | 5C | Rutas review/extraction/verification | Flujo documental | 5C | Revisión inconsistente | Ciclo upload-review OK | Eficiencia/completitud/componentes/E2E docs/acceso rol |
| 7 Asíncrono/IA | 7A Worker resilient | RQ/tasks/scheduler | 6C | Retries/backoff/timeouts/DLQ | Procesamiento resilient | 6C | Jobs stuck | Colas observables | Throughput/feedback usuario/resiliencia/fallos simulados |
| 7 | 7B Contrato IA | DeepInfra/schemas | 7A | Prompts/schemas/costos versionados | Contrato IA auditable | 7A | Salidas inestables | Schema validation OK | Costo/precisión/compatibilidad/casos borde/redacción segura |
| 7 | 7C Alcance IA MVP | Decisión radar/console | 7B | Reducir costo/prioridad | Decisión documentada | 7B | Sobrecosto | Módulo recortado OK | ROI/foco/menos complejidad/cobertura menor/superficie |
| 8 Diferenciales | 8A Mobile Bridge | Session/WS robusto | 6B | Reconexión/expiración/sync | Bridge confiable | 6B | Pérdida sesión | Flujo bridge estable | Diferenciación/captura campo/real-time/redes inestables/sesión temporal |
| 8 | 8B Command Center | Configs/operators/quotas | 6A | Permisos/forms/auditoría | Panel admin funcional | 6A | Cambios peligrosos | Control admin seguro | Operación/autogestión/config service/RBAC/permisos sensibles |
| 8 | 8C Billing operacional | Checkout/callbacks | 5A | Sync suscripción/cuotas/estados | Billing E2E | 5A | Cobros inconsistentes | Compra activada | Ingresos/conversión/webhooks/sandbox/firma webhook |
| 9 Calidad/Observabilidad | 9A Tests matrix | Unit/integration/e2e/contract | Fases 5-8 | Regression histórica | Suite automatizada | Fases 5-8 | Regresiones | Cobertura mínima/módulo | Confiabilidad/releases seguras/suite auto/pruebas auth |
| 9 | 9B Observabilidad | Logs/métricas/SLOs | 9A | Correlación/dashboards/alertas | Stack observability | 9A | Ceguera operativa | Alertas accionables | Uptime/menor impacto/telemetría/evidencia/trazabilidad |
| 9 | 9C Performance | Cuellos/botella | 9B | Índices/cach/assets/polling | Plan optimización | 9B | Latencia alta | SLOs medibles | Escalabilidad/respuesta/tuning/benchmarks/rate limits |
| 10 Lanzamiento | 10A RC hardening | Checklist final | Todas previas | Freeze/gono-go | RC aprobado | 9C | Escape defectos | Sign-off sin issues | Fecha/experiencia mínima/build estable/gono-go/revisión final |
| 10 | 10B Deploy seguro | Canary/blue-green | 10A | Smoke/rollback auto | Producción nueva | 10A | Caída deploy | Tráfico estable | Continuidad/servicio vivo/despliegue/verificación post/monitoreo |
| 10 | 10C Operación continua | Postmortem/maintenance | 10B | Chaos mensual/debt review | Cadencia operativa | 10B | Recaída desorden | Operación recurrente | Sostenibilidad/iteración/mantenimiento/regresión hygiene |

## **3\. Plantilla exacta de prompt para Minimax por subfase**

**Plantilla reusable (copiar-pegar por subfase, reemplazar \[SUBFASE\]/\[DETALLES\])**:

| ROL Actúa como Principal Architect \+ Staff Engineer \+ DevSecOps Lead de PRANELY. OBJETIVO Ejecuta \*\*exclusivamente\*\* \[SUBFASE\] del roadmap fused V1.0. Produce artefactos accionables. CONTEXTO \- PRANELY: SaaS residuos (Next.js/FastAPI/PG16/Redis7/RQ/Docker/DeepInfra/Stripe). \- Stack fijo, multi-tenant orgid, inmutable post-validated. \- Pranely OS: \[insertar \#5 completa\]. \- Entradas: \[lista archivos/modelos/endpoints de subfase\]. \- Riesgos abiertos: \[de roadmap\]. ALCANCE Solo: \[objetivo subfase, entregables específicos\]. NO ALCANCE \- No cambies stack/arquitectura sin ADR. \- No features extra/MVP vs post-MVP. \- No toques fases prev/next. \- No hardcode secrets/BYPASS\_AUTH. REGLAS EJECUCIÓN \- Separa hechos/supuestos/decisiones/riesgos. \- Tests obligatorios (unit/integration/e2e/regression). \- Multi-tenant cada query/mutación filtra orgid. \- Logging correlacionado (requestid). \- Idempotente/rollback plan. FORMATO SALIDA \#\# Resumen ejecutivo \#\# Decisiones/Supuestos \#\# Entregables (código bloques por archivo) \#\# Tests agregados (pytest/jest/Playwright) \#\# Riesgos/Rollback \#\# Criterios terminado \[checklist subfase\] \#\# Próximo: \[siguiente subfase\] CRITERIOS TERMINADO \- \[criterios salida roadmap\]. \- CI local verde. \- E2E subfase OK. \- 0 secrets gitleaks.  |
| :---- |

**Ej. 0A:** ALCANCE: Repo limpio, docker-compose.dev.yml, .devcontainer.json. CRITERIOS: docker compose up 4 servicios healthy.

## **4\. Plantilla de auditoría por subfase**

**Plantilla reusable (por subfase):**

| AUDITORÍA PRANELY \- \[SUBFASE\] | Fecha: \[DD/MM\] | Auditor: \[Nombre/Modelo\] \*\*Qué se audita:\*\* Alcance/completitud/técnico/funcional/seguridad/documental. \*\*Checklist completitud\*\* \- \[ \] Entregables 100% (archivos/código/tests). \- \[ \] Hechos/supuestos/riesgos separados. \- \[ \] Dependencias/criterios salida cubiertos. \*\*Checklist técnico\*\* \- \[ \] No rompe contratos (OpenAPI diffs). \- \[ \] Multi-tenant (orgid filter tests). \- \[ \] Tests cobertura \>80% cambiado. \*\*Checklist funcional\*\* \- \[ \] Resuelve problema subfase. \- \[ \] Alineado MVP (P0 first). \- \[ \] E2E preview env OK. \*\*Checklist seguridad\*\* \- \[ \] 0 secrets (gitleaks). \- \[ \] RBAC/least privilege tests. \- \[ \] No BYPASS\_AUTH prod. \*\*Checklist consistencia\*\* \- \[ \] Naming PRANELY normalizado. \- \[ \] Actualiza PRD/roadmap/models. \*\*Hallazgos\*\* | Hallazgo | Severidad | Decisión | |----------|-----------|----------| | \[ej.\]   | Alta     | Observaciones | \*\*Decisión global:\*\* ☐ Aprobado ☐ Observaciones ☐ Rechazado   \*\*Acciones:\*\* \[lista con owner/fecha\].  |
| :---- |

**Ej. gates severidad:** Crítica (secretos/BYPASS) bloquea; Alta (regresiones) requiere fix inmediato.

## **5\. Skill persistente “Pranely Operating System”**

**Identidad/propósito:** IA persistente (Chief Architect/Staff Eng/DevSecOps) para PRANELY. Convierte requests en cambios seguros/auditables alineados roadmap, priorizando estabilidad/seguridad sobre velocidad.

**Contexto permanente:** SaaS residuos MX/LATAM (Next.js15/FastAPI3.12/PG16/Redis7/RQ/Docker/Nginx/DeepInfra/Stripe). Multi-tenant orgid, inmutable post-validated, i18n ES/EN.

**Principios:** Un cambio/vez; pipelines única entrada; "not tested=broken"; rules→tests auto; tenant isolation non-negociable.

**Priorización:** P0: auth/dashboard/waste/upload/seguridad; P1: bridge/command/billing/legal básico; P2+: expansions.

**Reglas arquitectura:** Desacoplado/services, async RQ, circuit-breakers/retries, feature flags, backward migrations.

**Reglas doc:** Markdown estructurado; naming PRANELY; "No datos suficientes → propone inicial"; ADRs cambios archi.

**Reglas seguridad:** No secrets hardcode; no BYPASS prod; least privilege/MFA sensibles; SAST/DAST CI; rotación auto.

**Reglas testing:** Pyramid (unit/int/contract/e2e/regression bugs históricos); coverage 80% crítico.

**Reglas deploy:** Inmutable contenedores; blue-green/rollback auto; healthchecks profundos (DB/Redis/worker/auth); previews PR.

**Reglas no-regresión:** No multi-dominio/prompt; no legacy/quarantine; gates CI; postmortem sin culpa.

**Formato respuesta:** Objetivo/contexto/hechos/supuestos/plan/código/tests/riesgos/rollback/checklist/aceptación.

**Estilo:** Ejecutivo/operativo/sin relleno/artefactos aplicables.

**Nunca hacer:** Inventar data; cambiar stack sin RFC; ocultar conflictos; aprobar sin seguridad/tenant/tests.

**Autocontrol pre-respuesta:** ¿Respeta OS? ¿Deuda nueva? ¿Testeado? ¿Tenant/audit? ¿Consistente maestro?.

## **6\. Visión de negocio y propuesta de valor en una página**

**Visión:** Estándar operativo/legal para economía circular industrial: trazabilidad inmutable/automatizada/auditada por IA en LATAM.

**Problema mercado:** Procesos manuales → multas (PROFEPA/SEMARNAT), pérdida manifiestos, opacidad chain-of-custody.

**Propuesta valor:** Automatiza trazabilidad/compliance residuos: IA extrae manifiestos (85%+ precisión), radar proactivo NOMs, bridge móvil real-time, dashboard multi-tenant.

**Diferenciadores:** Bridge QR/WS campo; Jurista IA NOM-específica; inmutable auditlogs design-time; compliance-first (no solo docs).

**Por qué ahora:** ESG presión 2026; Qwen accesible; dolor post-pandemia supply-chain.

**Para quién:** Generadores SMB/Enterprise (manufactura/minera); Gestores/transportistas MX/LATAM.

**Resultado cliente:** \-70% tiempo docs; cero multas; auditorías instantáneas; ROI cuotas/planes.

**Narrativa:** No software logística: copiloto legal/operativo ambiental.

## **7\. Perfil de clientes y segmentos prioritarios**

**Segmentos primarios:**

* Generadores SMB/Enterprise (manufactura/farmacéutica/minera).  
* Gestores/transportistas autorizados.

**Secundarios:** Consultoras/auditores ambientales.

**Buyer persona:** Director Planta/Compliance (45-55, técnico, anti-multas).  
**Usuario operador:** Campo/logística (25-40, captura rápida).

**Pains:** Multas/manualidad/opacidad; conectividad campo; costo IA.  
**Gains:** Compliance auto; visibilidad real-time; ROI volumen docs.

**Barreras:** Confianza IA; digitalización campo; pricing inicial.

**Señales prioridad:** Auditorías recientes; \>500 tons/mes; \>10 camiones.

| Segmento | Prioridad | Razón |
| :---- | :---- | :---- |
| Generador SMB/Ent | P0 | Dashboard/upload/IA/trazabilidad/monetización simple[2.PRD-Maestro-Operativo-completo-VERSION-CHATGPT-5.4-THINKING-2.md](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/79034917/b640d2c0-b645-44e5-a619-401e5627e898/2.PRD-Maestro-Operativo-completo-VERSION-CHATGPT-5.4-THINKING-2.md?AWSAccessKeyId=ASIA2F3EMEYESQWDUHJ4&Signature=lCpaZ9d9yRgbeRbysUUASWDnw08%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEFkaCXVzLWVhc3QtMSJGMEQCIE9w5ES55BL1qDZUrr6peTb6hDunfSoxX34yVrGYrZP5AiBQ6fCz5%2FfOJ6aZWfu3A3fidGt%2ByFSeA17cFPkrdOYquirzBAgiEAEaDDY5OTc1MzMwOTcwNSIMXj2DtAi7nKFnoENaKtAEZoTR%2FcBNgo7hgotsLn8ivz6XcoJxVov59JdN015h%2B4MF4KpuebKZUt6vbdV5BvMzhhf5OeTdiAVI1vwswei%2BRkofxQNDrbyerEOueMuu6QvD%2Bdrmsf8P8IF8P77E%2BveJxUfARSS10ABwdMFtSu6r6IjM7KYGHQ1mySXl%2BoV5qRzBFX3Rk3lN8B5EDr4FUBNKng2aOOnfz6q3Vl4s50ckfdaI7%2Fxvq4b3L5UBCuPjsjuPhOHXeKZfJPjQW1RpbQZQ5PBqYjmGVq97mBK%2BykVpswNGTxzS76yTaU15HFS8CnrA1dWsGJc0eI%2F1Ol%2FAqR2Fq0CYDGwH3JaSYo7uYi1wEI%2FZcKogPVey%2Bwqs15Do136lWXF30gk5hSnEPs3HQPW2pPB4SJETm4MO7w6ry8VAcNFX3qz4qWwxzspFJGM7gNviBppxIJwaW24iUk59mwFijn3Mjf45EtKZ7oiC6vFgymc%2BnjTEL98uFrUPBiZ%2FSIfzt0sC%2F6Vj4nZ%2FhZbmXfgXp7lAM4chvFcMkSFPiVpU4pzPvZwCjecTjG7u%2BdXNtf9zOCgvnrbV9P%2BYOqFzkez7sYJYO%2BXDYVgkoCp3VcdH%2FO0bjk4%2FcYgSjvBcQCvg2oekuS3yykrNmaLLLLwqL2JkgZ8Q85zx8ZzJcZ%2BocjCFVPsbQxNrykJcZ6ZJQVxf%2B31L1I3gdVcvoLfAIdWplCns5wOMXm514CDpPqNT72SHlEUPRPRZ%2BxWLs9qKztU9CrSfYrTXuZISW%2BbwG9ABr4aGgeaFsxWIBFH2PF%2FNR0jUfDCwppnPBjqZAaw76SfT3gx%2BCoYBOHpLSPaeDkhEGpTrGvJDEiuxWB1vSVbb3rTt7gCnjzTu%2BSdUyOHelYHs%2BkYlRROLfxAJ%2FP0CReiYvD2sr5%2F5jCOg%2FqK2e8k%2FPF%2FsByv7DLUaDx%2B9Yb4l1ErOTuGF1ttZQSc0A7KTEMXHF66nNqMeCtOsez3yh1Y0shUdpiNMJoMSXiygu%2FFN7Bg7aAcbiw%3D%3D&Expires=1776702886). |
| Gestor/transp. | P0 | Bridge/movimientos/campo[4.PRD-Maestro-Operativo-completo-VERSION-GEMINI-3.1-PRO-4.md](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/79034917/5bb47f66-783a-44d4-9094-33c60743ea8c/4.PRD-Maestro-Operativo-completo-VERSION-GEMINI-3.1-PRO-4.md?AWSAccessKeyId=ASIA2F3EMEYESQWDUHJ4&Signature=wd7CNmS6rd4RBytHjY9DAYZSAkI%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEFkaCXVzLWVhc3QtMSJGMEQCIE9w5ES55BL1qDZUrr6peTb6hDunfSoxX34yVrGYrZP5AiBQ6fCz5%2FfOJ6aZWfu3A3fidGt%2ByFSeA17cFPkrdOYquirzBAgiEAEaDDY5OTc1MzMwOTcwNSIMXj2DtAi7nKFnoENaKtAEZoTR%2FcBNgo7hgotsLn8ivz6XcoJxVov59JdN015h%2B4MF4KpuebKZUt6vbdV5BvMzhhf5OeTdiAVI1vwswei%2BRkofxQNDrbyerEOueMuu6QvD%2Bdrmsf8P8IF8P77E%2BveJxUfARSS10ABwdMFtSu6r6IjM7KYGHQ1mySXl%2BoV5qRzBFX3Rk3lN8B5EDr4FUBNKng2aOOnfz6q3Vl4s50ckfdaI7%2Fxvq4b3L5UBCuPjsjuPhOHXeKZfJPjQW1RpbQZQ5PBqYjmGVq97mBK%2BykVpswNGTxzS76yTaU15HFS8CnrA1dWsGJc0eI%2F1Ol%2FAqR2Fq0CYDGwH3JaSYo7uYi1wEI%2FZcKogPVey%2Bwqs15Do136lWXF30gk5hSnEPs3HQPW2pPB4SJETm4MO7w6ry8VAcNFX3qz4qWwxzspFJGM7gNviBppxIJwaW24iUk59mwFijn3Mjf45EtKZ7oiC6vFgymc%2BnjTEL98uFrUPBiZ%2FSIfzt0sC%2F6Vj4nZ%2FhZbmXfgXp7lAM4chvFcMkSFPiVpU4pzPvZwCjecTjG7u%2BdXNtf9zOCgvnrbV9P%2BYOqFzkez7sYJYO%2BXDYVgkoCp3VcdH%2FO0bjk4%2FcYgSjvBcQCvg2oekuS3yykrNmaLLLLwqL2JkgZ8Q85zx8ZzJcZ%2BocjCFVPsbQxNrykJcZ6ZJQVxf%2B31L1I3gdVcvoLfAIdWplCns5wOMXm514CDpPqNT72SHlEUPRPRZ%2BxWLs9qKztU9CrSfYrTXuZISW%2BbwG9ABr4aGgeaFsxWIBFH2PF%2FNR0jUfDCwppnPBjqZAaw76SfT3gx%2BCoYBOHpLSPaeDkhEGpTrGvJDEiuxWB1vSVbb3rTt7gCnjzTu%2BSdUyOHelYHs%2BkYlRROLfxAJ%2FP0CReiYvD2sr5%2F5jCOg%2FqK2e8k%2FPF%2FsByv7DLUaDx%2B9Yb4l1ErOTuGF1ttZQSc0A7KTEMXHF66nNqMeCtOsez3yh1Y0shUdpiNMJoMSXiygu%2FFN7Bg7aAcbiw%3D%3D&Expires=1776702886). |
| Enterprise reg. | P1 | Compliance/observabilidad full[1.PRANELY-SISTEMA-DOCUMENTAL-MAESTRO-v1-VERSION-CLAUDE-SONNET.md](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/79034917/6b96b7b1-4315-4fcb-be96-7cff21ffe931/1.PRANELY-SISTEMA-DOCUMENTAL-MAESTRO-v1-VERSION-CLAUDE-SONNET.md?AWSAccessKeyId=ASIA2F3EMEYESQWDUHJ4&Signature=z4q6RKG2hljGQacT1tjRKJOf6zM%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEFkaCXVzLWVhc3QtMSJGMEQCIE9w5ES55BL1qDZUrr6peTb6hDunfSoxX34yVrGYrZP5AiBQ6fCz5%2FfOJ6aZWfu3A3fidGt%2ByFSeA17cFPkrdOYquirzBAgiEAEaDDY5OTc1MzMwOTcwNSIMXj2DtAi7nKFnoENaKtAEZoTR%2FcBNgo7hgotsLn8ivz6XcoJxVov59JdN015h%2B4MF4KpuebKZUt6vbdV5BvMzhhf5OeTdiAVI1vwswei%2BRkofxQNDrbyerEOueMuu6QvD%2Bdrmsf8P8IF8P77E%2BveJxUfARSS10ABwdMFtSu6r6IjM7KYGHQ1mySXl%2BoV5qRzBFX3Rk3lN8B5EDr4FUBNKng2aOOnfz6q3Vl4s50ckfdaI7%2Fxvq4b3L5UBCuPjsjuPhOHXeKZfJPjQW1RpbQZQ5PBqYjmGVq97mBK%2BykVpswNGTxzS76yTaU15HFS8CnrA1dWsGJc0eI%2F1Ol%2FAqR2Fq0CYDGwH3JaSYo7uYi1wEI%2FZcKogPVey%2Bwqs15Do136lWXF30gk5hSnEPs3HQPW2pPB4SJETm4MO7w6ry8VAcNFX3qz4qWwxzspFJGM7gNviBppxIJwaW24iUk59mwFijn3Mjf45EtKZ7oiC6vFgymc%2BnjTEL98uFrUPBiZ%2FSIfzt0sC%2F6Vj4nZ%2FhZbmXfgXp7lAM4chvFcMkSFPiVpU4pzPvZwCjecTjG7u%2BdXNtf9zOCgvnrbV9P%2BYOqFzkez7sYJYO%2BXDYVgkoCp3VcdH%2FO0bjk4%2FcYgSjvBcQCvg2oekuS3yykrNmaLLLLwqL2JkgZ8Q85zx8ZzJcZ%2BocjCFVPsbQxNrykJcZ6ZJQVxf%2B31L1I3gdVcvoLfAIdWplCns5wOMXm514CDpPqNT72SHlEUPRPRZ%2BxWLs9qKztU9CrSfYrTXuZISW%2BbwG9ABr4aGgeaFsxWIBFH2PF%2FNR0jUfDCwppnPBjqZAaw76SfT3gx%2BCoYBOHpLSPaeDkhEGpTrGvJDEiuxWB1vSVbb3rTt7gCnjzTu%2BSdUyOHelYHs%2BkYlRROLfxAJ%2FP0CReiYvD2sr5%2F5jCOg%2FqK2e8k%2FPF%2FsByv7DLUaDx%2B9Yb4l1ErOTuGF1ttZQSc0A7KTEMXHF66nNqMeCtOsez3yh1Y0shUdpiNMJoMSXiygu%2FFN7Bg7aAcbiw%3D%3D&Expires=1776702886). |
| Legal heavy | P2 | Radar/Jurista expandido[3.PAQUETE-MAESTRO-DE-DEFINICION-DE-PRODUCTO-Y-EJECUCION-PRANELY-VERSION-GROK-4.2-REASONING-3.md](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/79034917/4c202b18-bdb6-41f8-b65b-cdf2162ed5ec/3.PAQUETE-MAESTRO-DE-DEFINICION-DE-PRODUCTO-Y-EJECUCION-PRANELY-VERSION-GROK-4.2-REASONING-3.md?AWSAccessKeyId=ASIA2F3EMEYESQWDUHJ4&Signature=jp%2FoF2cZRz%2F%2Bmpb7B97BrNgG9vU%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEFkaCXVzLWVhc3QtMSJGMEQCIE9w5ES55BL1qDZUrr6peTb6hDunfSoxX34yVrGYrZP5AiBQ6fCz5%2FfOJ6aZWfu3A3fidGt%2ByFSeA17cFPkrdOYquirzBAgiEAEaDDY5OTc1MzMwOTcwNSIMXj2DtAi7nKFnoENaKtAEZoTR%2FcBNgo7hgotsLn8ivz6XcoJxVov59JdN015h%2B4MF4KpuebKZUt6vbdV5BvMzhhf5OeTdiAVI1vwswei%2BRkofxQNDrbyerEOueMuu6QvD%2Bdrmsf8P8IF8P77E%2BveJxUfARSS10ABwdMFtSu6r6IjM7KYGHQ1mySXl%2BoV5qRzBFX3Rk3lN8B5EDr4FUBNKng2aOOnfz6q3Vl4s50ckfdaI7%2Fxvq4b3L5UBCuPjsjuPhOHXeKZfJPjQW1RpbQZQ5PBqYjmGVq97mBK%2BykVpswNGTxzS76yTaU15HFS8CnrA1dWsGJc0eI%2F1Ol%2FAqR2Fq0CYDGwH3JaSYo7uYi1wEI%2FZcKogPVey%2Bwqs15Do136lWXF30gk5hSnEPs3HQPW2pPB4SJETm4MO7w6ry8VAcNFX3qz4qWwxzspFJGM7gNviBppxIJwaW24iUk59mwFijn3Mjf45EtKZ7oiC6vFgymc%2BnjTEL98uFrUPBiZ%2FSIfzt0sC%2F6Vj4nZ%2FhZbmXfgXp7lAM4chvFcMkSFPiVpU4pzPvZwCjecTjG7u%2BdXNtf9zOCgvnrbV9P%2BYOqFzkez7sYJYO%2BXDYVgkoCp3VcdH%2FO0bjk4%2FcYgSjvBcQCvg2oekuS3yykrNmaLLLLwqL2JkgZ8Q85zx8ZzJcZ%2BocjCFVPsbQxNrykJcZ6ZJQVxf%2B31L1I3gdVcvoLfAIdWplCns5wOMXm514CDpPqNT72SHlEUPRPRZ%2BxWLs9qKztU9CrSfYrTXuZISW%2BbwG9ABr4aGgeaFsxWIBFH2PF%2FNR0jUfDCwppnPBjqZAaw76SfT3gx%2BCoYBOHpLSPaeDkhEGpTrGvJDEiuxWB1vSVbb3rTt7gCnjzTu%2BSdUyOHelYHs%2BkYlRROLfxAJ%2FP0CReiYvD2sr5%2F5jCOg%2FqK2e8k%2FPF%2FsByv7DLUaDx%2B9Yb4l1ErOTuGF1ttZQSc0A7KTEMXHF66nNqMeCtOsez3yh1Y0shUdpiNMJoMSXiygu%2FFN7Bg7aAcbiw%3D%3D&Expires=1776702886). |

## **8\. Mapa de usuarios y permisos reales**

**Tipos usuarios:** Owner (full tenant), Admin (ops), Member (daily), Viewer (read), Director (global Command).

| Módulo | Owner | Admin | Member | Viewer | Director |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Auth/perfil | Gestión miembros | Ops básica | Acceso propio | Acceso propio | Global auth |
| Dashboard | Full/act | Full/act | Full/act | Read | Supervisión |
| Waste CRUD | Full (approve/export) | Full | Create/edit policy | Read | Supervisión |
| Review/verify | Full | Full | Ops | Read (si habilita) | Supervisión |
| Mobile Bridge | Full | Full | Uso | No | Config adv |
| Command Center | Parcial alto | Parcial | Restringido | No | Full |
| Legal Radar | Full/act | Full/act | View/ops | Read | Config/sup |
| Billing/Settings | Full (pay) | View/limited | No | No | Quotas globales[1.PRANELY-SISTEMA-DOCUMENTAL-MAESTRO-v1-VERSION-CLAUDE-SONNET.md](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/79034917/6b96b7b1-4315-4fcb-be96-7cff21ffe931/1.PRANELY-SISTEMA-DOCUMENTAL-MAESTRO-v1-VERSION-CLAUDE-SONNET.md?AWSAccessKeyId=ASIA2F3EMEYESQWDUHJ4&Signature=z4q6RKG2hljGQacT1tjRKJOf6zM%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEFkaCXVzLWVhc3QtMSJGMEQCIE9w5ES55BL1qDZUrr6peTb6hDunfSoxX34yVrGYrZP5AiBQ6fCz5%2FfOJ6aZWfu3A3fidGt%2ByFSeA17cFPkrdOYquirzBAgiEAEaDDY5OTc1MzMwOTcwNSIMXj2DtAi7nKFnoENaKtAEZoTR%2FcBNgo7hgotsLn8ivz6XcoJxVov59JdN015h%2B4MF4KpuebKZUt6vbdV5BvMzhhf5OeTdiAVI1vwswei%2BRkofxQNDrbyerEOueMuu6QvD%2Bdrmsf8P8IF8P77E%2BveJxUfARSS10ABwdMFtSu6r6IjM7KYGHQ1mySXl%2BoV5qRzBFX3Rk3lN8B5EDr4FUBNKng2aOOnfz6q3Vl4s50ckfdaI7%2Fxvq4b3L5UBCuPjsjuPhOHXeKZfJPjQW1RpbQZQ5PBqYjmGVq97mBK%2BykVpswNGTxzS76yTaU15HFS8CnrA1dWsGJc0eI%2F1Ol%2FAqR2Fq0CYDGwH3JaSYo7uYi1wEI%2FZcKogPVey%2Bwqs15Do136lWXF30gk5hSnEPs3HQPW2pPB4SJETm4MO7w6ry8VAcNFX3qz4qWwxzspFJGM7gNviBppxIJwaW24iUk59mwFijn3Mjf45EtKZ7oiC6vFgymc%2BnjTEL98uFrUPBiZ%2FSIfzt0sC%2F6Vj4nZ%2FhZbmXfgXp7lAM4chvFcMkSFPiVpU4pzPvZwCjecTjG7u%2BdXNtf9zOCgvnrbV9P%2BYOqFzkez7sYJYO%2BXDYVgkoCp3VcdH%2FO0bjk4%2FcYgSjvBcQCvg2oekuS3yykrNmaLLLLwqL2JkgZ8Q85zx8ZzJcZ%2BocjCFVPsbQxNrykJcZ6ZJQVxf%2B31L1I3gdVcvoLfAIdWplCns5wOMXm514CDpPqNT72SHlEUPRPRZ%2BxWLs9qKztU9CrSfYrTXuZISW%2BbwG9ABr4aGgeaFsxWIBFH2PF%2FNR0jUfDCwppnPBjqZAaw76SfT3gx%2BCoYBOHpLSPaeDkhEGpTrGvJDEiuxWB1vSVbb3rTt7gCnjzTu%2BSdUyOHelYHs%2BkYlRROLfxAJ%2FP0CReiYvD2sr5%2F5jCOg%2FqK2e8k%2FPF%2FsByv7DLUaDx%2B9Yb4l1ErOTuGF1ttZQSc0A7KTEMXHF66nNqMeCtOsez3yh1Y0shUdpiNMJoMSXiygu%2FFN7Bg7aAcbiw%3D%3D&Expires=1776702886). |

**Restricciones:** Cross-tenant prohibido; viewer no muta; director platform vs tenant separado. **Sensibles:** Rotación claves/cuotas/billing MFA. **Prohibidas:** Acceso sin membership; BYPASS prod.

## **9\. Casos de uso end-to-end priorizados**

| Prioridad | Nombre | Actor | Disparador | Flujo principal | Alternos/Errores | Resultado | Depend. | Módulos |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| P0 | Login-dashboard | Cualquiera | Credenciales | POST /auth/login → JWT → dashboard KPIs | 500 Content-Type, token inválido | Acceso tenant-isolado | Auth models | Auth/dashboard |
| P0 | Upload-procesar IA | Owner/admin/member | Drag-drop PDF | Upload → RQ pending → OCR/DeepInfra → inreview/rejected | Schema fail → exception; quota block | Estado updated, auditlog | Waste/IA | Upload/review |
| P0 | Aprobar/archive movimiento | Admin/member | Acción tabla | PATCH approve → isimmutable=true; DELETE → archivedat | Ya immutable → 403 | Inmutable/auditable | Waste | Dashboard/waste |
| P1 | Mobile Bridge sync | Member/campo | Escanea QR | POST bridge/session → WS connect → capture → sync dashboard | Reconexión fail → backoff | Docs campo → dashboard real-time | Bridge | Mobile/dashboard |
| P1 | Review queue manual | Admin | Acceso /review | GET queue → filter → edit → approve | Low confidence highlight | Ciclo → validated | Review | Review/extraction |
| P1 | Checkout Stripe | Owner | Upgrade plan | POST billing/checkout → webhook → quota update | Firma fail → retry | Suscripción activa/limits | Billing | Settings/billing |
| P2 | Radar legal alert | Scheduler/owner | Diario 07:00 MX | Scrape DOF/SEMARNAT → Jurista → alert org | Fuente change → manual scan | Notificación proactiva | Legal | Radar/dashboard2.PRD-Maestro-Operativo-completo-VERSION-CHATGPT-5.4-THINKING-2.md+1. |

## **10\. Catálogo de funcionalidades por módulo**

| Módulo | Objetivo | Funcionalidades | Prioridad | Depend. | Complejidad | Riesgo | Estado |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Landing | Captación | CTAs/pricing/features | P2 | Frontend/billing | Baja | Baja | MVP |
| Auth | Acceso seguro | Login/registro/JWT/refresh | P0 | Users/memberships | Media | Crítica | MVP |
| Dashboard | Visibilidad | KPIs/tabla/polling/actions | P0 | Waste/legal | Media | Alta | MVP |
| Waste Core | Transaccional | CRUD/approve/archive/export | P0 | DB/audit | Alta | Alta | MVP |
| Upload/Ingest | Entrada docs | Upload/RQ/estados/queue | P0 | Storage/worker/DeepInfra | Alta | Alta | MVP |
| Review/Verification | Validación | Queue/filter/edit/approve | P1 | Waste/upload | Media | Media | MVP |
| Mobile Bridge | Campo | QR/session/WS/sync/reconnect | P1 | Bridge/auth | Alta | Media | MVP |
| Command Center | Admin | Configs/operators/quotas/toggles | P1 | Roles/orgs/audit | Media | Alta | MVP básico |
| Legal Radar | Vigilancia | Scan/scheduler/alerts/archive | P2 | APScheduler/IA | Alta | Media | Post-MVP básico |
| AI Console | Pruebas IA | Playground/chat/action-execute | P3 | IA/costos | Alta | Alta | Post-MVP |
| Billing | Monetización | Checkout/webhooks/subscriptions/quotas | P1 | Stripe/plans | Media | Alta | MVP |
| Settings | Config | Account/org/upgrade/quotas | P2 | Auth/orgs/billing | Media | Media | MVP reducido2.PRD-Maestro-Operativo-completo-VERSION-CHATGPT-5.4-THINKING-2.md+1. |

## **11\. Reglas de negocio y validaciones del dominio**

**Globales:** Acceso filtra organizationid/membership; cambios sensibles → auditlogs; soft-delete archivedat (no hard DELETE); inmutable post-validated (isimmutable=true); cuotas pre-upload (402 si locked).

**Por módulo:**

* **Auth:** JWT 24h HS256/Argon2id; Content-Type urlencoded login.  
* **Waste:** Estados: pending/inreview/validated/exception/rejected; approve → inmutable.  
* **Billing:** UsageCycle docsused vs limit; webhook idempotente.  
* **Legal:** Alertas distribuida org; archive soft.

**Validaciones entrada:** Archivo tipo/size/quota; schema Pydantic IA JSON.  
**Estado:** Rejected → reprocess OK; validated → no edit.  
**Rol:** Viewer no muta; director platform ≠ tenant.  
**Temporales:** Scheduler 07:00 MX; JWT 24h.  
**Legales:** NOM-052 implemented (clasif.); LFPDPPP backlog (consent/ARCO).  
**→ Tests auto:** Isolation orgid; no edit inmutable; quota block; webhook sig.

## **12\. Arquitectura funcional y técnica resumida**

**Tipo/canales:** SaaS web-responsive/PWA \+ bridge móvil (no nativa MVP).

* **Frontend:** Next.js 15 App Router/TS/Tailwind; EventBus nativo (no Redux); SSR+CSR hybrid; i18n next-intl ES/EN.  
* **Backend:** FastAPI/Pydantic/SQLAlchemy; routers dominio (auth/waste/bridge/legal/billing).  
* **DB:** PG16 (orgid index/partition); no SQLite legacy.  
* **Auth:** JWT jose/Argon2id; RBAC claims \+ middleware.  
* **Storage:** Docker volumes uploads/orgid/uuid (S3 post-MVP).  
* **Async:** Redis7/RQ workers/docs; APScheduler radar 07:00.  
* **Observabilidad:** Structlog correlacionado; Prometheus/Grafana/SLOs/alertas.  
* **Seguridad:** Secrets manager/Vault rotación; SAST/DAST CI; MFA sensible; CSP/HSTS Nginx.  
* **Deploy:** Docker Compose dev/prod; blue-green/rollback; previews PR; chaos mensual.

**Justificación:** Stack probado/IA-friendly; rebuild disciplina \> rewrite; escalable LATAM VPS inicial.

## **13\. Modelo de datos funcional**

**Entidades clave:**

* **organizations:** id (PK), name/legalname, industry/segment (generator/gestor), stripecustomerid, isactive.  
* **users:** id (PK), email (unique), hashedpw (Argon2id), fullname/locale, isactive.  
* **memberships:** userid/orgid/rol (owner/admin/member/viewer).  
* **wastemovements:** id/orgid (FK/index), manifestnumber/type/quantity/unit/date/confidencescore/status (enum), isimmutable/archivedat/filepath/origfilename.  
* **plans/subscriptions/usagecycles:** code/name/priceusd, orgid/planid/status/externalsubid, doccount/used/islocked/limitsnapshot.  
* **auditlogs/aiauditlogs:** orgid/userid/action/resource/result/payload/timestamp/tokens/cost/confidence.

**Relaciones:** User 1:N memberships N:1 org; org 1:N movements/alerts/subscriptions/audits.  
**Claves negocio:** orgid+manifestnumber+date unique; email user unique.  
**Estados:** Waste: pending/inreview/validated/exception/rejected.  
**Auditoría:** Obligatoria mutaciones sensibles/IA/cambios admin.  
**Multi-tenant:** Filter orgid queries; RLS futuro.  
**Tablas add:** featureflags, jobruns, webhookevents (post-MVP).  
**Riesgos:** create\_all() → Alembic full; orgid nullable ops → NOT NULL policy.

## **14\. Integraciones externas reales**

| Integración | Propósito | Dirección | Criticidad | Datos | Riesgo operativo | Legal/contractual | Fallback | Prioridad |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Stripe | Pagos/suscripciones | Bi-dir (checkout/webhooks) | Alta | Customer/plan/status/usage | Cobros fail/sync loss | Sí (fiscal) | Grace period/retry idemp | P0/MVP[2.PRD-Maestro-Operativo-completo-VERSION-CHATGPT-5.4-THINKING-2.md](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/79034917/b640d2c0-b645-44e5-a619-401e5627e898/2.PRD-Maestro-Operativo-completo-VERSION-CHATGPT-5.4-THINKING-2.md?AWSAccessKeyId=ASIA2F3EMEYESQWDUHJ4&Signature=lCpaZ9d9yRgbeRbysUUASWDnw08%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEFkaCXVzLWVhc3QtMSJGMEQCIE9w5ES55BL1qDZUrr6peTb6hDunfSoxX34yVrGYrZP5AiBQ6fCz5%2FfOJ6aZWfu3A3fidGt%2ByFSeA17cFPkrdOYquirzBAgiEAEaDDY5OTc1MzMwOTcwNSIMXj2DtAi7nKFnoENaKtAEZoTR%2FcBNgo7hgotsLn8ivz6XcoJxVov59JdN015h%2B4MF4KpuebKZUt6vbdV5BvMzhhf5OeTdiAVI1vwswei%2BRkofxQNDrbyerEOueMuu6QvD%2Bdrmsf8P8IF8P77E%2BveJxUfARSS10ABwdMFtSu6r6IjM7KYGHQ1mySXl%2BoV5qRzBFX3Rk3lN8B5EDr4FUBNKng2aOOnfz6q3Vl4s50ckfdaI7%2Fxvq4b3L5UBCuPjsjuPhOHXeKZfJPjQW1RpbQZQ5PBqYjmGVq97mBK%2BykVpswNGTxzS76yTaU15HFS8CnrA1dWsGJc0eI%2F1Ol%2FAqR2Fq0CYDGwH3JaSYo7uYi1wEI%2FZcKogPVey%2Bwqs15Do136lWXF30gk5hSnEPs3HQPW2pPB4SJETm4MO7w6ry8VAcNFX3qz4qWwxzspFJGM7gNviBppxIJwaW24iUk59mwFijn3Mjf45EtKZ7oiC6vFgymc%2BnjTEL98uFrUPBiZ%2FSIfzt0sC%2F6Vj4nZ%2FhZbmXfgXp7lAM4chvFcMkSFPiVpU4pzPvZwCjecTjG7u%2BdXNtf9zOCgvnrbV9P%2BYOqFzkez7sYJYO%2BXDYVgkoCp3VcdH%2FO0bjk4%2FcYgSjvBcQCvg2oekuS3yykrNmaLLLLwqL2JkgZ8Q85zx8ZzJcZ%2BocjCFVPsbQxNrykJcZ6ZJQVxf%2B31L1I3gdVcvoLfAIdWplCns5wOMXm514CDpPqNT72SHlEUPRPRZ%2BxWLs9qKztU9CrSfYrTXuZISW%2BbwG9ABr4aGgeaFsxWIBFH2PF%2FNR0jUfDCwppnPBjqZAaw76SfT3gx%2BCoYBOHpLSPaeDkhEGpTrGvJDEiuxWB1vSVbb3rTt7gCnjzTu%2BSdUyOHelYHs%2BkYlRROLfxAJ%2FP0CReiYvD2sr5%2F5jCOg%2FqK2e8k%2FPF%2FsByv7DLUaDx%2B9Yb4l1ErOTuGF1ttZQSc0A7KTEMXHF66nNqMeCtOsez3yh1Y0shUdpiNMJoMSXiygu%2FFN7Bg7aAcbiw%3D%3D&Expires=1776702886) |
| DeepInfra-Qwen | OCR/triage/extracción IA/Jurista | Saliente | Alta | Docs/prompts → JSON score/cost | Latencia 10-20s/schema error | Sí | Manual review/exception | P0/MVP |
| DOF/SEMARNAT/PROFEPA/ASEA | Radar regulatorio | Entrante (scrape) | Media | Eventos HTML/textos | Fuente change/ruido | Uso público | Manual scan/backlog | P1/post-MVP |
| Redis | Colas/cache/sesiones | Interno | Alta | Jobs/estados temp | Stuck queue | No | Retries/DLQ persist | P0 |
| Nginx/Let's Encrypt | Proxy/TLS | Interno | Alta | HTTPS/headers/routing | Exposición directa | Operativa | Rollback config/health | P0[4.PRD-Maestro-Operativo-completo-VERSION-GEMINI-3.1-PRO-4.md](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/79034917/5bb47f66-783a-44d4-9094-33c60743ea8c/4.PRD-Maestro-Operativo-completo-VERSION-GEMINI-3.1-PRO-4.md?AWSAccessKeyId=ASIA2F3EMEYESQWDUHJ4&Signature=wd7CNmS6rd4RBytHjY9DAYZSAkI%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEFkaCXVzLWVhc3QtMSJGMEQCIE9w5ES55BL1qDZUrr6peTb6hDunfSoxX34yVrGYrZP5AiBQ6fCz5%2FfOJ6aZWfu3A3fidGt%2ByFSeA17cFPkrdOYquirzBAgiEAEaDDY5OTc1MzMwOTcwNSIMXj2DtAi7nKFnoENaKtAEZoTR%2FcBNgo7hgotsLn8ivz6XcoJxVov59JdN015h%2B4MF4KpuebKZUt6vbdV5BvMzhhf5OeTdiAVI1vwswei%2BRkofxQNDrbyerEOueMuu6QvD%2Bdrmsf8P8IF8P77E%2BveJxUfARSS10ABwdMFtSu6r6IjM7KYGHQ1mySXl%2BoV5qRzBFX3Rk3lN8B5EDr4FUBNKng2aOOnfz6q3Vl4s50ckfdaI7%2Fxvq4b3L5UBCuPjsjuPhOHXeKZfJPjQW1RpbQZQ5PBqYjmGVq97mBK%2BykVpswNGTxzS76yTaU15HFS8CnrA1dWsGJc0eI%2F1Ol%2FAqR2Fq0CYDGwH3JaSYo7uYi1wEI%2FZcKogPVey%2Bwqs15Do136lWXF30gk5hSnEPs3HQPW2pPB4SJETm4MO7w6ry8VAcNFX3qz4qWwxzspFJGM7gNviBppxIJwaW24iUk59mwFijn3Mjf45EtKZ7oiC6vFgymc%2BnjTEL98uFrUPBiZ%2FSIfzt0sC%2F6Vj4nZ%2FhZbmXfgXp7lAM4chvFcMkSFPiVpU4pzPvZwCjecTjG7u%2BdXNtf9zOCgvnrbV9P%2BYOqFzkez7sYJYO%2BXDYVgkoCp3VcdH%2FO0bjk4%2FcYgSjvBcQCvg2oekuS3yykrNmaLLLLwqL2JkgZ8Q85zx8ZzJcZ%2BocjCFVPsbQxNrykJcZ6ZJQVxf%2B31L1I3gdVcvoLfAIdWplCns5wOMXm514CDpPqNT72SHlEUPRPRZ%2BxWLs9qKztU9CrSfYrTXuZISW%2BbwG9ABr4aGgeaFsxWIBFH2PF%2FNR0jUfDCwppnPBjqZAaw76SfT3gx%2BCoYBOHpLSPaeDkhEGpTrGvJDEiuxWB1vSVbb3rTt7gCnjzTu%2BSdUyOHelYHs%2BkYlRROLfxAJ%2FP0CReiYvD2sr5%2F5jCOg%2FqK2e8k%2FPF%2FsByv7DLUaDx%2B9Yb4l1ErOTuGF1ttZQSc0A7KTEMXHF66nNqMeCtOsez3yh1Y0shUdpiNMJoMSXiygu%2FFN7Bg7aAcbiw%3D%3D&Expires=1776702886)[Memory](https://www.perplexity.ai/search/41271edb-80fc-4745-b0e0-8b3ffe041257). |

