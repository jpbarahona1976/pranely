# Subfase 7A: Worker Resilient

## Resumen

**Estado:** Implementado ✅  
**Fecha:** 2026-04-28  
**Stack:** Redis + RQ (Redis Queue)

## Objetivo

Implementar procesamiento asíncrono del pipeline documental IA con resiliencia: retries, backoff, timeouts, manejo de fallos y Dead Letter Queue.

## Arquitectura Implementada

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│  FastAPI    │────>│   Redis     │────>│   RQ Worker     │
│  (enqueue)  │     │  (broker)   │     │  (processing)  │
└─────────────┘     └─────────────┘     └─────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
            ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
            │    HIGH       │        │  AI_PROCESSING│        │    FAILED     │
            │   (critical)  │        │  (document)   │        │   (DLQ)       │
            └───────────────┘        └───────────────┘        └───────────────┘
```

## Jobs Definidos

| Job | Cola | Timeout | Retry | Descripción |
|-----|------|---------|-------|-------------|
| `process_document` | ai_processing | 180s | 3 (30s, 120s, 300s) | OCR/triage documento |
| `validate_waste_movement` | ai_processing | 300s | 3 (10s, 60s, 180s) | Validación NOM-052 |
| `send_notification` | default | 60s | 2 (5s, 30s) | Notificaciones async |
| `cleanup_old_jobs` | low | 600s | 1 (60s) | Cleanup periódico |
| `health_check` | high | 30s | 0 | Health del worker |

## Retries y Backoff

```python
RetryPolicy.DELAYS = [30, 120, 300]  # Exponential backoff

# Para AI Processing:
# Attempt 1: wait 30s → retry
# Attempt 2: wait 120s → retry
# Attempt 3: wait 300s → retry
# After 3 failures → Job goes to DLQ (failed queue)
```

## Manejo de Errores

```
Error Hierarchy:
├── WorkerJobError (base)
│   ├── RecoverableError
│   │   ├── AIProcessingError (timeout, rate limit)
│   │   └── (default para errores de red)
│   └── NonRecoverableError
│       ├── ValidationError (bad data)
│       └── ResourceNotFoundError (404)
```

**Clasificación:**
- **RecoverableError**: Retry automático (errores de red, timeout de IA)
- **NonRecoverableError**: Sin retry, va directo a DLQ

## Logging Correlacionado

Todos los logs incluyen contexto de correlación:

```json
{
  "timestamp": "2026-04-28T15:30:00Z",
  "level": "INFO",
  "job_id": "doc_123_20260428153000",
  "organization_id": 1,
  "correlation": {
    "job_id": "doc_123_20260428153000",
    "organization_id": 1,
    "document_id": 123,
    "user_id": 5,
    "queue": "ai_processing"
  }
}
```

## Observabilidad

### Comandos de Monitoring

```bash
# Ver stats de colas
python -m app.workers.runner --stats

# Health check
python -m app.workers.runner --health

# Ver jobs fallidos (DLQ)
python -m app.workers.runner --failed

# Ver logs del worker
tail -f /var/log/pranely/worker.log
```

### Métricas de Salud

- `queues.<name>.jobs`: Jobs encolados
- `queues.<name>.workers`: Workers activos
- `failed.total`: Jobs en DLQ

## Uso desde API

```python
from app.workers import enqueue_task

# Encolar procesamiento de documento
job = enqueue_task(
    "process_document",
    document_id=123,
    org_id=1,
    user_id=5,
    queue="ai_processing",
    meta={"request_id": "req-456"}
)

print(f"Job enqueued: {job.id}")
```

## Ejecutar Worker

```bash
# Script básico
./run_worker.sh

# Single queue
./run_worker.sh ai_processing

# Con docker compose (desarrollo)
docker compose up -d redis
docker compose run --rm backend python -m app.workers.runner

# Tests
./run_worker_tests.bat
```

## Archivos Creados/Modificados

| Archivo | Descripción |
|---------|-------------|
| `app/workers/config.py` | Configuración de queues, retry, timeout |
| `app/workers/logging_config.py` | Logging correlacionado |
| `app/workers/tasks.py` | Definición de jobs |
| `app/workers/runner.py` | Runner executable del worker |
| `app/workers/__init__.py` | Exports y helper de encolado |
| `tests/test_workers_rq.py` | Tests unitarios e integración |
| `run_worker.sh` | Script de startup |
| `.env.example` | Variables de worker |

## Criterios de Terminado

- [x] Jobs definidos con retry policy
- [x] Backoff exponencial configurado
- [x] Timeouts por tipo de tarea
- [x] Exception hierarchy para clasificación
- [x] DLQ implementado (cola 'failed')
- [x] Logging con correlation context
- [x] Observabilidad mínima (stats, health, failed)
- [x] Tests para happy path, retry, timeout, failure
- [x] Multi-tenant respetado (org_id en todos los jobs)
- [x] Sin secrets hardcodeados

## Próximo Paso

- **7B Contrato IA**: Integración real con DeepInfra para OCR/triage
- Alternativa: **9A Tests matrix** para coverage general

## Notas

- El worker usa `rq worker` standard con configuración de retry en los jobs
- DLQ implementado como cola 'failed' (RQ estándar)
- Circuit breaker ya existe en `redis_client.py` (fase anterior)