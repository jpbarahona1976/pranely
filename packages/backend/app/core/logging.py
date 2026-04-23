"""
PRANELY Structured Logging System - NOM-151 Compliance

JSON structured logging with correlation IDs, PII redaction, and compliance levels.
Supports multi-tenant context, log shipping, and audit-critical events.
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from app.core.audit import CorrelationContext, PIIRedactor


# =============================================================================
# Log Levels (Extended for Audit)
# =============================================================================


class LogLevel(str, Enum):
    """Extended log levels including AUDIT for compliance."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    AUDIT = "AUDIT"  # Critical audit events


# =============================================================================
# Structured Log Formatter
# =============================================================================


class StructuredLogFormatter(logging.Formatter):
    """
    JSON structured log formatter for NOM-151 compliance.
    
    Features:
    - JSON output format
    - Correlation ID injection
    - Multi-tenant context (org_id, user_id)
    - PII redaction
    - Configurable field redaction
    """
    
    def __init__(
        self,
        include_stack_trace: bool = False,
        redact_fields: Optional[list] = None,
        redact_pii: bool = True,
    ):
        """
        Initialize formatter.
        
        Args:
            include_stack_trace: Include stack traces in logs
            redact_fields: Field names to redact
            redact_pii: Auto-redact PII based on field names
        """
        super().__init__()
        self.include_stack_trace = include_stack_trace
        self.redact_fields = redact_fields or [
            'password', 'hashed_password', 'secret', 'token', 'api_key',
            'authorization', 'credential', 'private_key',
            'credit_card', 'card_number', 'cvv', 'ssn',
        ]
        self.redact_pii = redact_pii
    
    def _format_timestamp(self) -> str:
        """Get ISO format timestamp."""
        return datetime.now(timezone.utc).isoformat()
    
    def _get_context(self) -> Dict[str, Any]:
        """Get current correlation context."""
        return {
            "correlation_id": CorrelationContext.get_correlation_id(),
            "org_id": CorrelationContext.get_org_id(),
            "user_id": CorrelationContext.get_user_id(),
        }
    
    def _redact_message(self, message: str) -> str:
        """Redact PII from message string."""
        if not self.redact_pii:
            return message
        
        # Basic PII patterns in messages
        patterns = [
            (r'\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b', lambda m: PIIRedactor.redact_email(m.group())),
            (r'\b\d{2}-\d{4}-\d{4}\b', '[PHONE_REDACTED]'),
            (r'\b\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE_REDACTED]'),
        ]
        
        result = message
        for pattern, replacement in patterns:
            if callable(replacement):
                import re
                result = re.sub(pattern, replacement, result)
            else:
                import re
                result = re.sub(pattern, replacement, result)
        
        return result
    
    def _redact_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields from log record."""
        if not self.redact_pii:
            return record
        
        result = {}
        for key, value in record.items():
            if value is None:
                result[key] = None
                continue
            
            key_lower = key.lower()
            
            # Check if field should be redacted
            should_redact = any(field in key_lower for field in self.redact_fields)
            
            if should_redact:
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = self._redact_record(value)
            elif isinstance(value, list):
                result[key] = [
                    self._redact_record(item) if isinstance(item, dict)
                    else "[REDACTED]" if any(f in str(item).lower() for f in self.redact_fields)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base structure
        log_entry = {
            "timestamp": self._format_timestamp(),
            "level": record.levelname,
            "logger": record.name,
            "message": self._redact_message(str(record.getMessage())),
            **self._get_context(),
        }
        
        # Add source information
        if record.filename:
            log_entry["source"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        # Add exception info if present
        if record.exc_info and self.include_stack_trace:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stack_trace": self.formatException(record.exc_info),
            }
        
        # Add extra fields from LogRecord
        if hasattr(record, '__dict__'):
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in (
                    'name', 'msg', 'args', 'created', 'filename', 'funcName',
                    'levelname', 'lineno', 'module', 'msecs', 'message',
                    'pathname', 'process', 'processName', 'relativeCreated',
                    'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                    'taskName', 'message', 'asctime',
                ):
                    extra_fields[key] = value
            
            if extra_fields:
                log_entry["extra"] = self._redact_record(extra_fields)
        
        # Apply final redaction
        log_entry = self._redact_record(log_entry)
        
        return json.dumps(log_entry, default=str)


# =============================================================================
# Audit Logger
# =============================================================================


class AuditLogger:
    """
    Specialized audit logger for NOM-151 compliance.
    
    Logs critical events that must be preserved for regulatory compliance.
    Always includes full context and cannot be silenced.
    """
    
    def __init__(self, name: str = "pranely.audit"):
        """Initialize audit logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.CRITICAL)  # Never filtered out
        
        # Add handler if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredLogFormatter(
                include_stack_trace=True,
                redact_pii=True,
            ))
            self.logger.addHandler(handler)
    
    def _build_entry(
        self,
        event_type: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Build audit log entry."""
        entry = {
            "audit_event": True,
            "event_type": event_type,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **self._get_context(),
        }
        
        if resource_type:
            entry["resource_type"] = resource_type
        if resource_id:
            entry["resource_id"] = str(resource_id)
        if metadata:
            entry["metadata"] = PIIRedactor.redact_dict(metadata)
        
        entry.update(kwargs)
        
        return entry
    
    def _get_context(self) -> Dict[str, Any]:
        """Get current context for audit log."""
        return {
            "correlation_id": CorrelationContext.get_correlation_id(),
            "org_id": CorrelationContext.get_org_id(),
            "user_id": CorrelationContext.get_user_id(),
        }
    
    def log_authentication(
        self,
        action: str,
        success: bool,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ):
        """Log authentication events."""
        entry = self._build_entry(
            event_type="authentication",
            action=action,
            metadata={
                "success": success,
                "email": PIIRedactor.redact_email(email) if email else None,
                "ip_address": ip_address,
                "user_agent": user_agent,
                **kwargs,
            }
        )
        self.logger.critical(json.dumps(entry, default=str))
    
    def log_authorization(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        granted: bool = True,
        **kwargs
    ):
        """Log authorization events."""
        entry = self._build_entry(
            event_type="authorization",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata={
                "granted": granted,
                **kwargs,
            }
        )
        self.logger.critical(json.dumps(entry, default=str))
    
    def log_data_access(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        fields_accessed: Optional[list] = None,
        **kwargs
    ):
        """Log data access events."""
        entry = self._build_entry(
            event_type="data_access",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata={
                "fields_accessed": fields_accessed,
                **kwargs,
            }
        )
        self.logger.critical(json.dumps(entry, default=str))
    
    def log_data_modification(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
        **kwargs
    ):
        """Log data modification events."""
        entry = self._build_entry(
            event_type="data_modification",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata={
                "previous_state": PIIRedactor.redact_dict(previous_state) if previous_state else None,
                "new_state": PIIRedactor.redact_dict(new_state) if new_state else None,
                **kwargs,
            }
        )
        self.logger.critical(json.dumps(entry, default=str))
    
    def log_consent(
        self,
        action: str,
        consent_type: str,
        granted: bool,
        **kwargs
    ):
        """Log consent events (NOM-151 PII compliance)."""
        entry = self._build_entry(
            event_type="consent",
            action=action,
            metadata={
                "consent_type": consent_type,
                "granted": granted,
                **kwargs,
            }
        )
        self.logger.critical(json.dumps(entry, default=str))
    
    def log_data_export(
        self,
        resource_type: str,
        record_count: int,
        export_format: str,
        **kwargs
    ):
        """Log data export events (NOM-151 data portability)."""
        entry = self._build_entry(
            event_type="data_export",
            action="export",
            resource_type=resource_type,
            metadata={
                "record_count": record_count,
                "export_format": export_format,
                **kwargs,
            }
        )
        self.logger.critical(json.dumps(entry, default=str))
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        **kwargs
    ):
        """Log security-related events."""
        entry = self._build_entry(
            event_type="security",
            action=event_type,
            metadata={
                "severity": severity,
                "description": description,
                **kwargs,
            }
        )
        self.logger.critical(json.dumps(entry, default=str))


# =============================================================================
# Logging Configuration
# =============================================================================


def setup_logging(
    level: str = "INFO",
    json_output: bool = True,
    include_correlation: bool = True,
    redact_pii: bool = True,
) -> logging.Logger:
    """
    Configure application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARN, ERROR)
        json_output: Use JSON formatter
        include_correlation: Include correlation ID in logs
        redact_pii: Redact PII from logs
    
    Returns:
        Configured root logger
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger("pranely")
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    
    if json_output:
        handler.setFormatter(StructuredLogFormatter(
            include_stack_trace=True,
            redact_pii=redact_pii,
        ))
    else:
        # Plain text formatter with correlation ID
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
    
    # Configure werkzeug logger to reduce noise
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str = "pranely") -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (will be prefixed with 'pranely.')
    
    Returns:
        Logger instance
    """
    if not name.startswith("pranely"):
        name = f"pranely.{name}"
    
    return logging.getLogger(name)


def get_audit_logger() -> AuditLogger:
    """Get the audit logger instance."""
    return AuditLogger()


# =============================================================================
# Context Manager for Logging
# =============================================================================


class LogContext:
    """Context manager for temporary logging context."""
    
    def __init__(
        self,
        correlation_id: Optional[str] = None,
        org_id: Optional[int] = None,
        user_id: Optional[int] = None,
        request_id: Optional[str] = None,
    ):
        """Initialize log context."""
        self.correlation_id = correlation_id
        self.org_id = org_id
        self.user_id = user_id
        self.request_id = request_id
        self._previous_correlation: Optional[str] = None
        self._previous_org: Optional[int] = None
        self._previous_user: Optional[int] = None
        self._previous_request: Optional[str] = None
    
    def __enter__(self):
        """Enter context - save and set values."""
        self._previous_correlation = CorrelationContext.get_correlation_id()
        self._previous_org = CorrelationContext.get_org_id()
        self._previous_user = CorrelationContext.get_user_id()
        self._previous_request = CorrelationContext.get_request_id()
        
        CorrelationContext.set(
            correlation_id=self.correlation_id,
            org_id=self.org_id,
            user_id=self.user_id,
            request_id=self.request_id,
        )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore previous values."""
        CorrelationContext.set(
            correlation_id=self._previous_correlation,
            org_id=self._previous_org,
            user_id=self._previous_user,
            request_id=self._previous_request,
        )
        return False


# =============================================================================
# Convenience Logging Functions
# =============================================================================


def log_audit_event(
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    **kwargs
):
    """
    Log an audit event using the audit logger.
    
    This is a convenience function that wraps AuditLogger.log_data_modification.
    """
    audit_logger = get_audit_logger()
    audit_logger.log_data_modification(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        **kwargs
    )


def log_with_context(logger: logging.Logger, message: str, **kwargs):
    """
    Log a message with additional context fields.
    
    Args:
        logger: Logger instance
        message: Log message
        **kwargs: Additional context fields to include
    """
    extra = {'context': kwargs}
    logger.log(logging.INFO, message, extra=extra)
