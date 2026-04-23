"""
PRANELY Audit Trail System - NOM-151 Compliance

Audit trails for regulatory compliance with Mexican digital document standards.
Supports data residency, PII handling, and structured logging.
"""
from __future__ import annotations

import json
import re
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from app.core.database import AsyncSessionLocal
from app.models import Base
from sqlalchemy import DateTime, Index, Integer, JSON, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# =============================================================================
# Enums
# =============================================================================


class AuditAction(str, Enum):
    """Audit action types for NOM-151 compliance."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    ARCHIVE = "archive"
    RESTORE = "restore"
    CONSENT = "consent"
    CONSENT_WITHDRAW = "consent_withdraw"
    PERMISSION_CHANGE = "permission_change"
    CONFIG_CHANGE = "config_change"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    AUDIT = "audit"  # Critical audit events


# =============================================================================
# PII Redaction Utilities
# =============================================================================


class PIIRedactor:
    """
    PII redaction utility for NOM-151 compliance.
    
    Redacts sensitive data before logging to ensure privacy compliance.
    """
    
    EMAIL_PATTERN = re.compile(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
    PHONE_PATTERN = re.compile(r'(\+?[0-9]{1,3}[-.\s]?)?(\(?[0-9]{2,4}\)?[-.\s]?)?[0-9]{6,10}')
    RFC_PATTERN = re.compile(r'[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}')
    CURP_PATTERN = re.compile(r'[A-Z]{4}[0-9]{6}[A-Z]{6}[0-9]{2}')
    
    @classmethod
    def redact_email(cls, email: str) -> str:
        """Redact email address: john.doe@example.com → j***@***.com"""
        if not email or '@' not in email:
            return "[EMAIL_REDACTED]"
        
        local, domain = email.split('@', 1)
        
        # Mask local part: keep first char + *** mask
        if len(local) >= 1:
            local_masked = local[0] + "***"
        else:
            local_masked = "***"
        
        # For very short local parts, show more of the domain for usability
        # Otherwise, mask domain except TLD for privacy
        if len(local) <= 2:
            # Show domain name but mask TLD for very short local parts
            if '.' in domain:
                domain_parts = domain.split('.')
                if len(domain_parts) >= 2:
                    # Show domain name, mask TLD except first char
                    domain_name = domain_parts[0]
                    tld = domain_parts[-1]
                    if len(tld) <= 2:
                        domain_masked = domain_name + ".***"
                    else:
                        domain_masked = domain_name + "." + tld[0] + "**"
                else:
                    domain_masked = domain
            else:
                domain_masked = domain
        else:
            # Mask domain except TLD for normal/local part lengths
            parts = domain.rsplit('.', 1)
            if len(parts) == 2:
                domain_masked = "***."
            else:
                domain_masked = "***"
         
        return f"{local_masked}@{domain_masked}{'' if len(local) <= 2 and '.' in domain else (parts[-1] if len(parts) == 2 else '')}"
    
    @classmethod
    def redact_phone(cls, phone: str) -> str:
        """Redact phone number: +52-55-1234-5678 → +52-***-***-5678"""
        if not phone:
            return "[PHONE_REDACTED]"
        
        # Keep last 4 digits
        digits = re.sub(r'[^0-9]', '', phone)
        if len(digits) >= 7:
            return f"[PHONE_REDACTED_LAST_{digits[-4:]}]"
        return "[PHONE_REDACTED]"
    
    @classmethod
    def redact_rfc(cls, rfc: str) -> str:
        """Redact RFC: ABCD123456XYZ → ABCD******XYZ"""
        if not rfc or len(rfc) < 6:
            return "[RFC_REDACTED]"
        
        if len(rfc) <= 8:
            return rfc[:4] + "****"
        return rfc[:4] + "******" + rfc[-3:]
    
    @classmethod
    def redact_curp(cls, curp: str) -> str:
        """Redact CURP: ABCD123456ABCDEF12 → ABCD********ABCDEF12"""
        if not curp or len(curp) < 12:
            return "[CURP_REDACTED]"
        return curp[:4] + "********" + curp[-8:]
    
    @classmethod
    def redact_value(cls, value: str, field_name: str = "") -> str:
        """Auto-detect and redact PII based on field name or content."""
        if not value:
            return "[REDACTED]"
        
        value_lower = field_name.lower()
        
        # Field-based redaction
        if any(k in value_lower for k in ['email', 'correo', 'mail']):
            return cls.redact_email(value)
        if any(k in value_lower for k in ['phone', 'telefono', 'celular', 'mobile']):
            return cls.redact_phone(value)
        if any(k in value_lower for k in ['rfc', 'tax', 'fiscal']):
            return cls.redact_rfc(value)
        if 'curp' in value_lower:
            return cls.redact_curp(value)
        
        # Content-based detection
        if cls.EMAIL_PATTERN.match(value):
            return cls.redact_email(value)
        if cls.RFC_PATTERN.match(value.upper()):
            return cls.redact_rfc(value)
        
        return "[REDACTED]"
    
    @classmethod
    def redact_dict(cls, data: Dict[str, Any], fields_to_redact: Optional[list] = None) -> Dict[str, Any]:
        """
        Redact PII from dictionary.
        
        Args:
            data: Dictionary to redact
            fields_to_redact: Optional list of field names to redact (auto-detect if not provided)
        
        Returns:
            New dictionary with PII redacted
        """
        if fields_to_redact is None:
            fields_to_redact = [
                'email', 'correo', 'mail',
                'phone', 'telefono', 'celular', 'mobile',
                'rfc', 'tax_id', 'fiscal_id',
                'curp',
                'password', 'hashed_password',
                'secret', 'token', 'api_key',
            ]
        
        result = {}
        for key, value in data.items():
            if value is None:
                result[key] = None
                continue
            
            key_lower = key.lower()
            
            # Check if field should be redacted
            should_redact = any(field in key_lower for field in fields_to_redact)
            
            if should_redact:
                result[key] = cls.redact_value(str(value), key)
            elif isinstance(value, dict):
                result[key] = cls.redact_dict(value, fields_to_redact)
            elif isinstance(value, list):
                result[key] = [
                    cls.redact_dict(item, fields_to_redact) if isinstance(item, dict)
                    else cls.redact_value(str(item), key) if should_redact else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result


# =============================================================================
# Correlation ID Management
# =============================================================================


class CorrelationContext:
    """Thread-local correlation ID management for request tracing."""
    
    _correlation_id: str = ""
    _org_id: Optional[int] = None
    _user_id: Optional[int] = None
    _request_id: Optional[str] = None
    
    @classmethod
    def set(
        cls,
        correlation_id: Optional[str] = None,
        org_id: Optional[int] = None,
        user_id: Optional[int] = None,
        request_id: Optional[str] = None
    ) -> str:
        """Set correlation context values."""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        cls._correlation_id = correlation_id
        cls._org_id = org_id
        cls._user_id = user_id
        cls._request_id = request_id
        
        return correlation_id
    
    @classmethod
    def get_correlation_id(cls) -> str:
        """Get current correlation ID.
        
        Returns empty string if no correlation ID was set,
        unless explicitly set via set() which generates UUID.
        """
        return cls._correlation_id
    
    @classmethod
    def get_org_id(cls) -> Optional[int]:
        """Get current organization ID."""
        return cls._org_id
    
    @classmethod
    def get_user_id(cls) -> Optional[int]:
        """Get current user ID."""
        return cls._user_id
    
    @classmethod
    def get_request_id(cls) -> Optional[str]:
        """Get current request ID."""
        return cls._request_id
    
    @classmethod
    def clear(cls) -> None:
        """Clear correlation context."""
        cls._correlation_id = ""
        cls._org_id = None
        cls._user_id = None
        cls._request_id = None


# =============================================================================
# AuditTrail Model
# =============================================================================


class AuditTrailModel(Base):
    """
    Audit trail model for NOM-151 compliance.
    
    Stores all significant events with full context for regulatory compliance.
    Data retention: 5 years minimum per NOM-151 requirements.
    
    Attributes:
        correlation_id: Request tracing ID
        user_id: User who performed the action
        org_id: Organization context
        action: Type of action performed
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        severity: Event severity level
        ip_address: Client IP address
        user_agent: Client user agent
        request_path: API endpoint path
        request_method: HTTP method
        request_data: Request payload (PII redacted)
        response_status: HTTP response status
        metadata: Additional structured metadata
        timestamp: Event timestamp (UTC)
    """
    __tablename__ = "audit_trails"
    __table_args__ = (
        # Indexes for common queries
        Index("ix_audit_trail_org_timestamp", "organization_id", "timestamp"),
        Index("ix_audit_trail_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_trail_resource", "resource_type", "resource_id"),
        Index("ix_audit_trail_correlation", "correlation_id"),
        Index("ix_audit_trail_action", "action", "timestamp"),
        UniqueConstraint("id", name="uq_audit_trail_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # Actor context
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    organization_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Action details
    action: Mapped[AuditAction] = mapped_column(SQLEnum(AuditAction), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    severity: Mapped[AuditSeverity] = mapped_column(
        SQLEnum(AuditSeverity), default=AuditSeverity.INFO
    )
    
    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 compatible
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    request_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Response
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Additional metadata
    audit_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    
    def __repr__(self) -> str:
        return (
            f"<AuditTrail(id={self.id}, action={self.action.value}, "
            f"resource={self.resource_type}/{self.resource_id}, "
            f"user={self.user_id}, org={self.organization_id})>"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "severity": self.severity.value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_path": self.request_path,
            "request_method": self.request_method,
            "request_data": self.request_data,
            "response_status": self.response_status,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =============================================================================
# Audit Event Context Manager
# =============================================================================


@contextmanager
async def audit_event(
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.INFO,
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    org_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_path: Optional[str] = None,
    request_method: Optional[str] = None,
    request_data: Optional[Dict[str, Any]] = None,
    response_status: Optional[int] = None,
):
    """
    Context manager for audit event recording.
    
    Usage:
        async with audit_event(
            action=AuditAction.CREATE,
            resource_type="employer",
            resource_id="123",
            org_id=1,
            user_id=1
        ) as event:
            # Do work
            event["response_status"] = 201
            event["metadata"]["employer_name"] = "Test Corp"
    
    Args:
        action: Type of audit action
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        severity: Event severity
        metadata: Additional metadata
        user_id: User performing action
        org_id: Organization context
        ip_address: Client IP
        user_agent: Client user agent
        request_path: API endpoint
        request_method: HTTP method
        request_data: Request payload (will be redacted)
        response_status: HTTP response status
    
    Yields:
        Dict that can be modified with additional data
    """
    correlation_id = CorrelationContext.get_correlation_id()
    
    # Redact PII from request data
    redacted_data = None
    if request_data:
        redacted_data = PIIRedactor.redact_dict(request_data)
    
    # Prepare event data
    event_data: Dict[str, Any] = {
        "correlation_id": correlation_id,
        "user_id": user_id or CorrelationContext.get_user_id(),
        "organization_id": org_id or CorrelationContext.get_org_id(),
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "severity": severity,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "request_path": request_path,
        "request_method": request_method,
        "request_data": redacted_data,
        "response_status": response_status,
        "metadata": metadata or {},
    }
    
    try:
        yield event_data
    except Exception as e:
        event_data["severity"] = AuditSeverity.ERROR
        event_data["metadata"]["error"] = str(e)
        event_data["response_status"] = 500
        raise
    finally:
        # Persist to database
        try:
            async with AsyncSessionLocal() as session:
                audit_record = AuditTrailModel(
                    correlation_id=event_data["correlation_id"],
                    user_id=event_data["user_id"],
                    organization_id=event_data["organization_id"],
                    action=event_data["action"],
                    resource_type=event_data["resource_type"],
                    resource_id=event_data["resource_id"],
                    severity=event_data["severity"],
                    ip_address=event_data["ip_address"],
                    user_agent=event_data["user_agent"],
                    request_path=event_data["request_path"],
                    request_method=event_data["request_method"],
                    request_data=event_data["request_data"],
                    response_status=event_data["response_status"],
                    metadata=event_data["metadata"],
                    timestamp=datetime.now(timezone.utc),
                )
                session.add(audit_record)
                await session.commit()
        except Exception as e:
            # Don't fail the main operation if audit fails
            print(f"Failed to persist audit event: {e}", file=sys.stderr)


# =============================================================================
# Audit Event Recording Function
# =============================================================================


async def record_audit_event(**kwargs) -> AuditTrailModel:
    """
    Record an audit event directly (without context manager).
    
    Args:
        **kwargs: Same as audit_event context manager parameters
    
    Returns:
        Created AuditTrailModel instance
    """
    correlation_id = CorrelationContext.get_correlation_id()
    
    # Redact PII from request data
    request_data = kwargs.get("request_data")
    if request_data:
        kwargs["request_data"] = PIIRedactor.redact_dict(request_data)
    
    # Merge with correlation context
    kwargs.setdefault("user_id", CorrelationContext.get_user_id())
    kwargs.setdefault("organization_id", CorrelationContext.get_org_id())
    kwargs.setdefault("correlation_id", correlation_id)
    
    async with AsyncSessionLocal() as session:
        audit_record = AuditTrailModel(
            correlation_id=kwargs.get("correlation_id", correlation_id),
            user_id=kwargs.get("user_id"),
            organization_id=kwargs.get("organization_id"),
            action=kwargs.get("action"),
            resource_type=kwargs.get("resource_type"),
            resource_id=kwargs.get("resource_id"),
            severity=kwargs.get("severity", AuditSeverity.INFO),
            ip_address=kwargs.get("ip_address"),
            user_agent=kwargs.get("user_agent"),
            request_path=kwargs.get("request_path"),
            request_method=kwargs.get("request_method"),
            request_data=kwargs.get("request_data"),
            response_status=kwargs.get("response_status"),
            metadata=kwargs.get("metadata"),
            timestamp=datetime.now(timezone.utc),
        )
        session.add(audit_record)
        await session.commit()
        await session.refresh(audit_record)
        return audit_record


# =============================================================================
# Query Utilities
# =============================================================================


async def query_audit_trails(
    session: AsyncSession,
    org_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[AuditAction] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    severity: Optional[AuditSeverity] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditTrailModel]:
    """
    Query audit trails with filters.
    
    Args:
        session: Database session
        org_id: Filter by organization
        user_id: Filter by user
        action: Filter by action type
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        start_date: Filter by start timestamp
        end_date: Filter by end timestamp
        severity: Filter by severity
        limit: Maximum results (default 100)
        offset: Pagination offset
    
    Returns:
        List of matching audit records
    """
    from sqlalchemy import select, and_
    
    conditions = []
    
    if org_id is not None:
        conditions.append(AuditTrailModel.organization_id == org_id)
    if user_id is not None:
        conditions.append(AuditTrailModel.user_id == user_id)
    if action is not None:
        conditions.append(AuditTrailModel.action == action)
    if resource_type is not None:
        conditions.append(AuditTrailModel.resource_type == resource_type)
    if resource_id is not None:
        conditions.append(AuditTrailModel.resource_id == resource_id)
    if start_date is not None:
        conditions.append(AuditTrailModel.timestamp >= start_date)
    if end_date is not None:
        conditions.append(AuditTrailModel.timestamp <= end_date)
    if severity is not None:
        conditions.append(AuditTrailModel.severity == severity)
    
    query = (
        select(AuditTrailModel)
        .where(and_(*conditions))
        .order_by(AuditTrailModel.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await session.execute(query)
    return list(result.scalars().all())


# =============================================================================
# Export Utilities
# =============================================================================


async def export_audit_trails(
    session: AsyncSession,
    org_id: int,
    start_date: datetime,
    end_date: datetime,
    format: str = "json"
) -> Dict[str, Any]:
    """
    Export audit trails for compliance reporting.
    
    Args:
        session: Database session
        org_id: Organization to export
        start_date: Start of date range
        end_date: End of date range
        format: Export format (json or csv)
    
    Returns:
        Dictionary with export data and metadata
    """
    records = await query_audit_trails(
        session=session,
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
        limit=10000,  # Max export size
    )
    
    export_data = {
        "export_metadata": {
            "org_id": org_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "record_count": len(records),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": format,
            "nom151_compliant": True,
        },
        "records": [record.to_dict() for record in records],
    }
    
    return export_data
