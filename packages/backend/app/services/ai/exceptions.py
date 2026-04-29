"""
AI Service Exceptions.

Jerarquía de errores específica para servicios de IA.
"""
from typing import Any, Dict, Optional


class AIError(Exception):
    """Base exception para errores de IA."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "ai_error",
        provider: str = "deepinfra",
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.provider = provider
        self.details = details or {}
        self.retry_after = retry_after


class AITimeoutError(AIError):
    """Timeout en request a IA."""
    
    def __init__(
        self,
        message: str = "Request a IA excedió el timeout",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="ai_timeout",
            details=details,
        )


class AIRateLimitError(AIError):
    """Rate limit excedido."""
    
    def __init__(
        self,
        message: str = "Rate limit excedido",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="ai_rate_limit",
            retry_after=retry_after,
            details=details,
        )


class AIModelUnavailableError(AIError):
    """Modelo no disponible."""
    
    def __init__(
        self,
        model: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"Modelo no disponible: {model}",
            error_code="ai_model_unavailable",
            details={"model": model, **(details or {})},
        )


class AIQuotaExceededError(AIError):
    """Cuota de uso excedida."""
    
    def __init__(
        self,
        message: str = "Cuota de uso excedida",
        quota_type: str = "monthly",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="ai_quota_exceeded",
            details={"quota_type": quota_type, **(details or {})},
        )


class AIInvalidRequestError(AIError):
    """Request inválido a IA."""
    
    def __init__(
        self,
        message: str,
        validation_errors: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="ai_invalid_request",
            details={
                "validation_errors": validation_errors,
                **(details or {}),
            },
        )


class AIResponseError(AIError):
    """Error procesando response de IA."""
    
    def __init__(
        self,
        message: str,
        raw_response: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="ai_invalid_response",
            details={
                "has_raw_response": raw_response is not None,
                **(details or {}),
            },
        )
        self.raw_response = raw_response


class AIServiceUnavailableError(AIError):
    """Servicio de IA no disponible."""
    
    def __init__(
        self,
        message: str = "Servicio de IA temporalmente no disponible",
        provider: str = "deepinfra",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="ai_service_unavailable",
            provider=provider,
            details=details,
        )


class AINotConfiguredError(AIError):
    """Servicio de IA no configurado."""
    
    def __init__(
        self,
        feature: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=f"Feature de IA no configurada: {feature}",
            error_code="ai_not_configured",
            details={"feature": feature, **(details or {})},
        )
