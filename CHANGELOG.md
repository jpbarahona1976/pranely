# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

### Próximas tareas

- [ ] 9A: Notificaciones push

### Completado

- [x] 8A: Mobile Bridge ✅ **2026-04-28**
- [x] 6B: Dashboard KPIs + tabla + polling (Glassmorphism) ✅ **AUDITORÍA CERRADA 2026-05-03**
- [x] Fix: Docstrings Python en archivos TSX → comentarios JS ✅ **2026-05-03**
- [x] 6A: Layout/navegación/i18n (estado previo)

---

## [1.20.0] - 2026-04-28 - FASE 8A MOBILE BRIDGE ✅

- 8B: Command Center (dashboard extendido)

> **MOBILE BRIDGE - QR SESSION + WEBSOCKET REALTIME + PWA** ✅
> Puente móvil para sincronización en tiempo real de escaneos QR.

### Backend

#### API Endpoints
- `POST /api/bridge/session` - Crear sesión QR temporal (5 min)
- `GET /api/bridge/session/{qr_token}` - Estado de sesión
- `POST /api/bridge/session/{qr_token}/extend` - Extender sesión
- `DELETE /api/bridge/session/{qr_token}` - Cerrar sesión
- `WS /ws/bridge/{session_id}` - WebSocket realtime

#### Características
- Token JWT temporal limitado para bridge (5 min expiry)
- Auth JWT con claims mínimos (sub, org_id, session_id, type=bridge)
- Tenant isolation por organization_id
- RBAC: owner/admin/member pueden crear, viewer no
- Cleanup periódico de sesiones expiradas
- Logging correlacionado con session_id
- Manejo explícito de errores y cierre limpio

### Frontend

#### Páginas
- `app/bridge/page.tsx` - Mobile-first (375px) bridge interface

#### Componentes
| Componente | Descripción |
|-----------|-------------|
| `QRScanner.tsx` | Escáner con getUserMedia + jsqr |
| `BridgeStatus.tsx` | StatusBadge + StatusBar glassmorphism |
| `lib/bridge-api.ts` | API client + WS client con reconnect |

#### Características
- QR Scanner live con cámara del dispositivo
- Cliente WebSocket con reconnect backoff exponencial
- Estados visuales: conectado, syncing, offline, expirado, error
- Bottom glass bar: Scan / Manual / Sync
- Offline queue con localStorage
- Responsive: mobile (375px) → tablet (768px) → desktop (1280px)
- Estilo Glassmorphism exacto: bg-white/5, backdrop-blur-md

### PWA

#### Archivos
- `public/manifest.json` - PWA manifest para bridge
- `public/sw-bridge.js` - Service worker básico

#### Funcionalidades
- Cache de assets estáticos
- Offline shell para /bridge
- Background sync para cola offline
- Push notifications (preparado)

### Tests

- `tests/test_bridge.py` - Unit + integration tests
- `e2e/bridge.spec.ts` - E2E playwright tests

### Criterios Terminados 8A

- [x] POST /api/bridge/session con auth + tenant isolation
- [x] WS /ws/bridge/{session_id} con validación + reconnect
- [x] /bridge existe con Glassmorphism
- [x] QR scanner live con jsqr
- [x] Estados visuales bridge
- [x] Offline queue local
- [x] PWA mínimo
- [x] Tests nuevos
- [x] No BYPASS auth
- [x] No hardcoded secrets

---

## [1.19.0] - 2026-05-03 - FASE 6B CERRADA ✅

> **DASHBOARD KPIs + TABLA + POLLING** ✅ **AUDITORÍA APROBADA**
> Dashboard operativo con datos del dominio waste, KPIs dinámicos, tabla completa con acciones visibles en touch, RBAC conectado al token real, polling 30s.

### Auditoría Hallazgos - RESUELTOS

#### H1: Endpoint /review no existe ✅
- **Problema**: Frontend llamaba POST /api/v1/waste/{id}/review pero no existía en backend
- **Solución**: Creado `app/api/v1/waste_review.py` con endpoints:
  - `POST /api/v1/waste/{id}/review` - approve/reject/request_changes
  - `PATCH /api/v1/waste/{id}` - update movement
  - `POST /api/v1/waste/{id}/archive` - soft delete
- **RBAC**: Solo owner/admin pueden aprobar/rechazar

#### H2: Acciones con hover no funcionan en móvil ✅
- **Problema**: `opacity-0 group-hover:opacity-100` ocultaba acciones en touch
- **Solución**: Botones siempre visibles (`opacity-100`), componente `ActionButton` con:
  - `min-width: 40px`, `min-height: 40px`
  - `touch-manipulation` para responsividad táctil
  - `focus:ring-2` para accesibilidad
  - `aria-label` para screen readers

#### H3: Rol hardcodeado "admin" ✅
- **Problema**: `DashboardKPI` usaba `getUserPermissions("admin")` hardcodeado
- **Solución**: `AuthContext` ahora extrae rol del JWT:
  - Intenta `/api/auth/me` primero
  - Fallback a decoding JWT `role` claim
  - `permissions` expuesto en contexto para consumo directo

#### H4: wasteApi sin contexto multi-tenant ✅
- **Problema**: API client no usaba organización real del usuario
- **Solución**: 
  - `AuthContext` extrae `org_id` del JWT
  - `wasteApi` usa Bearer token del localStorage
  -Todas las requests incluyen `Authorization: Bearer <token>`

#### H5: Sidebar con mocks ✅
- **Problema**: `mockActivity` y `mockAlerts` aparentaban datos reales
- **Solución**: 
  - Datos inicializados como arrays vacíos
  - UI controlada: empty state visible
  - **Documentado**: Activity/Alerts fuera de alcance 6B (requiere endpoints backend)

### Added

#### Backend: Waste Review API ✅
**Archivo**: `app/api/v1/waste_review.py`
- `POST /api/v1/waste/{id}/review` - Acciones de revisión
- `PATCH /api/v1/waste/{id}` - Actualización de movimiento
- `POST /api/v1/waste/{id}/archive` - Archivando
- RBAC verificado en cada endpoint
- Logs de auditoría correlacionados

#### Frontend: RBAC desde JWT ✅
**Archivo**: `src/contexts/AuthContext.tsx`
- Extracción de `role` del JWT payload
- Endpoint `/api/auth/me` como fuente preferida
- Helper `getPermissionsFromRole()` para mapeo
- Tipo `UserRole` exportado: owner/admin/member/viewer

#### Frontend: Actions Always Visible ✅
**Archivo**: `src/components/dashboard/MovementsTable.tsx`
- Componente `ActionButton` con área táctil ≥40px
- Clase `touch-manipulation` para dispositivos táctiles
- `aria-label` para accesibilidad
- `focus:ring-2` para feedback visual en focus

#### Frontend: Dashboard Contexto Real ✅
**Archivo**: `src/components/dashboard/DashboardKPI.tsx`
- Usa `permissions` del AuthContext (no hardcodeado)
- Indicador visual de fuente de datos (API/mock)
- Optimistic updates para approve/reject
- Error handling con rollback

#### Tests E2E ✅
**Archivo**: `packages/frontend/e2e/dashboard-6b-audit.spec.ts`
- H1: Validación endpoint review
- H2: Acciones visibles en móvil (375px)
- H3: Rol real del token (no hardcodeado)
- H4: Headers Authorization en requests
- H5: Empty state en sidebar (sin mocks)
- Flujo completo: login → dashboard → logout
- Responsive: 375px, 768px, 1920px

### Components (Glassmorphism)

| Componente | Descripción |
|-----------|-------------|
| `DashboardKPI.tsx` | Orchestrator principal con RBAC real |
| `MovementsTable.tsx` | Tabla con acciones touch-friendly |
| `KpiCard.tsx` | Cards con tendencias |
| `StatusBadge.tsx` | Badges de estado glass |
| `ConfidenceBar.tsx` | Barra de confianza IA |
| `Sidebar.tsx` | Actividad + Alertas (empty state) |
| `FAB.tsx` | Floating Action Button |

### API Client

**Archivo**: `src/lib/waste-api.ts`
- `wasteApi.approve(id)` - Llama POST /api/v1/waste/{id}/review
- `wasteApi.reject(id, reason)` - Llama POST con action=reject
- Token extraído de localStorage automáticamente

### Criterios Terminado 6B

- [x] Dashboard modular sin errores
- [x] Endpoint review existe en backend
- [x] Acciones visibles sin hover (touch ≥40px)
- [x] RBAC conectado al rol real del JWT
- [x] wasteApi usa contexto multi-tenant real
- [x] Sidebar con empty state controlado (no mocks)
- [x] Tests E2E para hallazgos de auditoría
- [x] Responsive 375px-2560px
- [x] Glassmorphism consistente

---

## [1.18.1] - 2026-05-01

> **FASE 6B - IMPLEMENTACIÓN INICIAL**
> Dashboard KPIs + tabla + polling con glassmorphism premium.
> ⚠️ Rechazada en auditoría por hallazgos H1-H5

*[... historial previo ...]*

---

## [1.14.0] - 2026-04-26

> **CIERRE DEFINITIVO FASE 5A - APROBADO LIMPIO** ✅
