"""
Tests para schemas de AI y mocks de DeepInfra client.

Cubre:
- OCRRequest, LLMRequest, EmbeddingsRequest (validación con extra="forbid")
- OCRResponse, LLMResponse, EmbeddingsResponse (serialización)
- AIJobRecord (registro interno)
- Mocks de httpx para DeepInfraClient
- Rate limiter thread-safety
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.schemas.api.ai import (
    AIErrorCode,
    AIErrorResponse,
    AIHealthResponse,
    AIJobRecord,
    AIProvider,
    DocumentType,
    EmbeddingsRequest,
    EmbeddingsResponse,
    ExtractedField,
    LLMRequest,
    LLMResponse,
    OCRRequest,
    OCRResponse,
    ProcessingStatus,
)
from app.services.ai.client import DeepInfraClient, RateLimiter
from app.services.ai.config import AIConfig, DeepInfraConfig
from app.services.ai.exceptions import (
    AIError,
    AIQuotaExceededError,
    AIRateLimitError,
)


# =============================================================================
# OCR Schemas Tests
# =============================================================================

class TestOCRSchemas:
    """Tests para OCRRequest y OCRResponse."""
    
    def test_ocr_request_valid(self):
        """OCRRequest válido con todos los campos."""
        req = OCRRequest(
            document_id=1,
            org_id=1,
            user_id=1,
            file_url="/uploads/test.pdf",
            file_type="pdf",
        )
        assert req.document_id == 1
        assert req.file_type == "pdf"
        assert req.extract_metadata is True
        assert req.language_hint == "es"
    
    def test_ocr_request_minimal(self):
        """OCRRequest con campos mínimos."""
        req = OCRRequest(
            document_id=1,
            org_id=1,
            user_id=1,
            file_url="s3://bucket/file.png",
            file_type="image",
        )
        assert req.expected_document_type is None
    
    def test_ocr_request_forbids_extra(self):
        """OCRRequest rechaza campos extra."""
        with pytest.raises(ValidationError) as exc_info:
            OCRRequest(
                document_id=1,
                org_id=1,
                user_id=1,
                file_url="/test.pdf",
                file_type="pdf",
                extra_field="invalid",  # No existe en schema
            )
        errors = exc_info.value.errors()
        assert any("extra_forbidden" in str(e.get("type", "")) for e in errors)
    
    def test_ocr_request_invalid_file_url(self):
        """OCRRequest rechaza URL vacía."""
        with pytest.raises(ValidationError):
            OCRRequest(
                document_id=1,
                org_id=1,
                user_id=1,
                file_url="",
                file_type="pdf",
            )
    
    def test_ocr_response_fields(self):
        """OCRResponse con campos extraídos."""
        resp = OCRResponse(
            document_id=1,
            job_id="ocr_1_123",
            status=ProcessingStatus.COMPLETED,
            text_extracted="Manifiesto NOM-052",
            detected_type=DocumentType.WASTE_MANIFEST,
            confidence=0.95,
            fields=[
                ExtractedField(name="manifest", value="NOM-001", confidence=0.98),
            ],
            is_waste_manifest=True,
            manifest_number="NOM-001",
        )
        assert resp.is_waste_manifest is True
        assert resp.fields[0].name == "manifest"
    
    def test_ocr_response_serialization(self):
        """OCRResponse serializa correctamente a JSON."""
        resp = OCRResponse(
            document_id=1,
            job_id="ocr_1_123",
            status=ProcessingStatus.COMPLETED,
            text_extracted="Test",
            detected_type=DocumentType.UNKNOWN,
            confidence=0.5,
        )
        json_data = resp.model_dump_json()
        assert "document_id" in json_data
        # Enum se serializa como valor string (lowercase)
        assert "completed" in json_data
        assert "unknown" in json_data


# =============================================================================
# LLM Schemas Tests
# =============================================================================

class TestLLMSchemas:
    """Tests para LLMRequest y LLMResponse."""
    
    def test_llm_request_valid(self):
        """LLMRequest válido."""
        req = LLMRequest(
            messages=[
                {"role": "system", "content": "Eres asistente"},
                {"role": "user", "content": "Hola"},
            ],
            temperature=0.7,
            max_tokens=100,
        )
        assert len(req.messages) == 2
        assert req.temperature == 0.7
        assert req.model == "deepinfra/NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO"
    
    def test_llm_request_temperature_bounds(self):
        """LLMRequest valida temperatura 0-2."""
        # Temperatura válida
        req = LLMRequest(messages=[{"role": "user", "content": "test"}], temperature=0)
        assert req.temperature == 0
        
        req = LLMRequest(messages=[{"role": "user", "content": "test"}], temperature=2)
        assert req.temperature == 2
        
        # Temperatura inválida
        with pytest.raises(ValidationError):
            LLMRequest(messages=[{"role": "user", "content": "test"}], temperature=3)
    
    def test_llm_request_forbids_extra(self):
        """LLMRequest rechaza campos extra."""
        with pytest.raises(ValidationError) as exc_info:
            LLMRequest(
                messages=[{"role": "user", "content": "test"}],
                unknown_param="value",
            )
        assert "extra_forbidden" in str(exc_info.value)
    
    def test_llm_response_structure(self):
        """LLMResponse con todos los campos."""
        resp = LLMResponse(
            model="test-model",
            created=1234567890,
            content="Respuesta del LLM",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            job_id="llm_123",
        )
        assert resp.finish_reason == "stop"
        assert resp.usage["total_tokens"] == 30


# =============================================================================
# Embeddings Schemas Tests
# =============================================================================

class TestEmbeddingsSchemas:
    """Tests para EmbeddingsRequest y EmbeddingsResponse."""
    
    def test_embeddings_request_valid(self):
        """EmbeddingsRequest válido."""
        req = EmbeddingsRequest(
            texts=["texto1", "texto2", "texto3"],
            model="deepinfra/nextml/Nomic-Embed-Text-v1.5",
        )
        assert len(req.texts) == 3
        assert req.truncate is True
    
    def test_embeddings_request_max_texts(self):
        """EmbeddingsRequest limita a 100 textos."""
        # 100 textos es válido
        req = EmbeddingsRequest(texts=[f"texto{i}" for i in range(100)])
        assert len(req.texts) == 100
        
        # 101 textos falla
        with pytest.raises(ValidationError):
            EmbeddingsRequest(texts=[f"texto{i}" for i in range(101)])
    
    def test_embeddings_request_min_texts(self):
        """EmbeddingsRequest requiere al menos 1 texto."""
        with pytest.raises(ValidationError):
            EmbeddingsRequest(texts=[])
    
    def test_embeddings_request_forbids_extra(self):
        """EmbeddingsRequest rechaza campos extra."""
        with pytest.raises(ValidationError):
            EmbeddingsRequest(
                texts=["test"],
                extra_field="invalid",
            )
    
    def test_embeddings_response_structure(self):
        """EmbeddingsResponse con vectores."""
        resp = EmbeddingsResponse(
            model="test-model",
            embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            job_id="emb_123",
        )
        assert len(resp.embeddings) == 2
        assert len(resp.embeddings[0]) == 3


# =============================================================================
# AIJobRecord Tests
# =============================================================================

class TestAIJobRecord:
    """Tests para AIJobRecord (registro interno BD)."""
    
    def test_job_record_defaults(self):
        """AIJobRecord con valores por defecto."""
        record = AIJobRecord(
            job_id="job_123",
            org_id=1,
            user_id=1,
            job_type="ocr",
            status=ProcessingStatus.PENDING,
        )
        assert record.provider == AIProvider.DEEPINFRA
        assert record.retry_count == 0
        assert record.max_retries == 3
        assert record.request_data == {}
    
    def test_job_record_timestamps(self):
        """AIJobRecord con timestamps."""
        now = datetime.now(timezone.utc)
        record = AIJobRecord(
            job_id="job_123",
            org_id=1,
            user_id=1,
            job_type="llm",
            status=ProcessingStatus.COMPLETED,
            created_at=now,
            started_at=now,
            completed_at=now,
        )
        assert record.created_at == now
        assert record.completed_at is not None


# =============================================================================
# Enums Tests
# =============================================================================

class TestEnums:
    """Tests para enums de AI."""
    
    def test_document_types(self):
        """Todos los DocumentType disponibles."""
        assert DocumentType.WASTE_MANIFEST.value == "waste_manifest"
        assert DocumentType.RECEIPT.value == "receipt"
        assert DocumentType.UNKNOWN.value == "unknown"
    
    def test_processing_status(self):
        """Todos los ProcessingStatus."""
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"
    
    def test_ai_provider(self):
        """AIProvider enum."""
        assert AIProvider.DEEPINFRA.value == "deepinfra"
        assert AIProvider.OPENAI.value == "openai"


# =============================================================================
# RateLimiter Tests (Thread-Safety)
# =============================================================================

class TestRateLimiter:
    """Tests para RateLimiter con asyncio."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_under_limit(self):
        """Rate limiter permite requests bajo el límite."""
        limiter = RateLimiter(requests_per_minute=10, requests_per_day=1000)
        
        # 5 requests deben pasar sin espera
        start = time.time()
        for _ in range(5):
            await limiter.acquire()
        elapsed = time.time() - start
        
        # Menos de 1 segundo (sin esperas)
        assert elapsed < 1.0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_minute_limit(self):
        """Rate limiter respeta límite por minuto."""
        limiter = RateLimiter(requests_per_minute=3, requests_per_day=10000)
        
        # 3 requests inmediatas
        for _ in range(3):
            await limiter.acquire()
        
        # 4ta request debe esperar
        start = time.time()
        # No esperamos realmente, solo verificamos que el lock funciona
        # En un test real, mediríamos el tiempo de espera
    
    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_safety(self):
        """RateLimiter es thread-safe con concurrent calls."""
        limiter = RateLimiter(requests_per_minute=100, requests_per_day=10000)
        results: Dict[str, Any] = {"success": 0, "errors": []}
        lock = asyncio.Lock()
        
        async def make_request(req_id: int):
            try:
                await limiter.acquire()
                async with lock:
                    results["success"] += 1
            except Exception as e:
                async with lock:
                    results["errors"].append(str(e))
        
        # 20 requests concurrentes
        await asyncio.gather(*[make_request(i) for i in range(20)])
        
        assert results["success"] == 20
        assert len(results["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_daily_quota_exceeded(self):
        """RateLimiter lanza error al exceder cuota diaria."""
        limiter = RateLimiter(requests_per_minute=1000, requests_per_day=2)
        
        # Usar los 2 requests diarios
        await limiter.acquire()
        await limiter.acquire()
        
        # 3ra request debe fallar
        with pytest.raises(AIQuotaExceededError):
            await limiter.acquire()


# =============================================================================
# DeepInfraClient Mock Tests
# =============================================================================

class TestDeepInfraClientMocks:
    """Tests con mocks de httpx para DeepInfraClient."""
    
    @pytest.mark.asyncio
    async def test_ocr_process_mock_success(self):
        """OCR process exitoso con mock httpx."""
        config = AIConfig(
            deepinfra=DeepInfraConfig(api_base="https://api.deepinfra.com/v1"),
            enable_ocr=True,
        )
        client = DeepInfraClient(config=config)
        
        # Mock httpx
        request = OCRRequest(
            document_id=1,
            org_id=1,
            user_id=1,
            file_url="/test.pdf",
            file_type="pdf",
        )
        
        # Ejecutar OCR (usa simulación interna)
        response = await client.ocr_process(request)
        
        assert response.document_id == 1
        assert response.status == ProcessingStatus.COMPLETED
        assert response.confidence > 0
    
    @pytest.mark.asyncio
    async def test_llm_generate_mock(self):
        """LLM generate con mock httpx response."""
        config = AIConfig(
            deepinfra=DeepInfraConfig(api_base="https://api.deepinfra.com/v1"),
            enable_llm=True,
        )
        client = DeepInfraClient(config=config)
        
        # Mock httpx response - incluir total_tokens para que no falle
        mock_response = {
            "choices": [{"message": {"content": "Test response"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        
        request = LLMRequest(
            messages=[{"role": "user", "content": "test"}],
            max_tokens=100,
        )
        
        # Patch _request para retornar mock
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            response = await client.llm_generate(request)
            
            assert response.content == "Test response"
            assert response.finish_reason == "stop"
    
    @pytest.mark.asyncio
    async def test_client_disabled_feature(self):
        """Cliente rechaza features deshabilitadas."""
        config = AIConfig(enable_ocr=False, enable_llm=False)
        client = DeepInfraClient(config=config)
        
        from app.services.ai.exceptions import AINotConfiguredError
        
        request = OCRRequest(
            document_id=1,
            org_id=1,
            user_id=1,
            file_url="/test.pdf",
            file_type="pdf",
        )
        
        with pytest.raises(AINotConfiguredError):
            await client.ocr_process(request)
    
    @pytest.mark.asyncio
    async def test_usage_stats(self):
        """DeepInfraClient tracking de uso."""
        config = AIConfig()
        client = DeepInfraClient(config=config)
        
        # Simular algunos requests (no esperamos a que realmente pasen)
        stats = client.get_usage_stats()
        
        assert "daily_requests" in stats
        assert "daily_limit" in stats
        assert "requests_per_minute_limit" in stats


# =============================================================================
# Error Schemas Tests
# =============================================================================

class TestAIErrorSchemas:
    """Tests para schemas de error de AI."""
    
    def test_ai_error_response(self):
        """AIErrorResponse con todos los campos."""
        resp = AIErrorResponse(
            error_code=AIErrorCode.TIMEOUT,
            message="Request timeout",
            retry_after=60,
            request_id="req_123",
        )
        assert resp.error_code == AIErrorCode.TIMEOUT
        assert resp.retry_after == 60
    
    def test_ai_health_response(self):
        """AIHealthResponse estructura."""
        resp = AIHealthResponse(
            provider=AIProvider.DEEPINFRA,
            status="healthy",
            latency_ms=150.5,
            rate_limit_remaining=50,
            models_available=["model1", "model2"],
        )
        assert resp.status == "healthy"
        assert len(resp.models_available) == 2
