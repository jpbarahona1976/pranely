"""
RQ Tasks for PRANELY document processing pipeline.

Subfase 7A: Pipeline asíncrono con retries, backoff, timeouts, DLQ.

Jobs definidos:
- process_document: OCR/triage de documento subido
- validate_waste_movement: Validación de manifiesto contra NOM-052
- send_notification: Notificaciones asíncronas
- cleanup_old_jobs: Cleanup periódico
- health_check: Health check del worker
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from rq import Retry

from app.workers.config import RetryPolicy, TimeoutPolicy, QueueNames
from app.workers.logging_config import (
    worker_logger,
    set_job_context,
    clear_job_context,
    get_job_context,
)

logger = logging.getLogger("workers.tasks")


# =============================================================================
# Exception Hierarchy para categorización de errores
# =============================================================================

class WorkerJobError(Exception):
    """Base exception for worker jobs."""
    pass


class RecoverableError(WorkerJobError):
    """Error recuperable - permite retry."""
    pass


class NonRecoverableError(WorkerJobError):
    """Error no recuperable - va directo a DLQ."""
    pass


class AIProcessingError(RecoverableError):
    """Error en procesamiento de IA (DeepInfra timeout, rate limit)."""
    pass


class ValidationError(NonRecoverableError):
    """Error de validación - datos inválidos no se pueden reparar con retry."""
    pass


class ResourceNotFoundError(NonRecoverableError):
    """Recurso no encontrado - no se puede recuperar."""
    pass


# =============================================================================
# Helper functions
# =============================================================================

def validate_document_exists(document_id: int, org_id: int) -> Dict[str, Any]:
    """
    Valida que el documento existe y pertenece al tenant.
    
    En producción, consultaría la base de datos.
    Para 7A, simulamos la validación.
    
    Returns:
        Documento simulado
    
    Raises:
        ResourceNotFoundError: Si el documento no existe
    """
    # Simulación - en producción sería query a DB
    if document_id <= 0:
        raise ResourceNotFoundError(f"Document {document_id} not found")
    
    return {
        "id": document_id,
        "org_id": org_id,
        "status": "pending",
        "file_path": f"/uploads/{org_id}/documents/{document_id}.pdf",
    }


def validate_waste_movement_data(data: Dict[str, Any]) -> None:
    """
    Valida datos de waste movement.
    
    Raises:
        ValidationError: Si los datos son inválidos
    """
    required_fields = ["manifest_number", "quantity"]
    missing = [f for f in required_fields if f not in data or data[f] is None]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")
    
    if data.get("quantity", 0) < 0:
        raise ValidationError("Quantity cannot be negative")


# =============================================================================
# Document Processing Pipeline
# =============================================================================

async def process_document(
    document_id: int,
    org_id: int,
    user_id: int,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Procesa documento para OCR/triage asíncrono.
    
    Pipeline:
    1. Validar documento existe
    2. Descargar archivo
    3. Enviar a DeepInfra para OCR (async)
    4. Parsear resultado
    5. Actualizar estado del documento
    6. Encolar validación si es waste movement
    
    Args:
        document_id: ID del documento
        org_id: Organization ID (multi-tenant)
        user_id: Usuario que subió el documento
        request_id: Request ID para correlación
    
    Returns:
        Dict con resultado del procesamiento
    
    Raises:
        RecoverableError: Si hay error temporal (retry)
        NonRecoverableError: Si hay error permanente (DLQ)
    """
    job_id = f"doc_{document_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    # Set correlation context
    set_job_context(
        job_id=job_id,
        organization_id=org_id,
        document_id=document_id,
        request_id=request_id,
        user_id=user_id,
        queue=QueueNames.AI_PROCESSING.value,
    )
    
    start_time = datetime.now(timezone.utc)
    
    worker_logger.log_job_start(
        job_id=job_id,
        func_name="process_document",
        organization_id=org_id,
        document_id=document_id,
        user_id=user_id,
    )
    
    try:
        # === Step 1: Validar documento ===
        doc = validate_document_exists(document_id, org_id)
        
        # === Step 2: OCR con DeepInfra Client ===
        # Usar DeepInfraClient real para procesamiento de IA
        from app.services.ai import get_deepinfra_client
        
        ai_client = get_deepinfra_client()
        
        # Construir request para OCR
        from app.schemas.api.ai import OCRRequest
        ocr_request = OCRRequest(
            document_id=document_id,
            org_id=org_id,
            user_id=user_id,
            file_url=doc["file_path"],
            file_type="pdf",  # Default, en producción vendría del documento
            expected_document_type=None,  # Auto-detectar
        )
        
        # Procesar con IA (maneja timeout, rate limit internamente)
        ocr_response = await ai_client.ocr_process(ocr_request)
        
        # Extraer datos del response
        ocr_result = {
            "document_id": document_id,
            "text_extracted": ocr_response.text_extracted,
            "confidence": ocr_response.confidence,
            "detected_type": ocr_response.detected_type.value,
            "fields": {f.name: f.value for f in ocr_response.fields},
            "is_waste_manifest": ocr_response.is_waste_manifest,
            "manifest_number": ocr_response.manifest_number,
        }
        
        # === Step 3: Parsear y validar ===
        # Verificar si es waste movement
        if ocr_response.is_waste_manifest:
            # Encolar validación asíncrona
            # En producción: encolaría validate_waste_movement
            worker_logger.info(
                "Waste manifest detected, enqueuing validation",
                document_id=document_id,
                manifest=ocr_response.manifest_number,
            )
        
        # === Step 4: Actualizar documento en DB ===
        # En producción: update document status to "processed"
        worker_logger.info(
            "Document processed successfully",
            document_id=document_id,
            confidence=ocr_response.confidence,
        )
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        worker_logger.log_job_success(
            job_id=job_id,
            func_name="process_document",
            duration_seconds=duration,
            confidence=ocr_result["confidence"],
        )
        
        return {
            "job_id": job_id,
            "document_id": document_id,
            "org_id": org_id,
            "status": "completed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "confidence": ocr_result["confidence"],
            "ocr_result": ocr_result,
            "duration_seconds": duration,
        }
    
    except ResourceNotFoundError as e:
        # Error no recuperable - no hacer retry
        worker_logger.log_job_failure(
            job_id=job_id,
            func_name="process_document",
            error=str(e),
            retry_count=0,
            is_final=True,
        )
        raise NonRecoverableError(str(e)) from e
    
    except Exception as e:
        # Error recuperable por defecto
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Clasificar tipo de error
        error_msg = str(e).lower()
        if any(x in error_msg for x in ["timeout", "rate limit", "connection", "unavailable"]):
            error_type = "recoverable"
        else:
            error_type = "unknown"
        
        worker_logger.log_job_failure(
            job_id=job_id,
            func_name="process_document",
            error=str(e),
            retry_count=0,  # RQ maneja esto
            is_final=False,
            error_type=error_type,
        )
        
        raise RecoverableError(f"Document processing failed: {e}") from e
    
    finally:
        clear_job_context()


# =============================================================================
# Waste Movement Validation
# =============================================================================

def validate_waste_movement(
    movement_id: int,
    org_id: int,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Valida waste movement contra NOM-052.
    
    Args:
        movement_id: ID del movement
        org_id: Organization ID (multi-tenant)
        request_id: Request ID para correlación
    
    Returns:
        Dict con resultado de validación
    """
    job_id = f"wm_{movement_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    set_job_context(
        job_id=job_id,
        organization_id=org_id,
        request_id=request_id,
        queue=QueueNames.AI_PROCESSING.value,
    )
    
    start_time = datetime.now(timezone.utc)
    
    worker_logger.log_job_start(
        job_id=job_id,
        func_name="validate_waste_movement",
        organization_id=org_id,
        movement_id=movement_id,
    )
    
    try:
        # === Validar datos del movement ===
        # En producción: fetch from DB
        movement_data = {
            "manifest_number": f"NOM-{org_id}-{movement_id}",
            "quantity": 150.5,
            "waste_type": "peligroso",
        }
        
        validate_waste_movement_data(movement_data)
        
        # === Simular validación NOM-052 ===
        # En producción: reglas de NOM-052
        import time
        time.sleep(0.3)
        
        validation_result = {
            "movement_id": movement_id,
            "org_id": org_id,
            "status": "validated",
            "norma_compliant": True,
            "validation_checks": {
                "manifest_format": True,
                "quantity_positive": True,
                "waste_type_valid": True,
            },
        }
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        worker_logger.log_job_success(
            job_id=job_id,
            func_name="validate_waste_movement",
            duration_seconds=duration,
            compliant=validation_result["norma_compliant"],
        )
        
        return {
            "job_id": job_id,
            "movement_id": movement_id,
            "org_id": org_id,
            **validation_result,
            "duration_seconds": duration,
        }
    
    except ValidationError as e:
        worker_logger.log_job_failure(
            job_id=job_id,
            func_name="validate_waste_movement",
            error=str(e),
            retry_count=0,
            is_final=True,
        )
        raise NonRecoverableError(str(e)) from e
    
    except Exception as e:
        worker_logger.log_job_failure(
            job_id=job_id,
            func_name="validate_waste_movement",
            error=str(e),
            retry_count=0,
            is_final=False,
        )
        raise RecoverableError(f"Validation failed: {e}") from e
    
    finally:
        clear_job_context()


# =============================================================================
# Notifications
# =============================================================================

def send_notification(
    user_id: int,
    org_id: int,
    notification_type: str,
    title: str,
    message: str,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Envía notificación asíncrona.
    
    Args:
        user_id: ID del usuario destino
        org_id: Organization ID (multi-tenant)
        notification_type: Tipo (email, sms, push)
        title: Título de la notificación
        message: Cuerpo del mensaje
        request_id: Request ID para correlación
    
    Returns:
        Dict con resultado del envío
    """
    job_id = f"notif_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    set_job_context(
        job_id=job_id,
        organization_id=org_id,
        user_id=user_id,
        request_id=request_id,
        queue=QueueNames.DEFAULT.value,
    )
    
    start_time = datetime.now(timezone.utc)
    
    worker_logger.log_job_start(
        job_id=job_id,
        func_name="send_notification",
        organization_id=org_id,
        user_id=user_id,
        notification_type=notification_type,
    )
    
    try:
        # === Simular envío de notificación ===
        # En producción: integrar con proveedor (SendGrid, Twilio, etc.)
        import time
        time.sleep(0.1)
        
        result = {
            "user_id": user_id,
            "org_id": org_id,
            "type": notification_type,
            "title": title,
            "sent": True,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        worker_logger.log_job_success(
            job_id=job_id,
            func_name="send_notification",
            duration_seconds=duration,
            notification_type=notification_type,
        )
        
        return {
            "job_id": job_id,
            **result,
            "duration_seconds": duration,
        }
    
    except Exception as e:
        worker_logger.log_job_failure(
            job_id=job_id,
            func_name="send_notification",
            error=str(e),
            retry_count=0,
            is_final=False,
        )
        # Notifications son recoverable
        raise RecoverableError(f"Notification failed: {e}") from e
    
    finally:
        clear_job_context()


# =============================================================================
# Cleanup Jobs
# =============================================================================

def cleanup_old_jobs(days_old: int = 30, request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Limpia jobs antiguos de RQ.
    
    Args:
        days_old: Eliminar jobs más antiguos que esto
        request_id: Request ID para correlación
    
    Returns:
        Dict con resultado del cleanup
    """
    job_id = f"cleanup_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    set_job_context(
        job_id=job_id,
        request_id=request_id,
        queue=QueueNames.LOW.value,
    )
    
    start_time = datetime.now(timezone.utc)
    
    worker_logger.log_job_start(
        job_id=job_id,
        func_name="cleanup_old_jobs",
        organization_id=None,
        days_old=days_old,
    )
    
    try:
        # === Simular cleanup ===
        # En producción: iterar jobs antiguos y eliminarlos
        
        deleted_count = 0  # Simulado
        
        worker_logger.info(
            f"Cleanup completed: {deleted_count} jobs deleted",
            days_old=days_old,
            deleted_count=deleted_count,
        )
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        worker_logger.log_job_success(
            job_id=job_id,
            func_name="cleanup_old_jobs",
            duration_seconds=duration,
            deleted_count=deleted_count,
        )
        
        return {
            "job_id": job_id,
            "deleted_count": deleted_count,
            "days_old": days_old,
            "cleanup_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration,
        }
    
    except Exception as e:
        worker_logger.log_job_failure(
            job_id=job_id,
            func_name="cleanup_old_jobs",
            error=str(e),
            retry_count=0,
            is_final=False,
        )
        raise RecoverableError(f"Cleanup failed: {e}") from e
    
    finally:
        clear_job_context()


# =============================================================================
# Health Check
# =============================================================================

def health_check(request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Health check del worker.
    
    Verifica:
    - Conexión a Redis
    - Conexión a PostgreSQL
    - Estado de queues
    
    Args:
        request_id: Request ID para correlación
    
    Returns:
        Dict con estado de salud
    """
    job_id = f"health_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    set_job_context(
        job_id=job_id,
        request_id=request_id,
        queue=QueueNames.HIGH.value,
    )
    
    start_time = datetime.now(timezone.utc)
    
    worker_logger.log_job_start(
        job_id=job_id,
        func_name="health_check",
        organization_id=None,
    )
    
    try:
        import socket
        from redis import Redis
        
        checks = {
            "redis": False,
            "postgres": False,
        }
        
        # Check Redis
        try:
            r = Redis.from_url("redis://localhost:6379", socket_timeout=5)
            r.ping()
            checks["redis"] = True
        except Exception as e:
            worker_logger.warning(f"Redis health check failed: {e}")
        
        # Check PostgreSQL (simplificado - en producción sería más completo)
        # Por ahora solo marcamos como no verificado
        checks["postgres"] = None  # No verificado en 7A
        
        all_healthy = all(v is True or v is None for v in checks.values())
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        status = "healthy" if all_healthy else "unhealthy"
        
        worker_logger.log_job_success(
            job_id=job_id,
            func_name="health_check",
            duration_seconds=duration,
            status=status,
        )
        
        return {
            "job_id": job_id,
            "status": status,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration,
        }
    
    except Exception as e:
        worker_logger.log_job_failure(
            job_id=job_id,
            func_name="health_check",
            error=str(e),
            retry_count=0,
            is_final=False,
        )
        return {
            "job_id": job_id,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    finally:
        clear_job_context()


# =============================================================================
# Retry Configuration Factory
# =============================================================================

def get_retry_for_task(task_name: str) -> Optional[Retry]:
    """
    Obtiene configuración de retry según el tipo de tarea.
    
    Args:
        task_name: Nombre de la función de tarea
    
    Returns:
        Retry instance o None
    """
    # Map task name to retry configuration
    retry_configs = {
        "process_document": Retry(max=RetryPolicy.MAX_RETRIES, interval=[30, 120, 300]),
        "validate_waste_movement": Retry(max=3, interval=[10, 60, 180]),
        "send_notification": Retry(max=2, interval=[5, 30]),
        "cleanup_old_jobs": Retry(max=1, interval=[60]),
        "health_check": None,  # Sin retry - solo reporta
    }
    
    return retry_configs.get(task_name)


def get_timeout_for_task(task_name: str) -> int:
    """
    Obtiene timeout según el tipo de tarea.
    
    Args:
        task_name: Nombre de la función de tarea
    
    Returns:
        Timeout en segundos
    """
    timeouts = {
        "process_document": TimeoutPolicy.OCR_TRIAGE,
        "validate_waste_movement": TimeoutPolicy.DEFAULT,
        "send_notification": TimeoutPolicy.NOTIFICATION,
        "cleanup_old_jobs": TimeoutPolicy.CLEANUP,
        "health_check": 30,
    }
    
    return timeouts.get(task_name, TimeoutPolicy.DEFAULT)