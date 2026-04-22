"""Common API schemas."""
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field


T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class ListResponse(BaseModel, Generic[T]):
    """Generic paginated list response."""
    items: List[T] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")


class ErrorDetail(BaseModel):
    """RFC 7807 Problem Details field error."""
    field: str = Field(description="Field that caused the error")
    message: str = Field(description="Error message")


class ErrorResponse(BaseModel):
    """Standard error response (RFC 7807)."""
    type: str = Field(description="Error type URI")
    title: str = Field(description="Short error title")
    status: int = Field(description="HTTP status code")
    detail: str = Field(description="Human-readable error detail")
    instance: Optional[str] = Field(default=None, description="Request path")
    errors: Optional[List[ErrorDetail]] = Field(default=None, description="Field-level errors")