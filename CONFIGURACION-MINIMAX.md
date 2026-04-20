# 🔧 Guía de Configuración - Minimax Chat

## 📋 Pasos para Configurar Minimax Chat

### Opción 1: Configuración Automática (Recomendado)

1. **Abre VS Code** en la carpeta `Pranely`

2. **Presiona `Ctrl+Shift+P`** y busca:
   ```
   Preferences: Open Workspace Settings (JSON)
   ```

3. **Copia y pega** el contenido de `.vscode/settings.json` en el archivo

4. **Reinicia VS Code**

---

### Opción 2: Configuración Manual de Minimax Chat

#### Paso 1: Abrir Configuración de Minimax Chat

1. Presiona `Ctrl+Shift+P`
2. Escribe: `Minimax Chat: Open Settings`
3. O busca en extensiones: **Minimax Chat** → ⚙️ (Settings)

#### Paso 2: Configurar Skills Folder

En la configuración de Minimax Chat, busca:

| Setting | Valor |
|---------|-------|
| `Skills Folder` | `.agents/skills` |
| `Auto Load Skills` | ✅ `true` |
| `Context Files` | Ver abajo |

**Context Files (archivos a leer al iniciar):**
```
PROJECT_STATE.md
README.md
SYSTEM_PROMPT.md
PROTOCOLO DE RECONSTRUCCIÓN Y ROADMAP/Skill Persistente_ Pranely Operating System (para Minimax M2.md
```

#### Paso 3: Agregar Custom Instructions (Opcional pero Recomendado)

1. En Minimax Chat Settings → busca **Custom Instructions** o **System Prompt**
2. Copia el contenido de `SYSTEM_PROMPT.md` (en la raíz del proyecto)
3. Pégalo en el campo de Custom Instructions

---

### Opción 3: Al Iniciar Cada Chat (Menos Automático)

Si no puedes configurar automáticamente, al iniciar cada chat nuevo escribe:

```
# PRANELY - Inicialización

Antes de responder, lee y aplica:
1. PROJECT_STATE.md → Estado del proyecto
2. PROTOCOLO DE RECONSTRUCCIÓN Y ROADMAP/Skill Persistente_ Pranely Operating System (para Minimax M2.md → Directrices
3. SYSTEM_PROMPT.md → Instrucciones del sistema

Skills disponibles en .agents/skills/ → 24 skills

Entendido? Confirma para continuar.
```

---

## 🔍 Cómo Verificar que Funciona

### Test 1: Nuevo Chat
1. Cierra todos los chats de Minimax Chat
2. Abre un **nuevo chat**
3. Escribe: `¿Cuántas skills hay disponibles?`
4. Debe responder con la lista de 24 skills

### Test 2: Contexto del Proyecto
1. Inicia nuevo chat
2. Escribe: `¿En qué fase está el proyecto?`
3. Debe leer `PROJECT_STATE.md` y responder correctamente

### Test 3: Skills Específicas
1. Inicia nuevo chat
2. Escribe: `¿Cómo creo una migración con alembic?`
3. Debe cargar la skill de alembic y responder

---

## ⚙️ Configuración para OpenCode (Auditorías)

Si también quieres configurar **OpenCode** (M2.5):

1. Presiona `Ctrl+Shift+P`
2. Escribe: `OpenCode: Open Settings`
3. Configura igual que Minimax Chat:
   - Skills Folder: `.agents/skills`
   - Auto Load Skills: `true`

---

## 📝 Resumen de Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `PROJECT_STATE.md` | Estado actual del proyecto |
| `README.md` | Documentación general |
| `SYSTEM_PROMPT.md` | Instrucciones para Minimax |
| `.agents/skills/` | 24 skills del sistema |
| `.vscode/settings.json` | Configuración del proyecto |
| `PROTOCOLO DE RECONSTRUCCIÓN...` | Directrices operativas |

---

## 🚨 Solución de Problemas

### Minimax no carga las skills
1. Verifica que `.agents/skills/` existe en el proyecto
2. Verifica que el path en settings es correcto
3. Reinicia VS Code

### No lee los archivos de contexto
1. Verifica que los archivos existen en la raíz
2. Verifica los nombres exactos (incluyendo tildes y caracteres especiales)

### Error de autenticación
1. Verifica que el token de GitHub está configurado
2. En Minimax Chat → Settings → GitHub Token

---

## 📞 Necesitas Ayuda?

Si la configuración no funciona, comparte:
1. Captura de pantalla de la configuración de Minimax Chat
2. El error que aparece (si hay alguno)
3. Qué versión de Minimax Chat tienes instalada

---

*Creado: 2026-04-20*
*Versión: 1.0.0*
