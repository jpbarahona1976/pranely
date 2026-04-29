"""
PRANELY RQ Workers package.

Subfase 7A: Worker resilient con retries, backoff, timeouts, DLQ.

Módulos:
- config: Configuración de queues, retry policy, timeout policy
- logging_config: Logging correlacionado con request_id / job_id / org_id
- redis_client: Cliente Redis con circuit breaker
- tasks: Tareas RQ para pipeline documental IA
- runner: Ejecutable del worker

Uso:
    # En API para encolar tarea
    from app.workers import enqueue_task
    
    # Para correr worker
    python -m app.workers.runner --queues ai_processing default --verbose
    
    # Para ver stats
    python -m app.workers.runner --stats
"""
from app.workers.config import (
    QueueNames,
    RetryPolicy,
    TimeoutPolicy,
    WorkerConfig,
    QueueConfig,
    QUEUES,
)
from app.workers.logging_config import (
    worker_logger,
    set_job_context,
    clear_job_context,
    get_job_context,
)
from app.workers.redis_client import (
    RedisClient,
    redis_client,
    get_redis,
    CircuitBreaker,
)
from app.workers.tasks import (
    # Tasks
    process_document,
    validate_waste_movement,
    send_notification,
    cleanup_old_jobs,
    health_check,
    # Exception hierarchy
    WorkerJobError,
    RecoverableError,
    NonRecoverableError,
    AIProcessingError,
    ValidationError,
    ResourceNotFoundError,
    # Helpers
    get_retry_for_task,
    get_timeout_for_task,
)

__all__ = [
    # Config
    "QueueNames",
    "RetryPolicy",
    "TimeoutPolicy",
    "WorkerConfig",
    "QueueConfig",
    "QUEUES",
    # Logging
    "worker_logger",
    "set_job_context",
    "clear_job_context",
    "get_job_context",
    # Redis
    "RedisClient",
    "redis_client",
    "get_redis",
    "CircuitBreaker",
    # Tasks
    "process_document",
    "validate_waste_movement",
    "send_notification",
    "cleanup_old_jobs",
    "health_check",
    # Exceptions
    "WorkerJobError",
    "RecoverableError",
    "NonRecoverableError",
    "AIProcessingError",
    "ValidationError",
    "ResourceNotFoundError",
    # Helpers
    "get_retry_for_task",
    "get_timeout_for_task",
]


# =============================================================================
# Enqueue helper para usar desde la API
# =============================================================================

def get_redis_connection():
    """Obtiene conexión Redis para encolar jobs."""
    from redis import Redis
    from app.workers.config import WorkerConfig
    return Redis.from_url(WorkerConfig.REDIS_URL, decode_responses=True)


def enqueue_task(
    func_name: str,
    *args,
    queue: str = None,
    job_timeout: int = None,
    retry: "Retry" = None,
    job_id: str = None,
    meta: dict = None,
    **kwargs,
):
    """
    Encola una tarea para ejecución asíncrona.
    
    Args:
        func_name: Nombre de la función de tarea
        *args: Argumentos positional para la tarea
        queue: Cola destino (default desde config)
        job_timeout: Timeout en segundos
        retry: Config de retry (Retry instance de rq)
        job_id: ID específico para el job
        meta: Metadata adicional para el job
        **kwargs: Argumentos keyword para la tarea
    
    Returns:
        Job instance
    """
    from rq import Queue
    
    from app.workers.tasks import get_timeout_for_task, get_retry_for_task
    
    redis_conn = get_redis_connection()
    queue_name = queue or WorkerConfig.DEFAULT_QUEUE
    
    if isinstance(queue_name, str):
        q = Queue(queue_name, connection=redis_conn)
    else:
        q = Queue(queue_name.value, connection=redis_conn)
    
    # Get task reference
    task_funcs = {
        "process_document": process_document,
        "validate_waste_movement": validate_waste_movement,
        "send_notification": send_notification,
        "cleanup_old_jobs": cleanup_old_jobs,
        "health_check": health_check,
    }
    
    func = task_funcs.get(func_name)
    if not func:
        raise ValueError(f"Unknown task function: {func_name}")
    
    # Get default timeout and retry if not specified
    timeout = job_timeout or get_timeout_for_task(func_name)
    retry_config = retry or get_retry_for_task(func_name)
    
    # Enqueue job
    job = q.enqueue(
        func,
        *args,
        kwargs=kwargs,
        timeout=timeout,
        job_timeout=timeout,
        retry=retry_config,
        job_id=job_id,
        meta=meta or {},
    )
    
    worker_logger.info(
        f"Enqueued task: {func_name}",
        job_id=job.id,
        queue=queue_name,
        timeout=timeout,
    )
    
    return job