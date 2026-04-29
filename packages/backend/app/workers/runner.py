"""
RQ Worker runner para PRANELY.

Subfase 7A: Worker ejecutable con observabilidad mínima.

Ejecuta: python -m app.workers.runner
"""
import os
import sys
import logging
from datetime import datetime, timezone

# Ensure app is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from redis import Redis
from rq import Worker, Queue
from rq.connections import RedisConnection as Connection
from rq.command import send_shutdown_command

from app.workers.config import (
    QueueNames,
    WorkerConfig,
    QueueConfig,
    QUEUES,
)
from app.workers.logging_config import worker_logger, set_job_context
from app.workers import tasks

logger = logging.getLogger("workers.runner")


# =============================================================================
# Worker Runner
# =============================================================================

def create_worker(
    redis_url: str = None,
    queues: list = None,
    name: str = None,
) -> Worker:
    """
    Crea un worker RQ con configuración resiliente.
    
    Args:
        redis_url: URL de Redis (default desde config)
        queues: Lista de queues a escuchar
        name: Nombre del worker
    
    Returns:
        Worker instance
    """
    redis_url = redis_url or WorkerConfig.REDIS_URL
    queues = queues or [q.value for q in QUEUES]
    
    if name is None:
        name = f"pranely-worker-{os.uname().nodename}"
    
    # Create Redis connection
    redis_conn = Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
    
    # Create queues
    queue_objects = [Queue(q) for q in queues]
    
    # Create worker with observability
    worker = Worker(
        queue_objects,
        connection=redis_conn,
        name=name,
        default_worker_ttl=WorkerConfig.MAX_JOB_DURATION,
        job_timeout=WorkerConfig.DEFAULT_TIMEOUT,
        result_ttl=WorkerConfig.DEFAULT_RESULT_TTL,
        worker_ttl=WorkerConfig.HEARTBEAT_TIMEOUT,
    )
    
    return worker


def get_queue_stats() -> dict:
    """
    Obtiene estadísticas de las colas para observabilidad.
    
    Returns:
        Dict con stats por cola
    """
    try:
        redis_conn = Redis.from_url(WorkerConfig.REDIS_URL, decode_responses=True)
        
        stats = {}
        for queue_name in [q.value for q in QUEUES]:
            queue = Queue(queue_name, connection=redis_conn)
            stats[queue_name] = {
                "jobs": queue.count,
                "failed": 0,  # RQ no expone failed count directamente
                "workers": len(queue.get_workers()),
            }
        
        # Get failed jobs from failed queue
        failed_queue = Queue(QueueNames.FAILED.value, connection=redis_conn)
        stats["failed"] = {
            "total": failed_queue.count,
            "description": QueueConfig.QUEUES[QueueNames.FAILED]["description"],
        }
        
        return stats
    
    except Exception as e:
        worker_logger.warning(f"Failed to get queue stats: {e}")
        return {"error": str(e)}


def get_failed_jobs(limit: int = 10) -> list:
    """
    Obtiene jobs fallidos para revisión manual.
    
    Args:
        limit: Máximo número de jobs a retornar
    
    Returns:
        Lista de dicts con info de jobs fallidos
    """
    try:
        redis_conn = Redis.from_url(WorkerConfig.REDIS_URL, decode_responses=True)
        failed_queue = Queue(QueueNames.FAILED.value, connection=redis_conn)
        
        failed_jobs = []
        for job in failed_queue.get_jobs()[0:limit]:
            failed_jobs.append({
                "id": job.id,
                "func_name": job.func_name,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "failed_at": job.ended_at.isoformat() if hasattr(job, 'ended_at') and job.ended_at else None,
                "exc_info": getattr(job, '_exc_info', None),
                "meta": job.meta,
            })
        
        return failed_jobs
    
    except Exception as e:
        worker_logger.warning(f"Failed to get failed jobs: {e}")
        return []


def health_check_worker() -> dict:
    """
    Health check del worker runner.
    
    Returns:
        Dict con estado de salud
    """
    stats = get_queue_stats()
    failed_jobs = get_failed_jobs(limit=5)
    
    return {
        "status": "healthy" if "error" not in stats else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queues": stats,
        "recent_failures": failed_jobs,
    }


def log_worker_status(worker: Worker) -> None:
    """
    Log status del worker periódicamente.
    """
    state = worker.get_state()
    current_job = worker.get_current_job_id()
    
    worker_logger.info(
        "Worker status",
        worker_name=worker.name,
        state=state,
        current_job=current_job,
        queues=[q.name for q in worker.queues],
    )


# =============================================================================
# CLI Commands
# =============================================================================

def run_worker(
    queues: list = None,
    name: str = None,
    verbose: bool = True,
) -> None:
    """
    Ejecuta worker RQ.
    
    Args:
        queues: Lista de queues a escuchar
        name: Nombre del worker
        verbose: Logging verbose
    """
    queues = queues or [q.value for q in QUEUES]
    
    worker_logger.info(
        "Starting PRANELY RQ worker",
        queues=queues,
        worker_name=name,
    )
    
    # Create worker
    worker = create_worker(
        queues=queues,
        name=name,
    )
    
    # Log worker info
    log_worker_status(worker)
    
    # Run worker
    worker.work(
        with_scheduler=True,
        log_level="DEBUG" if verbose else "INFO",
    )


def run_scheduler() -> None:
    """
    Ejecuta scheduler para jobs periódicos.
    """
    worker_logger.info("Starting RQ scheduler")
    
    from rq.scheduler import RQScheduler
    
    scheduler = RQScheduler(
        connection=Redis.from_url(WorkerConfig.REDIS_URL),
        interval=WorkerConfig.JOB_MONITORING_INTERVAL,
    )
    
    scheduler.run()


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PRANELY RQ Worker Runner")
    parser.add_argument(
        "--queues",
        nargs="+",
        default=None,
        help="Queues to listen to (default: all)",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Worker name",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show queue stats and exit",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Health check and exit",
    )
    parser.add_argument(
        "--failed",
        action="store_true",
        help="Show failed jobs and exit",
    )
    
    args = parser.parse_args()
    
    if args.stats:
        import json
        stats = get_queue_stats()
        print(json.dumps(stats, indent=2, default=str))
        sys.exit(0)
    
    if args.health:
        import json
        health = health_check_worker()
        print(json.dumps(health, indent=2, default=str))
        sys.exit(0)
    
    if args.failed:
        import json
        jobs = get_failed_jobs(limit=20)
        print(json.dumps(jobs, indent=2, default=str))
        sys.exit(0)
    
    # Run worker
    run_worker(
        queues=args.queues,
        name=args.name,
        verbose=args.verbose,
    )