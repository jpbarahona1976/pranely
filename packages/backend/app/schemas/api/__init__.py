"""API schema exports."""
from app.schemas.api.employer import EmployerIn, EmployerOut
from app.schemas.api.transporter import TransporterIn, TransporterOut
from app.schemas.api.residue import ResidueIn, ResidueOut
from app.schemas.api.link import LinkIn, LinkOut
from app.schemas.api.auth import LoginIn, RegisterIn, TokenOut, UserOut, OrgOut
from app.schemas.api.common import PaginationParams, ListResponse, ErrorResponse
from app.schemas.api.ai import (
    # Enums
    AIErrorCode,
    AIHealthResponse,
    AIProvider,
    DocumentType,
    ProcessingStatus,
    # Request schemas
    EmbeddingsRequest,
    LLMRequest,
    OCRRequest,
    # Response schemas
    EmbeddingsResponse,
    ExtractedField,
    LLMResponse,
    OCRResponse,
    # Error schemas
    AIErrorResponse,
    # Internal
    AIJobRecord,
)

__all__ = [
    # Common
    "PaginationParams",
    "ListResponse",
    "ErrorResponse",
    # Auth
    "LoginIn",
    "RegisterIn",
    "TokenOut",
    "UserOut",
    "OrgOut",
    # Employer
    "EmployerIn",
    "EmployerOut",
    # Transporter
    "TransporterIn",
    "TransporterOut",
    # Residue
    "ResidueIn",
    "ResidueOut",
    # Link
    "LinkIn",
    "LinkOut",
    # AI / DeepInfra
    "AIErrorCode",
    "AIErrorResponse",
    "AIHealthResponse",
    "AIJobRecord",
    "AIProvider",
    "DocumentType",
    "EmbeddingsRequest",
    "EmbeddingsResponse",
    "ExtractedField",
    "LLMRequest",
    "LLMResponse",
    "OCRRequest",
    "OCRResponse",
    "ProcessingStatus",
]