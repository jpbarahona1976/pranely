"""
Structured logging for RQ workers with correlation context.

Subfase 7A: Logging correlacionado con request_id / job_id / organization_id.
"""
import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variables for correlation
job_context: ContextVar[Dict[str, Any]] = ContextVar("job_context", default={})

logger = logging.getLogger("workers")


def set_job_context(
    job_id: Optional[str] = None,
    organization_id: Optional[int] = None,
    document_id: Optional[int] = None,
    request_id: Optional[str] = None,
    user_id: Optional[int] = None,
    queue: Optional[str] = None,
) -> None:
    """Set job context for correlation in logs."""
    context = {
        "job_id": job_id,
        "organization_id": organization_id,
        "document_id": document_id,
        "request_id": request_id,
        "user_id": user_id,
        "queue": queue,
    }
    job_context.set({k: v for k, v in context.items() if v is not None})


def clear_job_context() -> None:
    """Clear job context after job completes."""
    job_context.set({})


def get_job_context() -> Dict[str, Any]:
    """Get current job context."""
    return job_context.get({})


class WorkerFormatter(logging.Formatter):
    """JSON formatter for worker logs with correlation context."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Get correlation context
        context = get_job_context()
        
        # Build log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation context
        log_entry["correlation"] = {
            k: v for k, v in context.items() if v is not None
        }
        
        # Add job_id at root level for easier querying
        if "job_id" in context:
            log_entry["job_id"] = context["job_id"]
        
        if "organization_id" in context:
            log_entry["organization_id"] = context["organization_id"]
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        
        return json.dumps(log_entry)


class WorkerLogger:
    """
    Logger especializado para workers con contexto de correlación.
    
    Uso:
        from app.workers.logging_config import worker_logger
        
        worker_logger.info("Processing started", extra_data={"doc_id": 123})
    """
    
    def __init__(self, name: str = "workers"):
        self.logger = logging.getLogger(name)
        self._setup_handler()
    
    def _setup_handler(self) -> None:
        """Configure handler with JSON formatter."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(WorkerFormatter())
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    def _log(self, level: int, msg: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Log with extra data."""
        extra = {"extra_data": kwargs} if kwargs else {}
        self.logger.log(level, msg, exc_info=exc_info, extra=extra)
    
    def debug(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, exc_info: bool = True, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, exc_info=exc_info, **kwargs)
    
    def critical(self, msg: str, exc_info: bool = True, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, msg, exc_info=exc_info, **kwargs)
    
    def log_job_start(
        self,
        job_id: str,
        func_name: str,
        organization_id: int,
        **kwargs: Any
    ) -> None:
        """Log job start with full context."""
        self.info(
            f"Job started: {func_name}",
            job_id=job_id,
            organization_id=organization_id,
            func_name=func_name,
            **kwargs
        )
    
    def log_job_success(
        self,
        job_id: str,
        func_name: str,
        duration_seconds: float,
        **kwargs: Any
    ) -> None:
        """Log job success with duration."""
        self.info(
            f"Job completed: {func_name}",
            job_id=job_id,
            func_name=func_name,
            duration_seconds=duration_seconds,
            **kwargs
        )
    
    def log_job_failure(
        self,
        job_id: str,
        func_name: str,
        error: str,
        retry_count: int,
        is_final: bool,
        **kwargs: Any
    ) -> None:
        """Log job failure with retry info."""
        level = logging.ERROR if is_final else logging.WARNING
        self._log(
            level,
            f"Job {'failed permanently' if is_final else 'retrying'}: {func_name}",
            exc_info=not is_final,
            job_id=job_id,
            func_name=func_name,
            error=error,
            retry_count=retry_count,
            is_final=is_final,
            **kwargs
        )
    
    def log_dlq_enqueued(
        self,
        job_id: str,
        func_name: str,
        original_queue: str,
        failure_reason: str,
        **kwargs: Any
    ) -> None:
        """Log job moved to DLQ."""
        self.warning(
            f"Job moved to DLQ: {func_name}",
            job_id=job_id,
            func_name=func_name,
            original_queue=original_queue,
            failure_reason=failure_reason,
            **kwargs
        )


# Global logger instance
worker_logger = WorkerLogger()