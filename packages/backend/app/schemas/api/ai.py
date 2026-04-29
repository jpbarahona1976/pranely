"""
AI/DeepInfra API schemas.

Schemas para integración con servicios de IA (OCR, LLM) via DeepInfra.
Incluye validación de requests/responses y manejo de errores específicos de IA.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# Enums para tipos de documentos y estados
# =============================================================================

class DocumentType(str, Enum):
    """Tipos de documento detectados por OCR."""
    WASTE_MANIFEST = "waste_manifest"
    TRANSPORT_MANIFEST = "transport_manifest"
    RECEIPT = "receipt"
    INVOICE = "invoice"
    CERTIFICATE = "certificate"
    ID_CARD = "id_card"
    UNKNOWN = "unknown"


class ProcessingStatus(str, Enum):
    """Estados de procesamiento de documento."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class AIProvider(str, Enum):
    """Proveedores de IA disponibles."""
    DEEPINFRA = "deepinfra"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


# =============================================================================
# Request Schemas - Envío a DeepInfra
# =============================================================================

class OCRRequest(BaseModel):
    """Request para OCR de documento."""
    model_config = ConfigDict(extra="forbid")
    
    document_id: int = Field(..., description="ID del documento en BD")
    org_id: int = Field(..., description="ID de organización (tenant)")
    user_id: int = Field(..., description="ID de usuario que subió")
    file_url: str = Field(..., description="URL o path al archivo")
    file_type: Literal["pdf", "image", "jpg", "png", "tiff"] = Field(
        ..., description="Tipo MIME o extensión del archivo"
    )
    expected_document_type: Optional[DocumentType] = Field(
        default=None, description="Tipo esperado (para asistencia de IA)"
    )
    extract_metadata: bool = Field(
        default=True, description="Extraer metadatos adicionales"
    )
    language_hint: Optional[str] = Field(
        default="es", description="Código ISO de idioma principal"
    )

    @field_validator("file_url")
    @classmethod
    def validate_file_url(cls, v: str) -> str:
        """Valida que la URL sea accesible o sea un path local válido."""
        if not v or len(v) < 3:
            raise ValueError("URL o path inválido")
        return v


class LLMRequest(BaseModel):
    """Request para generación con LLM."""
    model_config = ConfigDict(extra="forbid")
    
    model: str = Field(
        default="deepinfra/NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO",
        description="Modelo a usar (formato: provider/model-name)"
    )
    messages: List[Dict[str, str]] = Field(
        ..., description="Mensajes en formato ChatML"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0,
        description="Temperatura de sampling (0=determinista, 2=máxima creatividad)"
    )
    max_tokens: int = Field(
        default=1024, ge=1, le=8192,
        description="Máximo de tokens a generar"
    )
    stream: bool = Field(
        default=False, description="Habilitar streaming de respuesta"
    )
    stop: Optional[List[str]] = Field(
        default=None, description="Secuencias de stop"
    )


class EmbeddingsRequest(BaseModel):
    """Request para generación de embeddings."""
    model_config = ConfigDict(extra="forbid")
    
    model: str = Field(
        default="deepinfra/nextml/Nomic-Embed-Text-v1.5",
        description="Modelo de embeddings"
    )
    texts: List[str] = Field(
        ..., min_length=1, max_length=100,
        description="Textos a convertir en embeddings (máx 100)"
    )
    truncate: bool = Field(
        default=True, description="Truncar textos que excedan el límite"
    )


# =============================================================================
# Response Schemas - Respuestas de DeepInfra
# =============================================================================

class ExtractedField(BaseModel):
    """Campo individual extraído de un documento."""
    name: str = Field(..., description="Nombre del campo")
    value: Any = Field(..., description="Valor extraído")
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confianza de la extracción (0-1)"
    )
    location: Optional[Dict[str, int]] = Field(
        default=None,
        description="Ubicación en imagen (bounding box): {x, y, width, height}"
    )


class OCRResponse(BaseModel):
    """Response de OCR procesado."""
    document_id: int = Field(..., description="ID del documento procesado")
    job_id: str = Field(..., description="ID del job de IA")
    status: ProcessingStatus = Field(..., description="Estado del procesamiento")
    
    # Contenido extraído
    text_extracted: str = Field(..., description="Texto completo extraído")
    detected_type: DocumentType = Field(..., description="Tipo de documento detectado")
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confianza general del OCR"
    )
    
    # Campos estructurados
    fields: List[ExtractedField] = Field(
        default_factory=list,
        description="Campos estructurados extraídos"
    )
    raw_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Datos crudos del proveedor de IA"
    )
    
    # Metadatos
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp de procesamiento"
    )
    processing_time_ms: Optional[int] = Field(
        default=None, ge=0,
        description="Tiempo de procesamiento en milisegundos"
    )
    
    # Waste manifest específico
    is_waste_manifest: bool = Field(
        default=False,
        description="Indica si el documento es un manifiesto de residuos"
    )
    manifest_number: Optional[str] = Field(
        default=None,
        description="Número de manifiesto (si aplica)"
    )


class LLMResponse(BaseModel):
    """Response de LLM."""
    model: str = Field(..., description="Modelo utilizado")
    created: int = Field(..., description="Timestamp Unix de creación")
    
    # Contenido
    content: str = Field(..., description="Contenido generado")
    finish_reason: Optional[str] = Field(
        default=None,
        description="Razón de finalización (stop, length, content_filter)"
    )
    
    # Usage
    usage: Dict[str, int] = Field(
        default_factory=dict,
        description="Uso de tokens: {prompt, completion, total}"
    )
    
    # Metadata
    job_id: str = Field(..., description="ID del job de IA")
    provider: AIProvider = Field(default=AIProvider.DEEPINFRA)


class EmbeddingsResponse(BaseModel):
    """Response de embeddings."""
    model: str = Field(..., description="Modelo utilizado")
    embeddings: List[List[float]] = Field(
        ..., description="Vectores de embedding (cada uno es un array de floats)"
    )
    truncated: Optional[List[int]] = Field(
        default=None,
        description="Índices de textos que fueron truncados"
    )
    job_id: str = Field(..., description="ID del job de IA")


# =============================================================================
# Error Schemas - Manejo de errores de IA
# =============================================================================

class AIErrorCode(str, Enum):
    """Códigos de error específicos de IA."""
    TIMEOUT = "ai_timeout"
    RATE_LIMIT = "ai_rate_limit"
    MODEL_UNAVAILABLE = "ai_model_unavailable"
    INVALID_REQUEST = "ai_invalid_request"
    CONTENT_FILTERED = "ai_content_filtered"
    SERVICE_UNAVAILABLE = "ai_service_unavailable"
    QUOTA_EXCEEDED = "ai_quota_exceeded"
    INVALID_RESPONSE = "ai_invalid_response"


class AIErrorResponse(BaseModel):
    """Error response específico para IA."""
    error_code: AIErrorCode = Field(..., description="Código de error")
    message: str = Field(..., description="Descripción del error")
    provider: AIProvider = Field(default=AIProvider.DEEPINFRA)
    retry_after: Optional[int] = Field(
        default=None, ge=0,
        description="Segundos para esperar antes de reintentar"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="ID de request para debugging"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp del error"
    )


class AIHealthResponse(BaseModel):
    """Health check de servicios de IA."""
    provider: AIProvider = Field(..., description="Proveedor")
    status: Literal["healthy", "degraded", "unavailable"] = Field(
        ..., description="Estado del servicio"
    )
    latency_ms: Optional[float] = Field(
        default=None, ge=0,
        description="Latencia promedio en ms"
    )
    rate_limit_remaining: Optional[int] = Field(
        default=None, ge=0,
        description="Requests restantes en ventana actual"
    )
    models_available: List[str] = Field(
        default_factory=list,
        description="Lista de modelos disponibles"
    )
    checked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp del health check"
    )


# =============================================================================
# Internal Processing Schemas
# =============================================================================

class AIJobRecord(BaseModel):
    """Registro interno de job de IA (para BD)."""
    job_id: str = Field(..., description="ID único del job")
    document_id: Optional[int] = Field(default=None, description="ID de documento")
    org_id: int = Field(..., description="ID de organización")
    user_id: int = Field(..., description="ID de usuario")
    
    # Tipo y estado
    job_type: Literal["ocr", "llm", "embeddings"] = Field(
        ..., description="Tipo de job"
    )
    status: ProcessingStatus = Field(..., description="Estado actual")
    provider: AIProvider = Field(default=AIProvider.DEEPINFRA)
    model_used: Optional[str] = Field(default=None, description="Modelo utilizado")
    
    # Request/Response
    request_data: Dict[str, Any] = Field(
        default_factory=dict, description="Datos del request"
    )
    response_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Datos de respuesta"
    )
    error_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Datos de error si falló"
    )
    
    # Métricas
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Confianza del resultado"
    )
    processing_time_ms: Optional[int] = Field(
        default=None, ge=0,
        description="Tiempo de procesamiento"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Cuando se creó el job"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="Cuando empezó el procesamiento"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Cuando completó"
    )
    retry_count: int = Field(default=0, ge=0, description="Número de reintentos")
    max_retries: int = Field(default=3, ge=0, description="Máximo de reintentos")
    
    model_config = ConfigDict(
        ser_json_timedelta="iso8601",
    )
