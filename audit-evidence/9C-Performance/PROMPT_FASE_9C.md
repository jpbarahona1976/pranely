# PROMPT FASE 9C - Minimax M2.7 (Implementador)

```
================================================================================
PRANELY - FASE 9C PERFORMANCE
FECHA: 30 Abril 2026
================================================================================

1. ROL
Actúa como Principal Software Architect + Staff Full-Stack Engineer + 
Performance Engineer de PRANELY.

2. OBJETIVO
Implementar Fase 9C Performance: identificar y optimizar cuellos de botella 
para cumplir SLOs p95<500ms antes de Fase 10 Lanzamiento.

3. CONTEXTO
- Fases 0A-9B cerradas (observabilidad activa).
- Stack: Next.js15/FastAPI3.12/PG16/Redis7/RQ/Docker.
- CI 100% verde, gitleaks 0.
- SLOs objetivo: p95 API <500ms, uptime 99.5%.
- Qwen mock (activar staging).

4. ALCANCE - SOLO ESTO:
- Identificar endpoints >500ms (GET /api/v1/waste/stats)
- Optimizar DB: índices org_id, N+1 queries waste/stats
- Redis cache: sessions + waste stats (5min TTL)
- Load test k6: 100 usuarios simultáneos
- Verificar SLOs post-optimización
- Docs PERFORMANCE.md con benchmarks antes/después

5. NO ALCANCE
- No Fase 10
- No features nuevas
- No cambiar stack
- No Qwen real (mock OK)

6. REGLAS EJECUCIÓN
- Usa Prometheus para profiling
- Cambios medibles (benchmarks)
- Tests no rompen CI
- Prioriza: DB → Cache → Frontend

7. FORMATO SALIDA
Resumen ejecutivo
Endpoints lentos identificados
Optimizaciones aplicadas
Benchmarks antes/después
Redis cache implementado
Load test k6 resultados
Docs PERFORMANCE.md
Criterios terminado

8. CRITERIOS TERMINADO
✅ p95 global <500ms
✅ Waste endpoints optimizados
✅ Redis cache activo (hit rate >70%)
✅ Load test 100 users OK
✅ CI intacto
✅ Docs benchmarks
✅ Listo para auditoría 9C

================================================================================
SKILLS CARGADAS
================================================================================
- monitoring-observability
- observability-engineer
- deployment-pipeline
- fastapi-patterns
- fastapi-pro
- next-best-practices
- systematic-debugging
- alembic
- playwright-best-practices

================================================================================
COMANDOS ÚTILES
================================================================================
# Verificar sintaxis
python -m py_compile app/services/cache.py

# Tests de cache
python -m pytest tests/test_cache_service.py -v

# Tests de waste API
python -m pytest tests/test_waste_api.py -v

# Verificar migración
alembic upgrade head --dry-run

# Run load test (requiere k6 instalado)
k6 run observability/load_test/load_test.js --env BASE_URL=http://localhost:8000

================================================================================
ENTREGABLES 9C
================================================================================

1. MIGRATION: alembic/versions/005_performance_indexes.py
   - ix_waste_movement_org_status_archived
   - ix_waste_movement_org_created_at
   - ix_membership_user_org
   - ix_audit_log_org

2. OPTIMIZACIÓN: app/api/v1/waste.py
   - get_waste_stats: 7 queries → 3 queries + cache
   - Cache invalidation en create/update/archive

3. CACHE SERVICE: app/services/cache.py
   - CacheService class
   - TTL_WASTE_STATS = 300
   - TTL_SESSION = 1800
   - get_waste_stats, set_waste_stats, invalidate_waste_stats

4. LOAD TEST: observability/load_test/load_test.js
   - 100 concurrent users
   - p95 < 500ms threshold
   - waste_list, waste_stats, waste_create scenarios

5. TESTS: tests/test_cache_service.py
   - 18 tests covering cache operations

6. DOCS: audit-evidence/9C-Performance/
   - BASELINE.md
   - PERFORMANCE.md
   - AUDIT_REPORT_9C.md

================================================================================
```

## Instrucciones de Uso

1. **Copiar este prompt** a un archivo para referencia
2. **Ejecutar cada entregable** en orden
3. **Verificar tests** después de cada cambio
4. **Documentar benchmarks** antes/después
5. **Generar AUDIT_REPORT_9C.md** al final

## Notas para el Auditor

- Los tests de rate limit (429) son comportamiento esperado del middleware 8C.2
- La optimización real se mide con load test k6 en staging
- Todos los archivos están verificados con `py_compile`
- La migración está lista para `alembic upgrade head`