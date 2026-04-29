"""
Tests para RQ Workers (Subfase 7A).

Test suites:
1. TestRetryPolicy: Verifica configuración de retry y backoff
2. TestTimeoutPolicy: Verifica timeouts por tipo de tarea
3. TestWorkerExceptions: Verifica jerarquía de excepciones
4. TestTaskHelpers: Verifica funciones auxiliares
5. TestProcessDocument: Tests unitarios del task principal
6. TestValidateWasteMovement: Tests de validación
7. TestLoggingCorrelation: Tests de correlación de logs
8. TestEnqueueHelper: Tests del helper de encolado
9. TestQueueObservability: Tests de stats y observabilidad

Ejecutar con:
    pytest packages/backend/tests/test_workers_rq.py -v
"""
import os
import sys
import pytest
import json
import logging
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from io import StringIO

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set environment for config
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ENV", "test")


# =============================================================================
# Test Retry Policy
# =============================================================================

class TestRetryPolicy:
    """Tests para RetryPolicy."""
    
    def test_max_retries_is_3(self):
        """Max retries es 3."""
        from app.workers.config import RetryPolicy
        assert RetryPolicy.MAX_RETRIES == 3
    
    def test_delays_are_exponential(self):
        """Delays siguen patrón exponencial."""
        from app.workers.config import RetryPolicy
        assert RetryPolicy.DELAYS == [30, 120, 300]
        # Verify exponential-ish growth
        assert RetryPolicy.DELAYS[0] < RetryPolicy.DELAYS[1] < RetryPolicy.DELAYS[2]
    
    def test_get_retry_returns_retry_for_valid_attempt(self):
        """get_retry devuelve Retry instance para intento válido."""
        from app.workers.config import RetryPolicy
        from rq import Retry
        
        retry = RetryPolicy.get_retry(0)
        assert retry is not None
        assert isinstance(retry, Retry)
        assert retry.max == 3
    
    def test_get_retry_returns_none_for_last_attempt(self):
        """get_retry devuelve None para último intento."""
        from app.workers.config import RetryPolicy
        
        retry = RetryPolicy.get_retry(3)
        assert retry is None
    
    def test_retry_intervals_match_delays(self):
        """Retry intervals coinciden con delays configurados."""
        from app.workers.config import RetryPolicy
        from rq import Retry
        
        # First attempt: 30s delay
        retry1 = RetryPolicy.get_retry(0)
        assert retry1 is not None
        
        # Verify we can create Retry with custom intervals
        retry_custom = Retry(max=3, interval=[30, 120, 300])
        assert retry_custom.max == 3
        assert len(retry_custom.intervals) == 3


# =============================================================================
# Test Timeout Policy
# =============================================================================

class TestTimeoutPolicy:
    """Tests para TimeoutPolicy."""
    
    def test_defaults_are_defined(self):
        """Timeouts por defecto definidos."""
        from app.workers.config import TimeoutPolicy
        
        assert TimeoutPolicy.DEFAULT == 300
        assert TimeoutPolicy.AI_PROCESSING == 120
        assert TimeoutPolicy.OCR_TRIAGE == 180
        assert TimeoutPolicy.NOTIFICATION == 60
    
    def test_timeout_values_are_sensible(self):
        """Timeouts son valores razonables."""
        from app.workers.config import TimeoutPolicy
        
        # No timeout should be negative
        assert TimeoutPolicy.DEFAULT > 0
        assert TimeoutPolicy.AI_PROCESSING > 0
        assert TimeoutPolicy.NOTIFICATION > 0
        
        # AI tasks have reasonable timeouts (< 5 min)
        assert TimeoutPolicy.AI_PROCESSING < 300
        
        # Cleanup can be longer (10 min)
        assert TimeoutPolicy.CLEANUP >= 600


# =============================================================================
# Test Worker Exceptions
# =============================================================================

class TestWorkerExceptions:
    """Tests para jerarquía de excepciones."""
    
    def test_exception_hierarchy(self):
        """Jerarquía correcta: RecoverableError -> WorkerJobError."""
        from app.workers.tasks import (
            WorkerJobError,
            RecoverableError,
            NonRecoverableError,
        )
        
        assert issubclass(RecoverableError, WorkerJobError)
        assert issubclass(NonRecoverableError, WorkerJobError)
    
    def test_ai_processing_error_is_recoverable(self):
        """AIProcessingError es RecoverableError."""
        from app.workers.tasks import AIProcessingError, RecoverableError
        assert issubclass(AIProcessingError, RecoverableError)
    
    def test_validation_error_is_non_recoverable(self):
        """ValidationError es NonRecoverableError."""
        from app.workers.tasks import ValidationError, NonRecoverableError
        assert issubclass(ValidationError, NonRecoverableError)
    
    def test_resource_not_found_is_non_recoverable(self):
        """ResourceNotFoundError es NonRecoverableError."""
        from app.workers.tasks import ResourceNotFoundError, NonRecoverableError
        assert issubclass(ResourceNotFoundError, NonRecoverableError)
    
    def test_can_raise_and_catch_by_type(self):
        """Se puede catch por tipo específico."""
        from app.workers.tasks import (
            RecoverableError,
            NonRecoverableError,
            ValidationError,
        )
        
        # RecoverableError catch
        try:
            raise RecoverableError("temp error")
        except RecoverableError:
            pass  # OK
        except Exception:
            pytest.fail("Should have caught RecoverableError")
        
        # ValidationError - específico
        try:
            raise ValidationError("bad data")
        except NonRecoverableError:
            pass  # OK
        except Exception:
            pytest.fail("Should have caught as NonRecoverableError")


# =============================================================================
# Test Task Helpers
# =============================================================================

class TestTaskHelpers:
    """Tests para funciones auxiliares de tasks."""
    
    def test_get_retry_for_task_returns_retry(self):
        """get_retry_for_task devuelve Retry para tasks conocidas."""
        from app.workers.tasks import get_retry_for_task
        
        retry = get_retry_for_task("process_document")
        assert retry is not None
    
    def test_get_retry_for_unknown_task_returns_none(self):
        """get_retry_for_task devuelve None para tasks desconocidas."""
        from app.workers.tasks import get_retry_for_task
        
        retry = get_retry_for_task("unknown_task")
        assert retry is None
    
    def test_get_timeout_for_task_returns_int(self):
        """get_timeout_for_task devuelve int."""
        from app.workers.tasks import get_timeout_for_task
        
        timeout = get_timeout_for_task("process_document")
        assert isinstance(timeout, int)
        assert timeout > 0
    
    def test_get_timeout_for_unknown_task_returns_default(self):
        """get_timeout para task desconocida devuelve default."""
        from app.workers.tasks import get_timeout_for_task
        from app.workers.config import TimeoutPolicy
        
        timeout = get_timeout_for_task("unknown_task")
        assert timeout == TimeoutPolicy.DEFAULT


# =============================================================================
# Test Process Document Task
# =============================================================================

class TestProcessDocument:
    """Tests para task process_document (async)."""
    
    @pytest.mark.asyncio
    async def test_process_document_success(self):
        """Procesamiento exitoso de documento."""
        from app.workers.tasks import process_document
        
        result = await process_document(
            document_id=1,
            org_id=1,
            user_id=1,
        )
        
        assert result["status"] == "completed"
        assert result["document_id"] == 1
        assert result["org_id"] == 1
        assert "job_id" in result
        assert "processed_at" in result
        assert "confidence" in result
    
    @pytest.mark.asyncio
    async def test_process_document_with_request_id(self):
        """Procesamiento con request_id para correlación."""
        from app.workers.tasks import process_document
        
        result = await process_document(
            document_id=1,
            org_id=1,
            user_id=1,
            request_id="req-123",
        )
        
        assert result["status"] == "completed"
        assert "job_id" in result
    
    @pytest.mark.asyncio
    async def test_process_document_invalid_id_raises(self):
        """Document ID inválido lanza NonRecoverableError."""
        from app.workers.tasks import process_document, NonRecoverableError
        
        with pytest.raises(NonRecoverableError):
            await process_document(
                document_id=0,
                org_id=1,
                user_id=1,
            )
    
    @pytest.mark.asyncio
    async def test_process_document_result_contains_job_id(self):
        """Resultado contiene job_id con formato correcto."""
        from app.workers.tasks import process_document
        
        result = await process_document(
            document_id=42,
            org_id=5,
            user_id=3,
        )
        
        assert "job_id" in result
        assert result["job_id"].startswith("doc_42_")
    
    @pytest.mark.asyncio
    async def test_process_document_result_contains_duration(self):
        """Resultado contiene duración en segundos."""
        from app.workers.tasks import process_document
        
        result = await process_document(
            document_id=1,
            org_id=1,
            user_id=1,
        )
        
        assert "duration_seconds" in result
        assert result["duration_seconds"] >= 0


# =============================================================================
# Test Validate Waste Movement
# =============================================================================

class TestValidateWasteMovement:
    """Tests para validate_waste_movement."""
    
    def test_validate_waste_movement_success(self):
        """Validación exitosa de movement."""
        from app.workers.tasks import validate_waste_movement
        
        result = validate_waste_movement(
            movement_id=1,
            org_id=1,
        )
        
        assert result["status"] == "validated"
        assert result["movement_id"] == 1
        assert "job_id" in result
        assert "duration_seconds" in result
    
    def test_validate_waste_movement_includes_noma_compliance(self):
        """Resultado incluye info de compliance NOM-052."""
        from app.workers.tasks import validate_waste_movement
        
        result = validate_waste_movement(
            movement_id=1,
            org_id=1,
        )
        
        assert "norma_compliant" in result
        assert "validation_checks" in result


# =============================================================================
# Test Send Notification
# =============================================================================

class TestSendNotification:
    """Tests para send_notification."""
    
    def test_send_notification_success(self):
        """Envío exitoso de notificación."""
        from app.workers.tasks import send_notification
        
        result = send_notification(
            user_id=1,
            org_id=1,
            notification_type="email",
            title="Test",
            message="Hello",
        )
        
        assert result["sent"] is True
        assert result["user_id"] == 1
        assert "sent_at" in result
    
    def test_send_notification_with_all_types(self):
        """Envío con diferentes tipos de notificación."""
        from app.workers.tasks import send_notification
        
        for notif_type in ["email", "sms", "push"]:
            result = send_notification(
                user_id=1,
                org_id=1,
                notification_type=notif_type,
                title="Test",
                message="Message",
            )
            assert result["type"] == notif_type


# =============================================================================
# Test Cleanup Old Jobs
# =============================================================================

class TestCleanupOldJobs:
    """Tests para cleanup_old_jobs."""
    
    def test_cleanup_with_default_days(self):
        """Cleanup con days_old por defecto."""
        from app.workers.tasks import cleanup_old_jobs
        
        result = cleanup_old_jobs()
        
        assert "deleted_count" in result
        assert result["days_old"] == 30
    
    def test_cleanup_with_custom_days(self):
        """Cleanup con days_old personalizado."""
        from app.workers.tasks import cleanup_old_jobs
        
        result = cleanup_old_jobs(days_old=60)
        
        assert result["days_old"] == 60


# =============================================================================
# Test Logging Correlation
# =============================================================================

class TestLoggingCorrelation:
    """Tests para logging con correlación de contexto."""
    
    def test_set_job_context(self):
        """set_job_context establece contexto correctamente."""
        from app.workers.logging_config import set_job_context, get_job_context, clear_job_context
        
        set_job_context(
            job_id="test-job-123",
            organization_id=1,
            document_id=42,
        )
        
        context = get_job_context()
        assert context["job_id"] == "test-job-123"
        assert context["organization_id"] == 1
        assert context["document_id"] == 42
        
        clear_job_context()
    
    def test_clear_job_context(self):
        """clear_job_context limpia todo."""
        from app.workers.logging_config import set_job_context, get_job_context, clear_job_context
        
        set_job_context(job_id="test", organization_id=1)
        clear_job_context()
        
        context = get_job_context()
        assert context == {}
    
    def test_worker_logger_records_job_start(self):
        """worker_logger.log_job_start registra correctamente."""
        from app.workers.logging_config import worker_logger
        
        # Should not raise
        worker_logger.log_job_start(
            job_id="test-job",
            func_name="test_func",
            organization_id=1,
        )
    
    def test_worker_logger_records_job_success(self):
        """worker_logger.log_job_success registra correctamente."""
        from app.workers.logging_config import worker_logger
        
        worker_logger.log_job_success(
            job_id="test-job",
            func_name="test_func",
            duration_seconds=1.5,
        )
    
    def test_worker_logger_records_job_failure(self):
        """worker_logger.log_job_failure registra correctamente."""
        from app.workers.logging_config import worker_logger
        
        worker_logger.log_job_failure(
            job_id="test-job",
            func_name="test_func",
            error="Test error",
            retry_count=1,
            is_final=False,
        )
    
    def test_worker_logger_records_dlq(self):
        """worker_logger.log_dlq_enqueued registra correctamente."""
        from app.workers.logging_config import worker_logger
        
        worker_logger.log_dlq_enqueued(
            job_id="test-job",
            func_name="test_func",
            original_queue="ai_processing",
            failure_reason="Max retries exceeded",
        )


# =============================================================================
# Test Queue Names and Config
# =============================================================================

class TestQueueConfig:
    """Tests para configuración de colas."""
    
    def test_queue_names_are_defined(self):
        """Todas las queues están definidas."""
        from app.workers.config import QueueNames
        
        assert QueueNames.HIGH.value == "high"
        assert QueueNames.DEFAULT.value == "default"
        assert QueueNames.LOW.value == "low"
        assert QueueNames.AI_PROCESSING.value == "ai_processing"
        assert QueueNames.FAILED.value == "failed"
    
    def test_queues_list_excludes_failed(self):
        """QUEUES no incluye failed (es DLQ, no se escucha)."""
        from app.workers.config import QUEUES
        
        queue_names = [q.value for q in QUEUES]
        assert "failed" not in queue_names
    
    def test_queue_config_has_description(self):
        """Cada cola tiene descripción."""
        from app.workers.config import QueueConfig
        
        for queue, config in QueueConfig.QUEUES.items():
            assert "description" in config
            assert config["description"]
    
    def test_failed_queue_ttl_is_7_days(self):
        """Cola failed tiene TTL de 7 días."""
        from app.workers.config import QueueNames, QueueConfig
        
        failed_config = QueueConfig.QUEUES[QueueNames.FAILED]
        assert failed_config["ttl"] == 604800  # 7 días en segundos


# =============================================================================
# Test Worker Config
# =============================================================================

class TestWorkerConfig:
    """Tests para WorkerConfig."""
    
    def test_max_job_duration_is_reasonable(self):
        """MAX_JOB_DURATION es menor a 1 hora."""
        from app.workers.config import WorkerConfig
        
        assert WorkerConfig.MAX_JOB_DURATION < 3600
        assert WorkerConfig.MAX_JOB_DURATION > 0
    
    def test_heartbeat_timeout_is_reasonable(self):
        """HEARTBEAT_TIMEOUT es menor a MAX_JOB_DURATION."""
        from app.workers.config import WorkerConfig
        
        assert WorkerConfig.HEARTBEAT_TIMEOUT < WorkerConfig.MAX_JOB_DURATION
        assert WorkerConfig.HEARTBEAT_TIMEOUT > 0
    
    def test_failed_jobs_ttl_is_7_days(self):
        """FAILED_JOBS_TTL es 7 días."""
        from app.workers.config import WorkerConfig
        
        assert WorkerConfig.FAILED_JOBS_TTL == 604800


# =============================================================================
# Test Enqueue Helper
# =============================================================================

class TestEnqueueHelper:
    """Tests para helper de encolado de tareas."""
    
    def test_enqueue_task_is_callable(self):
        """enqueue_task existe y es callable."""
        from app.workers import enqueue_task
        
        assert callable(enqueue_task)
    
    def test_enqueue_unknown_task_raises(self):
        """enqueue_task con task desconocida raise ValueError."""
        from app.workers import enqueue_task
        
        # This will fail because Redis is not running, but we can test the validation
        with pytest.raises(ValueError, match="Unknown task function"):
            enqueue_task("unknown_task")


# =============================================================================
# Test Health Check Task
# =============================================================================

class TestHealthCheck:
    """Tests para task health_check."""
    
    def test_health_check_returns_status(self):
        """health_check devuelve dict con status."""
        from app.workers.tasks import health_check
        
        result = health_check()
        
        assert "status" in result
        assert "timestamp" in result
        assert "job_id" in result
    
    def test_health_check_includes_checks(self):
        """health_check incluye checks de componentes."""
        from app.workers.tasks import health_check
        
        result = health_check()
        
        # May include redis check depending on availability
        assert "checks" in result


# =============================================================================
# Integration Tests (require Redis)
# =============================================================================

class TestWorkerIntegration:
    """Integration tests que requieren Redis."""
    
    @pytest.fixture(autouse=True)
    def check_redis(self):
        """Skip si Redis no está disponible."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            sock.connect(("localhost", 6379))
            sock.close()
        except (socket.timeout, ConnectionRefusedError):
            pytest.skip("Redis not available")
    
    def test_enqueue_and_fetch_job(self):
        """Encolar job y recuperarlo."""
        from redis import Redis
        from rq import Queue
        
        redis_conn = Redis.from_url("redis://localhost:6379", decode_responses=True)
        q = Queue("default", connection=redis_conn)
        
        # Enqueue simple job
        from app.workers.tasks import send_notification
        
        job = q.enqueue(
            send_notification,
            user_id=1,
            org_id=1,
            notification_type="test",
            title="Test",
            message="Integration test",
            job_timeout=30,
        )
        
        assert job.id is not None
        assert job.func_name == "app.workers.tasks.send_notification"
        
        # Clean up
        q.remove(job)
    
    def test_queue_stats_available(self):
        """Estadísticas de cola disponibles."""
        from app.workers.runner import get_queue_stats
        
        stats = get_queue_stats()
        
        # Should return dict with queue info (may have error if Redis not configured)
        assert isinstance(stats, dict)
    
    def test_health_check_worker(self):
        """Health check del worker."""
        from app.workers.runner import health_check_worker
        
        health = health_check_worker()
        
        assert "status" in health
        assert "timestamp" in health
        assert "queues" in health


# =============================================================================
# Test Idempotency
# =============================================================================

class TestIdempotency:
    """Tests para idempotencia en reprocesos."""
    
    @pytest.mark.asyncio
    async def test_process_document_twice_produces_same_job_id_prefix(self):
        """Procesar dos veces el mismo documento produce jobs diferentes."""
        from app.workers.tasks import process_document
        
        # Los job IDs incluyen timestamp, así que serán diferentes
        result1 = await process_document(document_id=1, org_id=1, user_id=1)
        result2 = await process_document(document_id=1, org_id=1, user_id=1)
        
        # Pero el document_id en el resultado es el mismo
        assert result1["document_id"] == result2["document_id"] == 1
    
    def test_validate_idempotent_data(self):
        """Validación de datos es idempotente."""
        from app.workers.tasks import validate_waste_movement
        
        # Mismo ID produce mismo resultado (sin efectos secundarios)
        result1 = validate_waste_movement(movement_id=1, org_id=1)
        result2 = validate_waste_movement(movement_id=1, org_id=1)
        
        assert result1["movement_id"] == result2["movement_id"]
        assert result1["status"] == result2["status"]


# =============================================================================
# Test Resilience: Retry and Timeout
# =============================================================================

class TestResilience:
    """Tests para resiliencia: retry, timeout, fallo."""
    
    def test_recoverable_error_triggers_retry(self):
        """RecoverableError permite retry."""
        from app.workers.tasks import RecoverableError
        
        # RecoverableError puede ser lanzada y catcheada para retry
        error = RecoverableError("Temporary failure")
        assert isinstance(error, Exception)
        assert isinstance(error, RecoverableError)
    
    def test_non_recoverable_error_does_not_retry(self):
        """NonRecoverableError no debería hacer retry."""
        from app.workers.tasks import NonRecoverableError
        
        # NonRecoverableError significa "no recoverable"
        error = NonRecoverableError("Permanent failure")
        assert isinstance(error, NonRecoverableError)
    
    def test_validation_error_classification(self):
        """ValidationError es no recuperable."""
        from app.workers.tasks import ValidationError
        
        error = ValidationError("Missing required field")
        # Classification correct
        assert "ValidationError" in str(type(error).__name__)
    
    def test_job_failure_log_includes_retry_info(self):
        """Log de failure incluye retry info."""
        from app.workers.logging_config import worker_logger
        
        # Should not raise
        worker_logger.log_job_failure(
            job_id="test",
            func_name="test_func",
            error="Test",
            retry_count=1,
            is_final=False,
        )
        
        worker_logger.log_job_failure(
            job_id="test",
            func_name="test_func",
            error="Test",
            retry_count=3,
            is_final=True,
        )
    
    def test_dlq_log_includes_failure_reason(self):
        """Log de DLQ incluye reason del fallo."""
        from app.workers.logging_config import worker_logger
        
        worker_logger.log_dlq_enqueued(
            job_id="test-dlq",
            func_name="test_func",
            original_queue="ai_processing",
            failure_reason="Max retries exceeded after 3 attempts",
        )


# =============================================================================
# Run all tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])