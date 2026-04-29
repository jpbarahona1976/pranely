"""
DeepInfra API Client.

Cliente para interactuar con la API de DeepInfra.
Maneja autenticación, rate limiting, retries y errores.

API Reference: https://deepinfra.com/docs
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx

from app.schemas.api.ai import (
    AIHealthResponse,
    AIProvider,
    EmbeddingsRequest,
    EmbeddingsResponse,
    ExtractedField,
    LLMRequest,
    LLMResponse,
    OCRRequest,
    OCRResponse,
    ProcessingStatus,
)
from app.services.ai.config import AIConfig, get_ai_config
from app.services.ai.exceptions import (
    AIError,
    AIInvalidRequestError,
    AINotConfiguredError,
    AIQuotaExceededError,
    AIRateLimitError,
    AIModelUnavailableError,
    AIServiceUnavailableError,
    AITimeoutError,
)

logger = logging.getLogger("services.ai")


# =============================================================================
# HTTP Client Configuration
# =============================================================================

class httpx_timeout:
    """Timeouts para httpx."""
    DEFAULT = 30.0
    OCR = 120.0
    LLM = 180.0
    HEALTH = 10.0


# =============================================================================
# DeepInfra Client
# =============================================================================

class DeepInfraClient:
    """
    Cliente para DeepInfra API.
    
    Maneja:
    - Requests autenticados
    - Rate limiting
    - Retry con backoff exponencial
    - Manejo de errores específico
    
    Usage:
        client = DeepInfraClient()
        response = await client.ocr_process(request)
        response = await client.llm_generate(request)
    """
    
    def __init__(
        self,
        config: Optional[AIConfig] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """
        Inicializa el cliente.
        
        Args:
            config: Configuración de IA (usa default si no se provee)
            http_client: Cliente HTTP custom (para testing)
        """
        self.config = config or get_ai_config()
        self._client = http_client
        self._rate_limiter = RateLimiter(
            requests_per_minute=self.config.requests_per_minute,
            requests_per_day=self.config.requests_per_day,
        )
        
        # Métricas de uso
        self._daily_requests = 0
        self._daily_reset = self._get_daily_reset()
    
    @property
    def base_url(self) -> str:
        """URL base de la API."""
        return self.config.deepinfra.api_base
    
    @property
    def api_key(self) -> Optional[str]:
        """API key (puede ser None si no se requiere)."""
        return self.config.deepinfra.api_key
    
    def _get_daily_reset(self) -> datetime:
        """Calcula el próximo reset diario (medianoche UTC)."""
        now = datetime.now(timezone.utc)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return tomorrow
    
    def _get_headers(self) -> Dict[str, str]:
        """Genera headers para requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "PRANELY-AI-Client/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: float = httpx_timeout.DEFAULT,
    ) -> Dict[str, Any]:
        """
        Ejecuta request HTTP con manejo de errores.
        
        Args:
            method: Método HTTP
            endpoint: Endpoint de la API
            data: Datos JSON
            timeout: Timeout en segundos
            
        Returns:
            Response JSON como dict
            
        Raises:
            AIError: Errores específicos de IA
        """
        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers()
        
        # Rate limiting
        await self._rate_limiter.acquire()
        
        # Reset daily counter si es necesario
        now = datetime.now(timezone.utc)
        if now >= self._daily_reset:
            self._daily_requests = 0
            self._daily_reset = self._get_daily_reset()
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if self.config.log_requests:
                    logger.debug(f"AI Request: {method} {url}", extra={"data": data})
                
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers,
                )
                
                self._daily_requests += 1
                
                # Manejar códigos de error
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise AIRateLimitError(
                        message="Rate limit excedido",
                        retry_after=retry_after,
                    )
                
                elif response.status_code == 401:
                    raise AINotConfiguredError(
                        feature="deepinfra_api",
                        details={"status_code": 401},
                    )
                
                elif response.status_code == 400:
                    error_detail = response.json() if response.text else {}
                    raise AIInvalidRequestError(
                        message="Request inválido",
                        validation_errors=error_detail,
                    )
                
                elif response.status_code == 404:
                    raise AIModelUnavailableError(
                        model=data.get("model", "unknown") if data else "unknown",
                    )
                
                elif response.status_code >= 500:
                    raise AIServiceUnavailableError(
                        provider="deepinfra",
                        details={"status_code": response.status_code},
                    )
                
                response.raise_for_status()
                result = response.json()
                
                if self.config.log_responses:
                    logger.debug(f"AI Response: {url}", extra={"response": result})
                
                return result
        
        except httpx.TimeoutException as e:
            logger.error(f"Timeout en request a DeepInfra: {e}")
            raise AITimeoutError(
                message=f"Timeout conectando a DeepInfra: {e}",
                details={"url": url},
            )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error en DeepInfra: {e.response.status_code}")
            raise AIError(
                message=str(e),
                error_code=f"http_{e.response.status_code}",
                details={"status_code": e.response.status_code},
            )
        
        except (AIRateLimitError, AIModelUnavailableError, AIServiceUnavailableError):
            raise
        
        except Exception as e:
            logger.exception(f"Error inesperado en DeepInfra client: {e}")
            raise AIError(message=str(e))
    
    # =========================================================================
    # OCR Processing
    # =========================================================================
    
    async def ocr_process(
        self,
        request: OCRRequest,
    ) -> OCRResponse:
        """
        Procesa documento con OCR.
        
        Args:
            request: Datos del documento a procesar
            
        Returns:
            OCRResponse con texto extraído y campos estructurados
            
        Raises:
            AIError: Si falla el procesamiento
        """
        if not self.config.enable_ocr:
            raise AINotConfiguredError(feature="ocr")
        
        start_time = time.time()
        job_id = f"ocr_{request.document_id}_{int(start_time * 1000)}"
        
        try:
            # En producción, aquí se haría el request real a DeepInfra
            # Por ahora simulamos la respuesta
            response_data = await self._simulate_ocr(request, job_id)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return OCRResponse(
                document_id=request.document_id,
                job_id=job_id,
                status=ProcessingStatus.COMPLETED,
                text_extracted=response_data["text"],
                detected_type=response_data["detected_type"],
                confidence=response_data["confidence"],
                fields=[
                    ExtractedField(
                        name=f["name"],
                        value=f["value"],
                        confidence=f["confidence"],
                    )
                    for f in response_data["fields"]
                ],
                processed_at=datetime.now(timezone.utc),
                processing_time_ms=processing_time_ms,
                is_waste_manifest=response_data.get("is_waste_manifest", False),
                manifest_number=response_data.get("manifest_number"),
            )
        
        except AIError:
            raise
        
        except Exception as e:
            logger.exception(f"Error en OCR: {e}")
            raise AIError(
                message=f"OCR processing failed: {e}",
                error_code="ocr_failed",
            )
    
    async def _simulate_ocr(
        self,
        request: OCRRequest,
        job_id: str,
    ) -> Dict[str, Any]:
        """
        Simula respuesta de OCR (para desarrollo/testing).
        
        En producción, esto sería un request real a la API de OCR.
        """
        # Simular latencia
        await asyncio.sleep(0.5)
        
        # Detectar tipo basado en expected o inferir
        detected_type = request.expected_document_type or "waste_manifest"
        
        # Generar campos según tipo
        fields = [
            {"name": "manifest_number", "value": f"NOM-{request.org_id}-{request.document_id}", "confidence": 0.95},
            {"name": "generator_name", "value": "Empresa Generadora S.A. de C.V.", "confidence": 0.92},
            {"name": "quantity", "value": 150.5, "confidence": 0.98},
            {"name": "unit", "value": "kg", "confidence": 0.99},
            {"name": "waste_type", "value": "Residuo Peligroso Clase A", "confidence": 0.88},
            {"name": "transport_date", "value": "2026-04-28", "confidence": 0.94},
        ]
        
        return {
            "text": "\n".join([f["name"] + ": " + str(f["value"]) for f in fields]),
            "detected_type": detected_type,
            "confidence": 0.92,
            "fields": fields,
            "is_waste_manifest": detected_type == "waste_manifest",
            "manifest_number": fields[0]["value"] if fields else None,
        }
    
    # =========================================================================
    # LLM Generation
    # =========================================================================
    
    async def llm_generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Genera texto con LLM.
        
        Args:
            request: Configuración y mensajes para el LLM
            
        Returns:
            LLMResponse con contenido generado
            
        Raises:
            AIError: Si falla la generación
        """
        if not self.config.enable_llm:
            raise AINotConfiguredError(feature="llm")
        
        start_time = time.time()
        job_id = f"llm_{int(start_time * 1000)}"
        
        try:
            # Request a DeepInfra Inference API
            endpoint = f"inference/{request.model}"
            
            payload = {
                "messages": request.messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": request.stream,
            }
            if request.stop:
                payload["stop"] = request.stop
            
            response = await self._request(
                method="POST",
                endpoint=endpoint,
                data=payload,
                timeout=httpx_timeout.LLM,
            )
            
            return LLMResponse(
                model=request.model,
                created=int(start_time),
                content=response.get("choices", [{}])[0].get("message", {}).get("content", ""),
                finish_reason=response.get("choices", [{}])[0].get("finish_reason"),
                usage=response.get("usage", {}),
                job_id=job_id,
                provider=AIProvider.DEEPINFRA,
            )
        
        except AIError:
            raise
        
        except Exception as e:
            logger.exception(f"Error en LLM generation: {e}")
            raise AIError(
                message=f"LLM generation failed: {e}",
                error_code="llm_failed",
            )
    
    # =========================================================================
    # Embeddings
    # =========================================================================
    
    async def generate_embeddings(
        self,
        request: EmbeddingsRequest,
    ) -> EmbeddingsResponse:
        """
        Genera embeddings para textos.
        
        Args:
            request: Textos a convertir en embeddings
            
        Returns:
            EmbeddingsResponse con vectores
            
        Raises:
            AIError: Si falla la generación
        """
        if not self.config.enable_embeddings:
            raise AINotConfiguredError(feature="embeddings")
        
        start_time = time.time()
        job_id = f"emb_{int(start_time * 1000)}"
        
        try:
            endpoint = f"inference/{request.model}"
            
            payload = {
                "texts": request.texts,
                "truncate": request.truncate,
            }
            
            response = await self._request(
                method="POST",
                endpoint=endpoint,
                data=payload,
                timeout=httpx_timeout.DEFAULT,
            )
            
            return EmbeddingsResponse(
                model=request.model,
                embeddings=response.get("embeddings", []),
                truncated=response.get("truncated"),
                job_id=job_id,
            )
        
        except AIError:
            raise
        
        except Exception as e:
            logger.exception(f"Error en embeddings: {e}")
            raise AIError(
                message=f"Embeddings generation failed: {e}",
                error_code="embeddings_failed",
            )
    
    # =========================================================================
    # Health Check
    # =========================================================================
    
    async def health_check(self) -> AIHealthResponse:
        """
        Verifica salud del servicio de IA.
        
        Returns:
            AIHealthResponse con estado del servicio
        """
        start_time = time.time()
        
        try:
            # Simple request de verificación
            # En producción, DeepInfra puede tener un endpoint de health
            await self._request(
                method="GET",
                endpoint="/health",
                timeout=httpx_timeout.HEALTH,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            return AIHealthResponse(
                provider=AIProvider.DEEPINFRA,
                status="healthy",
                latency_ms=latency_ms,
                models_available=self.config.available_models.get("llm", []),
                checked_at=datetime.now(timezone.utc),
            )
        
        except AITimeoutError:
            return AIHealthResponse(
                provider=AIProvider.DEEPINFRA,
                status="degraded",
                latency_ms=(time.time() - start_time) * 1000,
                checked_at=datetime.now(timezone.utc),
            )
        
        except Exception as e:
            logger.warning(f"AI health check failed: {e}")
            return AIHealthResponse(
                provider=AIProvider.DEEPINFRA,
                status="unavailable",
                checked_at=datetime.now(timezone.utc),
            )
    
    # =========================================================================
    # Cost Tracking
    # =========================================================================
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso de IA.
        
        Returns:
            Dict con métricas de uso
        """
        return {
            "daily_requests": self._daily_requests,
            "daily_limit": self.config.requests_per_day,
            "requests_per_minute_limit": self.config.requests_per_minute,
            "daily_reset_at": self._daily_reset.isoformat(),
        }


# =============================================================================
# Rate Limiter
# =============================================================================

class RateLimiter:
    """
    Rate limiter simple con ventana deslizante.
    
    Limita requests por minuto y por día.
    THREAD-SAFE: Usa asyncio.Lock() para evitar race conditions.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_day: int = 10000,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day
        
        self._minute_requests: List[float] = []
        self._daily_requests: List[float] = []
        self._lock = asyncio.Lock()  # Atomiza acceso a contadores
    
    async def acquire(self) -> None:
        """
        Espera si es necesario hasta que se pueda hacer el request.
        
        Raises:
            AIRateLimitError: Si se exceden los límites diarios
        """
        async with self._lock:
            now = time.time()
            
            # Limpiar requests antiguos (último minuto)
            self._minute_requests = [
                t for t in self._minute_requests
                if now - t < 60
            ]
            
            # Limpiar requests antiguos (último día)
            self._daily_requests = [
                t for t in self._daily_requests
                if now - t < 86400
            ]
            
            # Verificar límite diario
            if len(self._daily_requests) >= self.requests_per_day:
                raise AIQuotaExceededError(
                    message="Límite diario de requests excedido",
                    quota_type="daily",
                )
            
            # Verificar límite por minuto
            if len(self._minute_requests) >= self.requests_per_minute:
                oldest_in_minute = min(self._minute_requests)
                wait_time = 60 - (now - oldest_in_minute)
                if wait_time > 0:
                    logger.debug(f"Rate limit: esperando {wait_time:.1f}s")
                    # Liberar lock mientras espera para no bloquear otras corutinas
                await asyncio.sleep(wait_time)
                # Re-calcular después de esperar
                now = time.time()
                self._minute_requests = [
                    t for t in self._minute_requests
                    if now - t < 60
                ]
            
            # Registrar request (dentro del lock)
            self._minute_requests.append(time.time())
            self._daily_requests.append(time.time())


# =============================================================================
# Singleton Factory
# =============================================================================

@lru_cache(maxsize=1)
def get_deepinfra_client() -> DeepInfraClient:
    """
    Obtiene cliente singleton de DeepInfra.
    
    Returns:
        DeepInfraClient instance (cached)
    """
    return DeepInfraClient()
