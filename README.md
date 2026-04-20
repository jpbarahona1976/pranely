# Pranely - Sistema Operativo de Desarrollo con IA

> **🤖 Proyecto de desarrollo asistido por IA usando Minimax M2.5/M2.7**

---

## 📚 Documentación Principal

### 🔑 Archivos Críticos (Leer al iniciar cada chat)

| Archivo | Descripción | Ubicación |
|---------|-------------|-----------|
| `PROJECT_STATE.md` | Estado actual del proyecto y progreso | `./PROJECT_STATE.md` |
| `PROTOCOLO DE RECONSTRUCCIÓN.../Skill Persistente...md` | Directrices de operación | `./PROTOCOLO DE RECONSTRUCCIÓN Y ROADMAP"/` |
| `skills-lock.json` | Versiones de skills | `./skills-lock.json` |

---

## 🛠️ Estructura del Proyecto

```
Pranely/
├── 📁 .agents/skills/          # Skills del sistema (24 skills)
├── 📁 code-review-security/    # Revisión de código y seguridad
├── 📁 create-auth-skill/       # Sistema de autenticación
├── 📁 deployment-pipeline/     # Pipeline CI/CD
├── 📁 fastapi-patterns/        # Patrones FastAPI
├── 📁 fastapi-pro/            # FastAPI profesional
├── 📁 find-skills/            # Buscador de skills
├── 📁 frontend-design/         # Diseño frontend
├── 📁 monitoring-observability/ # Monitoreo y observabilidad
├── 📁 next-best-practices/    # Next.js
├── 📁 nodejs-backend-patterns/ # Node.js
├── 📁 playwright-best-practices/ # Playwright E2E
├── 📁 postgresql-database-engineering/ # PostgreSQL
├── 📁 prd-development/        # Desarrollo de PRD
├── 📁 shadcn/                  # shadcn/ui
├── 📁 systematic-debugging/    # Debugging
├── 📁 PROTOCOLO DE RECONSTRUCCIÓN Y ROADMAP/ # Protocolo principal
├── 📄 PROJECT_STATE.md         # Estado del proyecto
├── 📄 README.md                # Este archivo
└── 📄 skills-lock.json        # Lock de versiones
```

---

## 📦 Repositorios en GitHub

| Repositorio | Descripción | URL |
|-------------|-------------|-----|
| `Pranely` | Proyecto principal | https://github.com/jpbarahona1976/Pranely |
| `opencode-skills` | Skills del sistema | https://github.com/jpbarahona1976/opencode-skills |
| `PROTOCOLO-DE-RECONSTRUCCION-Y-ROADMAP` | Protocolo operativo | https://github.com/jpbarahona1976/PROTOCOLO-DE-RECONSTRUCCION-Y-ROADMAP |

---

## 🚀 Extensiones de VS Code

### Minimax Chat (M2.7) - Principal
- **Uso:** Chats de desarrollo normales
- **Prioridad:** ALTA

### OpenCode (M2.5)
- **Uso:** Auditorías y reportes
- **Prioridad:** SECUNDARIA

---

## 📋 Cómo Usar

### Iniciar Nuevo Chat
1. Leer `PROJECT_STATE.md` para contexto
2. Leer protocolo en `PROTOCOLO DE RECONSTRUCCIÓN...`
3. Minimax cargará automáticamente las skills relevantes

### Agregar Nueva Skill
1. Crear skill en `.agents/skills/NOMBRE_SKILL/`
2. Incluir `SKILL.md` con frontmatter
3. Agregar a `skills-lock.json`
4. Subir a GitHub: `opencode-skills`

---

## 🔧 Configuración

### Tokens de Acceso
- Usar tokens de GitHub con permisos de `repo`
- Almacenar de forma segura (NO commitear)

### Actualización de Skills
```bash
git clone https://github.com/jpbarahona1976/opencode-skills.git
# Copiar skills a .agents/skills/
```

---

## 📊 Estado del Proyecto

**Última actualización:** 2026-04-20
**Total de skills:** 24
**Fase actual:** Configuración de IA

Ver `PROJECT_STATE.md` para detalles completos.

---

*💡 Minimax leerá automáticamente los archivos de protocolo y estado al iniciar cada sesión.*
