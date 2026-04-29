"""
AI Configuration for DeepInfra services.

Configuración centralizada para todos los servicios de IA.
Lee de variables de entorno con validación y defaults seguros.
"""
import os
from functools import lru_cache
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class DeepInfraConfig(BaseModel):
    """Configuración específica de DeepInfra."""
    api_base: str = Field(
        default="https://api.deepinfra.com/v1",
        description="Base URL de la API"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key (opcional - algunas APIs son gratuitas)"
    )
    timeout: int = Field(
        default=120, ge=10, le=300,
        description="Timeout en segundos"
    )
    max_retries: int = Field(
        default=3, ge=0, le=10,
        description="Máximo de reintentos"
    )
    retry_delay: int = Field(
        default=5, ge=1, le=60,
        description="Delay base entre reintentos en segundos"
    )
    
    @field_validator("api_key", mode="after")
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Valida que la API key no esté vacía si se proporciona."""
        if v is not None and len(v.strip()) == 0:
            return None
        return v


class AIConfig(BaseModel):
    """Configuración global de IA."""
    
    # === DeepInfra ===
    deepinfra: DeepInfraConfig = Field(default_factory=DeepInfraConfig)
    
    # === Model defaults ===
    default_ocr_model: str = Field(
        default="ocr",
        description="Modelo default para OCR"
    )
    default_llm_model: str = Field(
        default="deepinfra/NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO",
        description="Modelo LLM default"
    )
    default_embeddings_model: str = Field(
        default="deepinfra/nextml/Nomic-Embed-Text-v1.5",
        description="Modelo de embeddings default"
    )
    
    # === Rate limits ===
    requests_per_minute: int = Field(
        default=60, ge=1,
        description="Límite de requests por minuto"
    )
    requests_per_day: int = Field(
        default=10000, ge=1,
        description="Límite diario de requests"
    )
    
    # === Feature flags ===
    enable_ocr: bool = Field(
        default=True,
        description="Habilitar procesamiento OCR"
    )
    enable_llm: bool = Field(
        default=True,
        description="Habilitar LLM"
    )
    enable_embeddings: bool = Field(
        default=True,
        description="Habilitar embeddings"
    )
    
    # === Cost control ===
    max_cost_per_month_usd: float = Field(
        default=100.0, ge=0,
        description="Presupuesto máximo mensual en USD"
    )
    cost_alert_threshold: float = Field(
        default=0.8, ge=0, le=1,
        description="Umbral de alerta de costo (% del presupuesto)"
    )
    
    # === Model catalog ===
    available_models: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "ocr": ["ocr", "easyocr"],
            "llm": [
                "deepinfra/NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO",
                "deepinfra/meta-llama/Llama-3-70B-Instruct",
                "deepinfra/mistralai/Mixtral-8x22B-Instruct-v0.1",
            ],
            "embeddings": [
                "deepinfra/nextml/Nomic-Embed-Text-v1.5",
                "deepinfra/BAAI/bge-base-en-v1.5",
            ],
        },
        description="Catálogo de modelos disponibles"
    )
    
    # === Logging ===
    log_requests: bool = Field(
        default=False,
        description="Loguear requests a IA (puede contener PII)"
    )
    log_responses: bool = Field(
        default=False,
        description="Loguear responses de IA (puede contener datos sensibles)"
    )


def _load_from_env() -> AIConfig:
    """
    Carga configuración desde variables de entorno.
    
    Variables soportadas:
    - DEEPINFRA_API_KEY: API key para DeepInfra
    - DEEPINFRA_API_BASE: Base URL custom
    - DEEPINFRA_TIMEOUT: Timeout en segundos
    - AI_DEFAULT_LLM_MODEL: Modelo LLM default
    - AI_RATE_LIMIT_PER_MINUTE: Límite por minuto
    - AI_MAX_MONTHLY_COST: Presupuesto máximo mensual
    """
    deepinfra_config = DeepInfraConfig(
        api_key=os.environ.get("DEEPINFRA_API_KEY"),
        api_base=os.environ.get(
            "DEEPINFRA_API_BASE",
            "https://api.deepinfra.com/v1"
        ),
        timeout=int(os.environ.get("DEEPINFRA_TIMEOUT", "120")),
        max_retries=int(os.environ.get("DEEPINFRA_MAX_RETRIES", "3")),
        retry_delay=int(os.environ.get("DEEPINFRA_RETRY_DELAY", "5")),
    )
    
    return AIConfig(
        deepinfra=deepinfra_config,
        default_llm_model=os.environ.get(
            "AI_DEFAULT_LLM_MODEL",
            "deepinfra/NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO"
        ),
        default_embeddings_model=os.environ.get(
            "AI_DEFAULT_EMBEDDINGS_MODEL",
            "deepinfra/nextml/Nomic-Embed-Text-v1.5"
        ),
        requests_per_minute=int(os.environ.get("AI_RATE_LIMIT_PER_MINUTE", "60")),
        max_cost_per_month_usd=float(os.environ.get("AI_MAX_MONTHLY_COST", "100.0")),
        enable_ocr=os.environ.get("AI_ENABLE_OCR", "true").lower() == "true",
        enable_llm=os.environ.get("AI_ENABLE_LLM", "true").lower() == "true",
        enable_embeddings=os.environ.get("AI_ENABLE_EMBEDDINGS", "true").lower() == "true",
        log_requests=os.environ.get("AI_LOG_REQUESTS", "false").lower() == "true",
        log_responses=os.environ.get("AI_LOG_RESPONSES", "false").lower() == "true",
    )


@lru_cache(maxsize=1)
def get_ai_config() -> AIConfig:
    """
    Obtiene configuración de IA singleton.
    
    Returns:
        AIConfig instance (cached)
    """
    return _load_from_env()
