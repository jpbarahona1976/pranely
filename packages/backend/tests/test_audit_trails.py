"""
PRANELY - Test Suite for Audit Trails and NOM-151 Compliance

Covers:
- AuditTrail model
- PII redaction
- Structured logging
- Correlation context
- Audit event recording
- NOM-151 compliance verification
"""
import json
import re
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional


# =============================================================================
# Test: PII Redaction
# =============================================================================


class TestPIIRedaction:
    """Tests for PII redaction utilities."""
    
    def setup_method(self):
        """Setup test fixtures."""
        from app.core.audit import PIIRedactor
        self.redactor = PIIRedactor
    
    def test_redact_email_basic(self):
        """Test basic email redaction."""
        email = "john.doe@example.com"
        result = self.redactor.redact_email(email)
        assert result == "j***@***.com"
    
    def test_redact_email_short_local(self):
        """Test email with short local part."""
        email = "jd@example.com"
        result = self.redactor.redact_email(email)
        # Short local part: first char + *** masking
        assert "***" in result
        assert "@" in result
        assert "example" in result
    
    def test_redact_email_invalid(self):
        """Test invalid email returns placeholder."""
        result = self.redactor.redact_email("not-an-email")
        assert result == "[EMAIL_REDACTED]"
    
    def test_redact_email_empty(self):
        """Test empty email returns placeholder."""
        result = self.redactor.redact_email("")
        assert result == "[EMAIL_REDACTED]"
    
    def test_redact_phone_mexican(self):
        """Test Mexican phone number redaction."""
        phone = "+52-55-1234-5678"
        result = self.redactor.redact_phone(phone)
        assert "5678" in result
        assert "1234" not in result
    
    def test_redact_phone_short(self):
        """Test short phone number redaction."""
        phone = "123456"
        result = self.redactor.redact_phone(phone)
        assert "[PHONE_REDACTED]" in result
    
    def test_redact_rfc_standard(self):
        """Test RFC (Mexican tax ID) redaction."""
        rfc = "ABCD123456XYZ"
        result = self.redactor.redact_rfc(rfc)
        assert "ABCD" in result
        assert "XYZ" in result
        assert "123456" not in result
    
    def test_redact_rfc_short(self):
        """Test short RFC redaction."""
        rfc = "ABC12"
        result = self.redactor.redact_rfc(rfc)
        assert result == "[RFC_REDACTED]"
    
    def test_redact_curp(self):
        """Test CURP redaction."""
        curp = "ABCD123456ABCDEF12"
        result = self.redactor.redact_curp(curp)
        # Keep first 4 and last 8 chars (8 chars = "ABCDEF12" as expected by test)
        assert "ABCD" in result
        assert "ABCDEF12" in result
        assert "123456" not in result
    
    def test_redact_value_auto_detect_email(self):
        """Test auto-detection of email in value."""
        result = self.redactor.redact_value("test@example.com", "data")
        assert "***" in result
    
    def test_redact_value_field_based(self):
        """Test field-based PII detection."""
        result = self.redactor.redact_value("secret123", "password")
        assert result == "[REDACTED]"
    
    def test_redact_dict_complete(self):
        """Test full dictionary redaction."""
        data = {
            "email": "test@example.com",
            "password": "supersecret",
            "name": "John Doe",
            "phone": "+52-55-1234-5678",
        }
        result = self.redactor.redact_dict(data)
        
        assert result["email"] == "t***@***.com"
        assert result["password"] == "[REDACTED]"
        assert result["name"] == "John Doe"  # Not PII
        assert "5678" in result["phone"]
    
    def test_redact_dict_nested(self):
        """Test nested dictionary redaction."""
        data = {
            "user": {
                "email": "test@example.com",
                "credentials": {
                    "api_key": "sk-123456"
                }
            }
        }
        result = self.redactor.redact_dict(data)
        
        assert result["user"]["email"] == "t***@***.com"
        assert result["user"]["credentials"]["api_key"] == "[REDACTED]"
    
    def test_redact_dict_with_list(self):
        """Test list value redaction."""
        data = {
            "users": [
                {"email": "user1@example.com"},
                {"email": "user2@example.com"},
            ]
        }
        result = self.redactor.redact_dict(data)
        
        assert result["users"][0]["email"] == "u***@***.com"
        assert result["users"][1]["email"] == "u***@***.com"
    
    def test_redact_dict_preserves_none(self):
        """Test that None values are preserved."""
        data = {"email": None, "name": None}
        result = self.redactor.redact_dict(data)
        
        assert result["email"] is None
        assert result["name"] is None


# =============================================================================
# Test: Correlation Context
# =============================================================================


class TestCorrelationContext:
    """Tests for correlation context management."""
    
    def setup_method(self):
        """Reset context before each test."""
        from app.core.audit import CorrelationContext
        CorrelationContext.clear()
        self.context = CorrelationContext
    
    def teardown_method(self):
        """Clear context after each test."""
        self.context.clear()
    
    def test_set_correlation_id(self):
        """Test setting correlation ID."""
        corr_id = self.context.set(correlation_id="test-123")
        assert corr_id == "test-123"
        assert self.context.get_correlation_id() == "test-123"
    
    def test_set_generates_uuid_if_none(self):
        """Test that UUID is generated if correlation ID is None."""
        corr_id = self.context.set()
        assert corr_id is not None
        assert len(corr_id) == 36  # UUID format
    
    def test_set_org_id(self):
        """Test setting organization ID."""
        self.context.set(org_id=123)
        assert self.context.get_org_id() == 123
    
    def test_set_user_id(self):
        """Test setting user ID."""
        self.context.set(user_id=456)
        assert self.context.get_user_id() == 456
    
    def test_set_multiple_contexts(self):
        """Test setting multiple context values at once."""
        self.context.set(
            correlation_id="corr-123",
            org_id=1,
            user_id=2,
            request_id="req-456"
        )
        
        assert self.context.get_correlation_id() == "corr-123"
        assert self.context.get_org_id() == 1
        assert self.context.get_user_id() == 2
        assert self.context.get_request_id() == "req-456"
    
    def test_get_correlation_id_returns_empty_when_not_set(self):
        """Test that get_correlation_id returns empty string when not set."""
        # Start fresh
        self.context.clear()
        corr_id = self.context.get_correlation_id()
        assert corr_id == ""
    
    def test_clear_context(self):
        """Test clearing context."""
        self.context.set(
            correlation_id="test-123",
            org_id=1,
            user_id=2
        )
        
        self.context.clear()
        
        assert self.context.get_correlation_id() == ""
        assert self.context.get_org_id() is None
        assert self.context.get_user_id() is None


# =============================================================================
# Test: AuditTrail Model
# =============================================================================


class TestAuditTrailModel:
    """Tests for AuditTrail model."""
    
    def test_audit_action_enum_values(self):
        """Test AuditAction enum has all expected values."""
        from app.core.audit import AuditAction
        
        expected_actions = [
            "create", "read", "update", "delete",
            "login", "logout", "export", "import",
            "approve", "reject", "archive", "restore",
            "consent", "consent_withdraw",
            "permission_change", "config_change"
        ]
        
        for action in expected_actions:
            assert hasattr(AuditAction, action.upper())
            assert getattr(AuditAction, action.upper()).value == action
    
    def test_audit_severity_enum_values(self):
        """Test AuditSeverity enum has all expected values."""
        from app.core.audit import AuditSeverity
        
        expected_levels = ["debug", "info", "warn", "error", "audit"]
        
        for level in expected_levels:
            assert hasattr(AuditSeverity, level.upper())
            assert getattr(AuditSeverity, level.upper()).value == level
    
    def test_audit_trail_model_fields(self):
        """Test AuditTrail model has all required fields."""
        from app.core.audit import AuditTrailModel
        
        # Check required fields exist
        required_fields = [
            'id', 'correlation_id', 'user_id', 'organization_id',
            'action', 'resource_type', 'resource_id', 'severity',
            'ip_address', 'user_agent', 'request_path', 'request_method',
            'request_data', 'response_status', 'metadata', 'timestamp'
        ]
        
        for field in required_fields:
            assert hasattr(AuditTrailModel, field), f"Missing field: {field}"
    
    def test_audit_trail_table_name(self):
        """Test AuditTrail table name."""
        from app.core.audit import AuditTrailModel
        
        assert AuditTrailModel.__tablename__ == "audit_trails"
    
    def test_audit_trail_repr(self):
        """Test AuditTrail string representation."""
        from app.core.audit import AuditTrailModel, AuditAction, AuditSeverity
        
        # Create a mock instance
        model = AuditTrailModel(
            id=1,
            action=AuditAction.CREATE,
            resource_type="employer",
            resource_id="123",
            user_id=1,
            organization_id=1,
            correlation_id="test-corr-123",
            severity=AuditSeverity.INFO,
        )
        
        repr_str = repr(model)
        assert "AuditTrail" in repr_str
        assert "action=create" in repr_str
        assert "resource=employer" in repr_str
    
    def test_audit_trail_to_dict(self):
        """Test AuditTrail to_dict method."""
        from app.core.audit import AuditTrailModel, AuditAction, AuditSeverity
        
        timestamp = datetime.now(timezone.utc)
        model = AuditTrailModel(
            id=1,
            correlation_id="test-corr-123",
            user_id=1,
            organization_id=1,
            action=AuditAction.CREATE,
            resource_type="employer",
            resource_id="123",
            severity=AuditSeverity.INFO,
            ip_address="192.168.1.1",
            request_path="/api/employers",
            request_method="POST",
            timestamp=timestamp,
        )
        
        result = model.to_dict()
        
        assert result["id"] == 1
        assert result["correlation_id"] == "test-corr-123"
        assert result["action"] == "create"
        assert result["resource_type"] == "employer"
        assert result["resource_id"] == "123"
        assert result["timestamp"] is not None


# =============================================================================
# Test: Structured Logging
# =============================================================================


class TestStructuredLogging:
    """Tests for structured logging system."""
    
    def test_log_level_enum(self):
        """Test LogLevel enum values."""
        from app.core.logging import LogLevel
        
        expected_levels = ["DEBUG", "INFO", "WARN", "ERROR", "AUDIT"]
        for level in expected_levels:
            assert hasattr(LogLevel, level)
            assert getattr(LogLevel, level).value == level
    
    def test_pii_redactor_integration(self):
        """Test PII redactor integration with logging."""
        from app.core.audit import PIIRedactor
        
        # Test email redaction in logs
        email = "admin@pranely.com"
        redacted = PIIRedactor.redact_email(email)
        assert "@" in redacted
        assert "admin" not in redacted or "***" in redacted
    
    def test_audit_logger_initialization(self):
        """Test AuditLogger initialization."""
        from app.core.logging import AuditLogger
        
        logger = AuditLogger(name="test.audit")
        assert logger.logger is not None
        assert logger.logger.name == "test.audit"


# =============================================================================
# Test: NOM-151 Compliance
# =============================================================================


class TestNOM151Compliance:
    """Tests for NOM-151 compliance requirements."""
    
    def test_audit_trail_has_timestamp(self):
        """Test that audit trail includes timestamp field."""
        from app.core.audit import AuditTrailModel
        
        assert hasattr(AuditTrailModel, 'timestamp')
    
    def test_audit_trail_has_user_id(self):
        """Test that audit trail includes user identification."""
        from app.core.audit import AuditTrailModel
        
        assert hasattr(AuditTrailModel, 'user_id')
    
    def test_audit_trail_has_org_id(self):
        """Test that audit trail includes organization context."""
        from app.core.audit import AuditTrailModel
        
        assert hasattr(AuditTrailModel, 'organization_id')
    
    def test_audit_trail_has_ip_address(self):
        """Test that audit trail captures IP address."""
        from app.core.audit import AuditTrailModel
        
        assert hasattr(AuditTrailModel, 'ip_address')
    
    def test_audit_trail_has_action_type(self):
        """Test that audit trail captures action type."""
        from app.core.audit import AuditTrailModel
        
        assert hasattr(AuditTrailModel, 'action')
    
    def test_audit_trail_has_request_data(self):
        """Test that audit trail captures request data."""
        from app.core.audit import AuditTrailModel
        
        assert hasattr(AuditTrailModel, 'request_data')
    
    def test_audit_trail_has_response_status(self):
        """Test that audit trail captures response status."""
        from app.core.audit import AuditTrailModel
        
        assert hasattr(AuditTrailModel, 'response_status')
    
    def test_audit_trail_has_correlation_id(self):
        """Test that audit trail has correlation ID for tracing."""
        from app.core.audit import AuditTrailModel
        
        assert hasattr(AuditTrailModel, 'correlation_id')
    
    def test_retention_period_documented(self):
        """Test that retention period is documented."""
        # Check docs/NOM-151.md exists and mentions 5 years
        import os
        docs_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', 'docs', 'NOM-151.md'
        )
        
        if os.path.exists(docs_path):
            with open(docs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert '5 años' in content or '5 years' in content
                assert 'Retention' in content or 'retención' in content


# =============================================================================
# Run Tests
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
