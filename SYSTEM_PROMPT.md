---
name: pranely-system
version: 1.0.0
type: system-prompt
---

# 🤖 Pranely Operating System - SYSTEM PROMPT

## 📋 Instrucciones de Inicio para Cada Chat

### Paso 1: Leer Contexto del Proyecto
Al iniciar una nueva sesión, SIEMPRE lee estos archivos en orden:

1. **PROJECT_STATE.md** → Estado actual y progreso del proyecto
2. **PROTOCOLO DE RECONSTRUCCIÓN Y ROADMAP/Skill Persistente_ Pranely Operating System (para Minimax M2.md** → Directrices operativas
3. **README.md** → Estructura del proyecto

### Paso 2: Cargar Skills Relevantes
Todas las skills están en `.agents/skills/`. Carga las skills según la consulta:

**Skills de Desarrollo:**
- `fastapi-patterns/` → APIs FastAPI
- `fastapi-pro/` → FastAPI avanzado
- `nodejs-backend-patterns/` → Backend Node.js
- `code-review-security/` → Seguridad
- `systematic-debugging/` → Debugging

**Skills de Frontend:**
- `next-best-practices/` → Next.js
- `frontend-design/` → Diseño
- `shadcn/` → Componentes UI

**Skills de Testing:**
- `playwright-best-practices/` → Testing E2E

**Skills de Base de Datos:**
- `alembic/` → Migraciones
- `postgresql-database-engineering/` → PostgreSQL
- `monitoring-observability/` → Monitoreo

**Skills de Proceso:**
- `prd-development/` → Documentación PRD
- `deployment-pipeline/` → CI/CD
- `api-designer/` → Diseño de APIs
- `openapi-spec-generation/` → OpenAPI

**Skills de Equipo:**
- `sw-team-build/` → Construcción de equipos
- `sw-multi-project/` → Multi-proyecto
- `sw-github-issue-standard/` → Issues
- `sw-analytics/` → Analytics
- `observability-engineer/` → Observabilidad
- `monitoring-observability/` → Monitoreo completo

**Skills Utilitarias:**
- `find-skills/` → Buscador de skills
- `create-auth-skill/` → Autenticación
- `close-all/` → Comandos de cierre

### Paso 3: Actualizar Estado
Después de cada sesión significativa, actualiza **PROJECT_STATE.md** con:
- Progreso realizado
- Decisiones tomadas
- Próximos pasos
- Bloqueos o problemas

### Paso 4: Mantener Consistencia
- Seguir las directrices del protocolo
- Documentar cambios importantes
- Mantener el PROJECT_STATE.md actualizado

---

## 📁 Estructura del Proyecto

```
Pranely/
├── .agents/skills/          # 24 skills del sistema
├── PROTOCOLO DE RECONSTRUCCIÓN Y ROADMAP/  # Protocolo operativo
├── PROJECT_STATE.md         # Estado del proyecto (ACTUALIZAR)
├── README.md                # Documentación
├── code-review-security/    # Skill: Seguridad
├── deployment-pipeline/     # Skill: CI/CD
├── playwright-best-practices/ # Skill: Testing
├── next-best-practices/    # Skill: Next.js
├── shadcn/                  # Skill: UI
├── systematic-debugging/    # Skill: Debugging
└── [otras skills en .agents/skills/]
```

---

## 🎯 Reglas de Operación

1. **NUNCA perder contexto** → Leer PROJECT_STATE.md al inicio
2. **MANTENER actualizado** → Documentar progreso en cada sesión
3. **USAR skills relevantes** → Cargar antes de responder
4. **SEGUIR protocolo** → Leer directrices antes de actuar
5. **DOCUMENTAR decisiones** → Registrar en PROJECT_STATE.md

---

## 📊 URLs de Repositorios

- **Proyecto:** https://github.com/jpbarahona1976/Pranely
- **Skills:** https://github.com/jpbarahona1976/opencode-skills
- **Protocolo:** https://github.com/jpbarahona1976/PROTOCOLO-DE-RECONSTRUCCION-Y-ROADMAP

---

## 🔄 Flujo de Trabajo

```
[Nuevo Chat] → [Leer PROJECT_STATE.md] → [Leer Protocolo] 
    → [Cargar Skills Relevantes] → [Procesar Consulta] 
    → [Actualizar Estado] → [Documentar Cambios]
```

---

*Prompt de sistema creado: 2026-04-20*
*Versión: 1.0.0*
