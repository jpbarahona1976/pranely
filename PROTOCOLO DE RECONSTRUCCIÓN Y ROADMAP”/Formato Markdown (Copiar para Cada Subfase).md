## **Formato Markdown (Copiar para Cada Subfase)**

| \# AUDITORÍA SUBFASE \[XX\] \- Pranely.ai \*\*Subfase:\*\* \[ej: 0A Limpieza \+ Repo Base\]   \*\*Fecha Inicio:\*\* YYYY-MM-DD HH:MM   \*\*Duración Real:\*\* Xh   \*\*Responsable:\*\* Minimax M2.7 / \[Tu nombre\]   \*\*Repo/PR:\*\* \[link GitHub\]   \*\*Branch:\*\* \[nombre\]   \#\# 🟢 ESTADO FINAL \- \[ \] \*\*🟢 COMPLETADA\*\* → Todos gates green, lista merge Fase Gate.   \- \[ \] \*\*🔴 BLOQUEADA\*\* → Gate fallido \[detalle\], requiere fix.   \#\# 1\. ENTREGABLES VERIFICADOS (Checklist Obligatorio) | \# | Entregable | Verificado | Evidencia/Hash | |---|-------------|------------|----------------| | 1 | \[ej: Repo nuevo limpio \<100 commits\] | \[ \] | \`git log \--oneline \\| wc \-l\` → 42 | | 2 | \[ej: .gitignore \+ .env.example\] | \[ \] | diff \--git .gitignore → OK | | 3 | \[ej: Estructura monorepo apps/web/api\] | \[ \] | \`tree \-L 2\` → matches spec | | 4 | \[Comando1: make pre-flight\] | \[ \] | Output: ✅ Todas versiones OK | | 5 | \[Archivo crítico hash\] | \[ \] | \`sha256sum backend/db/base.py\` → abc123... | \*\*% Completado:\*\* XX/XX (debe 100% para 🟢). \#\# 2\. GATES DE SALIDA (Binarios \- Fallo \= 🔴) | Gate | Criterio | Resultado | Evidencia | |------|----------|-----------|-----------| | \*\*G1: Sintaxis/Lint\*\* | \`make lint\` 0 errors | \[ \] PASS | Log: 0 issues | | \*\*G2: Typecheck\*\* | \`make typecheck\` 0 errors | \[ \] PASS | Log: All OK | | \*\*G3: Unit/Integration\*\* | pytest/Vitest \>80% cover | \[ \] PASS | \`pytest \--cov\` → 85% | | \*\*G4: Smoke/Health\*\* | Todos servicios healthy 120s | \[ \] PASS | \`curl /health\` → {"status":"healthy"} | | \*\*G5: Security\*\* | gitleaks=0, no BYPASS\_AUTH | \[ \] PASS | \`gitleaks detect\` → clean | | \*\*G6: Manual/Funcional\*\* | \[ej: docker up levanta scaffold\] | \[ \] PASS | Screenshot/logs | | \*\*G7: Regresión Histórica\*\* | Tests bugs previos pass | \[ \] PASS | \`make test-regression\` → 100% | \*\*Gates Globales Fase:\*\* \[ej: F0: make test-smoke 100%\] → \[ \] PASS/FAIL. \#\# 3\. EVIDENCIA TÉCNICA (Logs/Outputs)  |
| :---- |

\[Copiar outputs clave aquí\]  
ej: $ make dev  
✅ Node v22.13.1 OK  
✅ Backend health: {"database":"ok","redis":"ok"}  
ej: $ git status  
clean

|  \*\*Commits Nuevos:\*\* \[hash1..hash2\] \- \[N commits, messages clave\]. \#\# 4\. RIESGOS IDENTIFICADOS | Riesgo | Prob | Impacto | Mitigación | |--------|------|---------|------------| | \[ej: Versión Node drift\] | Baja | Alto | Pin .nvmrc \+ pre-flight | \#\# 5\. OBSERVACIONES / POST-MORTEM \- Bloqueos encontrados: \[ninguno / detalle \+ fix\]. \- Supuestos: \[lista explícita\]. \- Deuda técnica: \[TODOs pendientes con ticket\]. \#\# 6\. AUTORIZACIÓN AVANCE \*\*Gate Fase Global:\*\* \[ \] 🟢 PASS → Autorizado \[Siguiente Subfase XX\].   \*\*Firma Auditor:\*\* \[Tu nombre\] \- YYYY-MM-DD HH:MM   \*\*Merge OK:\*\* \[ \] Sí (PR \#XX) / No (motivo). \--- \*\*🟡 ESTADO INTERMEDIO PROHIBIDO.\*\* Si \<100% entregables o gate rojo → \*\*🔴 BLOQUEADA\*\*. Fix → re-auditoría.  |
| :---- |

## **Instrucciones Uso (Para Minimax/Tú)**

1. **Minimax genera subfase → llena plantilla al final respuesta.**  
2. **Tú verificas/ejecutas comandos → marcas checks.**  
3. **Si todos 🟢 → merge PR \+ próxima subfase.**  
4. **Si 🔴 → post-mortem corto \+ fix en nueva branch.**  
5. **Archivo por subfase:** audits/\[FASE\]-\[SUBFASE\].md → commit repo.

## **Ejemplo Lleno (0A)**

| \# AUDITORÍA SUBFASE 0A \- Pranely.ai \*\*Subfase:\*\* 0A Limpieza \+ Repo Base   \*\*Fecha Inicio:\*\* 2026-04-19 15:00   \*\*Duración Real:\*\* 3.5h   \#\# 🟢 ESTADO FINAL \- \[x\] \*\*🟢 COMPLETADA\*\*   \#\# 1\. ENTREGABLES VERIFICADOS | \# | Entregable | Verificado | Evidencia | |---|------------|------------|-----------| | 1 | Repo nuevo | x | 28 commits | | ... | ... | x | ... | \#\# 2\. GATES DE SALIDA | Gate | Resultado | Evidencia | |------|-----------|-----------| | G1 | x PASS | 0 lint | | ... | ... | ... | \*\*Próxima:\*\* 0B. \*\*Firma:\*\* Juan Barahona \- 2026-04-19 18:30  |
| :---- |

