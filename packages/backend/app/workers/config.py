"""
RQ Worker configuration and queues for PRANELY.

Subfase 7A: Worker resilient con retries, backoff, timeouts y DLQ.
"""
from enum import Enum


class QueueNames(str, Enum):
    """RQ queue names in priority order."""
    HIGH = "high"
    DEFAULT = "default"
    LOW = "low"
    AI_PROCESSING = "ai_processing"
    FAILED = "failed"  # DLQ equivalent


class RetryPolicy:
    """
    Política de reintentos para jobs RQ.
    
    Backoff exponencial: 30s → 120s → 300s (3 intentos max).
    Después de 3 fallos, el job va a la cola 'failed' (DLQ).
    """
    MAX_RETRIES = 3
    
    # Delay en segundos (exponencial)
    DELAYS = [30, 120, 300]
    
    @classmethod
    def get_retry(cls, attempt: int) -> "Retry":
        """
        Obtiene retry configurado para un intento específico.
        
        Args:
            attempt: Número de intento (0-indexed)
        
        Returns:
            Retry instance de rq
        """
        from rq import Retry
        
        if attempt >= cls.MAX_RETRIES:
            return None
        
        delay = cls.DELAYS[min(attempt, len(cls.DELAYS) - 1)]
        return Retry(max=cls.MAX_RETRIES, interval=delay)


class TimeoutPolicy:
    """
    Timeouts por tipo de tarea.
    
    Evita jobs stuck indefinidamente.
    """
    # Timeouts en segundos
    DEFAULT = 300  # 5 minutos
    AI_PROCESSING = 120  # 2 minutos
    OCR_TRIAGE = 180  # 3 minutos
    NOTIFICATION = 60  # 1 minuto
    CLEANUP = 600  # 10 minutos
    DOCUMENT_UPLOAD = 90  # 1.5 minutos


class WorkerConfig:
    """RQ worker configuration."""
    
    # Connection settings
    REDIS_URL = "redis://localhost:6379"
    
    # Worker settings
    DEFAULT_RESULT_TTL = 3600  # 1 hour
    JOB_MONITORING_INTERVAL = 60  # seconds
    MAX_JOB_DURATION = 1800  # 30 minutos (seguridad)
    
    # Queue configuration
    DEFAULT_QUEUE = QueueNames.DEFAULT
    AI_QUEUE = QueueNames.AI_PROCESSING
    
    # DLQ settings
    FAILED_QUEUE = QueueNames.FAILED
    FAILED_JOBS_TTL = 7 * 24 * 3600  # 7 días
    
    # Monitoring
    HEARTBEAT_TIMEOUT = 600  # 10 minutos sin heartbeat = stuck


class QueueConfig:
    """Configuración por cola."""
    
    QUEUES = {
        QueueNames.HIGH: {
            "description": "Tareas críticas de prioridad alta",
            "ttl": 3600,
        },
        QueueNames.DEFAULT: {
            "description": "Tareas normales",
            "ttl": 86400,
        },
        QueueNames.LOW: {
            "description": "Tareas de baja prioridad (cleanup, reportes)",
            "ttl": 604800,  # 7 días
        },
        QueueNames.AI_PROCESSING: {
            "description": "Procesamiento de documentos con IA",
            "ttl": 7200,  # 2 horas
        },
        QueueNames.FAILED: {
            "description": "Dead Letter Queue - jobs fallidos",
            "ttl": 604800,  # 7 días
        },
    }


# Exported constants
QUEUES = [
    QueueNames.HIGH,
    QueueNames.DEFAULT,
    QueueNames.LOW,
    QueueNames.AI_PROCESSING,
]

__all__ = [
    "QueueNames",
    "RetryPolicy",
    "TimeoutPolicy",
    "WorkerConfig",
    "QueueConfig",
    "QUEUES",
]