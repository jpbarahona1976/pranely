# ADR-0003: Alcance IA MVP - Decisión Radar vs Console

**Fecha:** 28 Abril 2026  
**Estado:** Aceptado  
**Decisor:** Principal Architect + Staff Engineer + DevSecOps Lead  
**Versión ADR base:** ADR-0002-STACK-ARQUITECTONICO-MVP.md  
**Relación:** Fase 7C del roadmap PRANELY

---

## 1. Resumen Ejecutivo

**Decisión Central:** 

Se define el alcance de funcionalidades IA para el MVP de PRANELY:

| Feature | Decisión | Justificación |
|---------|----------|---------------|
| OCR Extraction | ✅ MANTENER MVP | Core differentiator, ROI claro |
| AI Console (Playground) | ❌ RECORTAR | Costo sin ROI directo, no esencial |
| Legal Radar (DOF/SEMARNAT) | ⏳ POST-MVP | Complejidad alta, diferible |

**Resultado:** MVP = OCR + validaciones NOM-052. Legal Radar como feature P2.

---

## 2. Análisis Costo/ROI (Cuantitativo)

### 2.1 Estructura de Planes y Márgenes

| Plan | Docs/Mes | Precio | Costo IA Est. | Margen Bruto |
|------|----------|--------|---------------|--------------|
| **Free** | 100 | $0 | $0.55 | N/A |
| **Pro** | 2,500 | $299 | $13.75 | **$285.25 (95.4%)** |
| **Enterprise** | 10,000 | $999 | $55.00 | **$944.00 (94.5%)** |

### 2.2 Cálculo Costo por Documento

**Componentes de procesamiento por documento:**

```
1 documento = 
  ├── OCR (Qwen2.5-VL):     ~$0.005/imagen
  ├── LLM Validación:        ~500 tokens input + 200 tokens output
  │                          ($0.00027/K × 0.5 + $0.00054/K × 0.2) = $0.00023
  └── Total por doc:         ~$0.0055
```

### 2.3 Costo IA por Plan

| Plan | Docs/Mes | Costo IA/Mes | % del MRR |
|------|----------|--------------|-----------|
| Free | 100 | $0.55 | N/A (gratuito) |
| Pro | 2,500 | $13.75 | **4.6%** |
| Enterprise | 10,000 | $55.00 | **5.5%** |

### 2.4 ROI Analysis

**Hipótesis de conversión (primeros 6 meses):**
- Free → Pro: 10% (10 orgs gratis → 1 paga)
- Pro retention: 80%

| Mes | Org Free | Org Pro | MRR Real | Costo IA | Margen |
|-----|----------|---------|----------|----------|--------|
| 1 | 10 | 1 | $299 | $14.35 | $285 |
| 3 | 50 | 5 | $1,495 | $71.75 | $1,423 |
| 6 | 100 | 15 | $4,485 | $215.25 | $4,270 |

**Conclusión:** El costo de IA es <6% del MRR. ROI positivo desde el mes 1.

---

## 3. Análisis Features

### 3.1 AI Console (Playground/Test Prompts)

**Descripción:** Interfaz para que usuarios prueben prompts de IA sin procesar documentos reales.

| Aspecto | Análisis |
|---------|----------|
| **Costo** | +500-2000 tokens/uso × usuarios activos |
| **Complejidad** | Media (nueva UI + endpoints) |
| **ROI** | Bajo - no genera diferenciación directa |
| **Riesgo** | Sobrecosto por uso no productivo |
| **Decisión** | ❌ **RECORTAR para MVP** |

**Justificación:**
- No impacta el workflow core de extracción
-Users no técnicos no usan playgrounds
- Costo oculto difícil de predecir
- Feature standard en SaaS, no diferenciador

### 3.2 Legal Radar (Scraper DOF/SEMARNAT)

**Descripción:** Scraping automático del DOF y portales SEMARNAT para alertar sobre cambios regulatorios.

| Aspecto | Análisis |
|---------|----------|
| **Costo** | $50-200/mes (scrapers + хранилище) |
| **Complejidad** | Alta (anti-scraping, parsing PDF, mantenibilidad) |
| **ROI** | Alto - diferenciador fuerte para Directors Compliance |
| **Riesgo** | Legal (términos de servicio), mantenimiento constante |
| **Decisión** | ⏳ **POST-MVP (P2)** |

**Justificación:**
- Feature con alto valor diferenciador
- Complejidad técnica > capacidad MVP actual
- Requiere validación legal de scraping
- Mejor postpone hasta tener base de clientes sólida

### 3.3 OCR Extraction (Core)

**Descripción:** Extracción automática de campos de manifiestos de residuos usando DeepInfra + Qwen.

| Aspecto | Análisis |
|---------|----------|
| **Costo** | $0.005/doc (ya calculado) |
| **Complejidad** | Media (pipeline RQ + schemas + validation) |
| **ROI** | Muy Alto - justificación de precio principal |
| **Riesgo** | Bajo - tecnología probada |
| **Decisión** | ✅ **MANTENER en MVP** |

---

## 4. Decisión Final

### 4.1 Feature Set MVP

```
MVP IA (Subfases 7A-7F):
├── 7A: Workers RQ ✅ (retry/DLQ/observabilidad)
├── 7B: Contratos DeepInfra ✅ (schemas/cliente/rate limit)
├── 7C: Este ADR (alcance definido)
├── 7D: [RESERVADO] Optimización costos
├── 7E: [RESERVADO] Validación NOM-052 con IA
└── 7F: [RESERVADO] Reporting/analytics IA
```

### 4.2 Roadmap IA Post-MVP

| Feature | Prioridad | Estimado | Dependencias |
|---------|-----------|----------|--------------|
| Legal Radar | P2 | Q2 2026 | Base clientes 50+, validación legal |
| AI Console | P3 | Q3 2026 | Feedback usuarios, casos de uso |
| Fine-tuning custom | P3 | Q4 2026 | Volumen datos suficiente |

---

## 5. Supuestos y Riesgos

### 5.1 Supuestos

1. **Precios DeepInfra estables:** Cálculos basados en pricing actual (Abril 2026)
2. **Tasa conversión Free→Pro 10%:** Hipótesis conservadora basada en SaaS B2B típico
3. **2,500 docs/mes para Pro:** Suficiente para mayoría de plantas industriales
4. **Costo OCR $0.005:** Basado en imágenes 1MB promedio, modelo Qwen2.5-VL

### 5.2 Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Aumento precios IA | Media | Medio | Reservar 20% margen adicional |
| Uso excesivo Free | Baja | Alto | Rate limiting + monitoring |
| Modelos no disponibles | Baja | Alto | Multi-provider fallback (OpenAI backup) |
| Regulatory changes | Baja | Medio | Legal Radar Post-MVP reduce exposición |

---

## 6. Criterios de Terminación

- [x] Decisión ROI explícita documentada
- [x] Análisis costo/tokens por documento realizado
- [x] ADR-0003 escrito y aprobado
- [x] Feature set MVP alineado con P0-P3
- [x] 0 ambigüedad en próximo paso
- [x] Roadmap Post-MVP definido

---

## 7. Próxima Subfase Recomendada

**7D: Optimización de Costos IA** (reservado)

**Objetivo:** Implementar controles para asegurar margen >90% en planes Pro/Enterprise

**Entregables:**
- [ ] Budget alerts (80%/90%/100% de umbral)
- [ ] Usage tracking por org
- [ ] Quota enforcement en API
- [ ] Cost dashboard

**Alternativa:** Si 7D no es prioritaria, proceed a **8A: Mobile Bridge** para expandir mercado.
