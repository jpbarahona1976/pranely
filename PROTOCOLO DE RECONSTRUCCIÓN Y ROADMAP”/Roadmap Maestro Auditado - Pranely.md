# **Roadmap Maestro Auditado \- Pranely**

**Versión:** 1.0.0  
**Fecha:** 19 de abril de 2026  
**Estado:** CONGELADO \- No modificar sin RFC \+ 2 aprobaciones  
**Propósito:** Divide ejecución en subfases **0A-10C** con **gates de salida/bin bloqueo**. Minimax M2.7 ejecuta **UNA subfase por prompt**. Estados finales: **"Completada (lista auditoría)"** o **"Bloqueada (gate fallido)"**. No "casi listo".

**Reglas Globales:**

* **Ejecución ÚNICA en Dev Container/Docker.** Prohibido fuera.  
* **Pipeline CI VERDE obligatorio** antes merge (lint/typecheck/unit/integration/smoke/security).  
* **2 aprobaciones** infra/scripts base; 1 feature.  
* **Cada bug crítico → test regresión** antes fix merge.  
* **Output estructurado:** Checklist entregables \+ evidencia (comandos/logs/archivos).  
* **Gate fallido → STOP, post-mortem, fix → reintento subfase.**

## **Estructura de Subfases**

| FASE 0: Fundación (Semana 1\)   0A: Limpieza \+ Repo Base   0B: Dev Container \+ Versiones   0C: Docker Compose Dev FASE 1: Gobernanza CI/CD (Semana 1-2)   1A: Branch Protection \+ CODEOWNERS   1B: Pipeline CI Básico   1C: Secrets \+ Gitleaks FASE 2: Base de Datos (Semana 2\)   2A: Schema Normalizado \+ Alembic   2B: Migraciones Iniciales \+ Seed   2C: Tests DB Isolation FASE 3: Backend Auth (Semana 3\)   3A: FastAPI App Factory \+ Middleware   3B: JWT/RBAC/Tenant Filter   3C: Healthcheck \+ Rate Limit FASE 4: Backend Core Waste (Semana 3-4)   4A: Waste Models/Endpoints   4B: Repository Pattern \+ Soft-Delete   4C: OpenAPI Contract \+ Client Gen FASE 5: Workers Asíncronos (Semana 4\)   5A: RQ Redis Setup \+ Tasks Base   5B: IA Pipeline (DeepInfra Wrapper)   5C: Circuit Breaker \+ Idempotency FASE 6: Frontend Base (Semana 5\)   6A: Next.js Scaffold \+ TanStack Query   6B: Auth/Login/Register Forms   6C: Middleware \+ Error Boundary FASE 7: Frontend Dashboard (Semana 5-6)   7A: Dashboard Layout \+ KPIs   7B: Waste Table CRUD Hooks   7C: i18n ES/EN \+ Responsive FASE 8: Mobile Bridge \+ Billing (Semana 6\)   8A: Bridge QR/WS Client/Server   8B: Stripe Checkout/Callbacks   8C: Settings \+ Usage Tracking FASE 9: Testing Completo (Semana 7\)   9A: Unit/Integration Backend   9B: Unit/E2E Frontend Playwright   9C: Contract/Regression Historical FASE 10: Observabilidad \+ Deploy (Semana 8\)   10A: Logging/Metrics/Prometheus   10B: Blue/Green \+ Rollback Script   10C: Preview PR \+ Chaos Drill  |
| :---- |

## **Detalle por Subfase (con Gates)**

## **FASE 0: Fundación**

**0A: Limpieza \+ Repo Base**  
**Entregables:**

* Repo nuevo limpio (sin quarantine/SQLite/brain).  
* Estructura monorepo: apps/web/api, packages/ui, openapi/spec.yaml.  
* .gitignore \+ .env.example (placeholders).  
  **Comandos Evidencia:** git log \--oneline | wc \-l \<50, docker compose up levanta scaffold.  
  **Gate Salida:** make pre-flight pasa, repo \<100 commits.  
  **Bloqueo:** Archivos legacy detectados → listar \+ eliminar.  
  **Duración:** 4h.

**0B: Dev Container \+ Versiones**  
**Entregables:**

* .devcontainer/devcontainer.json \+ post-create.sh.  
* .tool-versions/.nvmrc/pyproject.toml: Node22.13.1/Python3.12.7/Docker27.4.  
* scripts/pre-flight-check.sh valida versiones.  
  **Comandos:** devcontainer up → todas versiones OK, npm ci && pip install.  
  **Gate:** make dev levanta 5 servicios healthy (30s).  
  **Bloqueo:** Versión mismatch → pin exacta.  
  **Duración:** 6h.

**0C: Docker Compose Dev**  
**Entregables:**

* docker-compose.dev.yml: frontend(3000)/backend(8000)/db(5432)/redis(6379)/mailhog.  
* Healthchecks todos servicios.  
* Makefile: dev/dev-clean/test/lint.  
  **Comandos:** make dev → curl localhost:8000/api/v1/health OK.  
  **Gate:** Todos healthchecks green (120s timeout).  
  **Bloqueo:** Servicio no levanta → logs \+ fix Dockerfile.  
  **Duración:** 8h.

**FASE 0 Gate Global:** make test-smoke pasa 100%. → Avanzar F1 o post-mortem.

## **FASE 1: Gobernanza CI/CD**

**1A: Branch Protection \+ CODEOWNERS**  
**Entregables:**

* .github/CODEOWNERS: tech-lead aprueba infra, 1 para features.  
* Branch rules GitHub: main/develop protegidos, require CI green \+ status checks.  
  **Evidencia:** Screenshot rules \+ test merge fail sin approvals.  
  **Gate:** PR simulado bloqueado sin 2 approvers infra.  
  **Bloqueo:** Rules no aplican → reconfig.  
  **Duración:** 2h.

**1B: Pipeline CI Básico**  
**Entregables:**

* .github/workflows/ci.yml: checkout/setup-node/python → lint(typecheck)/gitleaks/npm-audit/smoke.  
  **Comandos:** Push → CI green \<5min.  
  **Gate:** Lint+smoke 100% en main.  
  **Bloqueo:** Step falla → fix \+ retry.  
  **Duración:** 4h.

**1C: Secrets \+ Gitleaks**  
**Entregables:**

* .pre-commit-config.yaml \+ gitleaks.toml.  
* .env.example placeholders, rotar JWT/Stripe/DeepInfra (nuevas keys).  
  **Evidencia:** pre-commit run \--all-files clean, gitleaks detect=0.  
  **Gate:** CI secret-scan pasa, BYPASS\_AUTH=false enforced.  
  **Bloqueo:** Secret detectado → rotar \+ git filter-repo.  
  **Duración:** 4h.

**FASE 1 Gate:** Merge PR test → CI full green \+ deploy preview. → F2.

## **FASE 2: Base de Datos**

**2A: Schema Normalizado \+ Alembic**  
**Entregables:**

* backend/app/db/base.py: Mixins (UUID/Timestamp/SoftDelete/Tenant).  
* Models: organizations/users/memberships/waste\_movements/plans/subscriptions/audit\_logs.  
* alembic/env.py \+ versions/001\_initial.py (expand/contract).  
  **Evidencia:** alembic upgrade head → schema OK, psql \-c "\\dt".  
  **Gate:** Queries tenant-isolated pasan (test isolation).  
  **Duración:** 12h.

**2B: Migraciones Iniciales \+ Seed**  
**Entregables:**

* scripts/seed\_dev.py: 2 orgs/5 users/10 movements sample.  
* init.sql docker-entrypoint.  
  **Comandos:** make db-migrate db-seed → 10 rows waste\_movements.  
  **Gate:** Seed idempotente, no dupes.  
  **Duración:** 6h.

**2C: Tests DB Isolation**  
**Entregables:**

* tests/integration/test\_tenant\_isolation.py: OrgA no ve OrgB data.  
  **Evidencia:** pytest \-v → 100% pass.  
  **Gate:** Cobertura DB \>70%, isolation matrix green.  
  **Duración:** 8h.

**FASE 2 Gate:** Full DB CRUD E2E smoke OK. → F3.

*(Continúa patrón para Fases 3-10 con detalle similar: Entregables precisos, comandos evidencia, gates binarios, duración estimada, bloqueo explícito).*

## **FASE 10: Observabilidad \+ Deploy**

**10A: Logging/Metrics/Prometheus**  
**Entregables:** Correlation ID middleware, structured JSON logs, prometheus.yml \+ Grafana dashboards (API latencia/error).  
**Gate:** Logs con request\_id, Grafana up localhost:3001.

**10B: Blue/Green \+ Rollback**  
**Entregables:** docker-compose.prod.yml (nginx ALB), scripts/deploy.sh/rollback.sh.  
**Gate:** make deploy-staging → traffic switch \<1min.

**10C: Preview PR \+ Chaos**  
**Entregables:** GitHub preview envs/PR, chaos drills (kill Redis/DB).  
**Gate:** Preview PR auto-up, chaos recovery \<5min.

**FASE 10 Gate Global (MVP Done):**

* CI/CD prod green.  
* Flujo E2E smoke 100% (login-waste-upload-approve-bridge-export).  
* SLOs hit (uptime 99.5%, p95\<500ms).  
* Chaos drill passed (3 escenarios).  
* Post-mortem fase 0-10 sin bloqueos mayores.

**Producción Lista:** Deploy v1.0-MVP.

## **Plantilla Auditoría por Subfase (Usar en cada entrega Minimax)**

| SUBFASE: \[ej: 0A\] ESTADO: ⬜ Pendiente | 🟢 Completada | 🔴 Bloqueada ENTREGABLES VERIFICADOS: \- \[ \] Archivo1 (hash/content) \- \[ \] Archivo2 (test pasa) \- \[ \] Comando1: output OK GATE RESULTADO: \- \[ \] CI green (link) \- \[ \] Manual check (screenshot/logs) \- \[ \] Regresión histórica OK EVIDENCIA: \- Commits: hash1..hash2 \- PR: \#XX approved OBSERVACIONES: Próxima: \[subfase siguiente\]  |
| :---- |

