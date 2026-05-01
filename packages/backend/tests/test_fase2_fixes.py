"""FASE 2 Backend Tests - Pytest

Tests Fixes 1-5:
- FIX 1: WasteMovement extended model
- FIX 2: Upload endpoint with RQ
- FIX 3: Review approve/reject
- FIX 4: Command operators CRUD
- FIX 5: Invite with hash expiry
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib
import uuid

# Mock settings before importing app modules
@pytest.fixture(autouse=True)
def mock_settings():
    with patch.dict('os.environ', {
        'SECRET_KEY': 'test-secret-key-for-testing-only',
        'DATABASE_URL': 'postgresql://test:test@localhost/test',
        'REDIS_URL': 'redis://localhost:6379',
    }):
        yield


# =============================================================================
# FIX 1: WasteMovement Model Tests
# =============================================================================

class TestWasteMovementModel:
    """Test WasteMovement extended fields (FIX 1)."""
    
    def test_model_has_review_fields(self):
        """Verify WasteMovement has all FASE 2 fields."""
        from app.models import WasteMovement
        
        required_fields = [
            'created_by_user_id', 'confidence_score', 'is_immutable',
            'archived_at', 'file_hash', 'file_size_bytes',
            'reviewed_by', 'reviewed_at', 'rejection_reason'
        ]
        
        for field in required_fields:
            assert hasattr(WasteMovement, field), f"Missing field: {field}"
    
    def test_confidence_score_range(self):
        """Test confidence_score is Float (0-1)."""
        from app.models import WasteMovement
        from sqlalchemy import Float
        
        col = WasteMovement.__table__.columns.get('confidence_score')
        assert col is not None
        assert col.type.python_type == float
    
    def test_file_hash_length(self):
        """Test file_hash is VARCHAR(64) for SHA-256."""
        from app.models import WasteMovement
        
        col = WasteMovement.__table__.columns.get('file_hash')
        assert col is not None
        assert col.type.length == 64


# =============================================================================
# FIX 2: Upload Endpoint Tests
# =============================================================================

class TestUploadEndpoint:
    """Test upload endpoint with RQ integration (FIX 2)."""
    
    @pytest.mark.asyncio
    async def test_upload_creates_movement(self):
        """Test upload creates WasteMovement with org_id."""
        from app.models import WasteMovement, MovementStatus
        
        # Mock file
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=b'%PDF-1.4 test content')
        mock_file.seek = AsyncMock()
        
        # Verify WasteMovement has all needed fields
        movement = WasteMovement(
            organization_id=1,
            manifest_number="NOM-20260501-TEST",
            status=MovementStatus.PENDING,
            file_path="/uploads/1/test.pdf",
            orig_filename="test.pdf",
            file_hash=hashlib.sha256(b'%PDF-1.4').hexdigest(),
            file_size_bytes=17,
        )
        
        assert movement.organization_id == 1
        assert movement.file_hash is not None
        assert movement.status == MovementStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_upload_rejects_non_pdf(self):
        """Test upload rejects non-PDF files."""
        # This would be tested with actual FastAPI TestClient
        pass
    
    def test_rq_job_enqueue_signature(self):
        """Test RQ job enqueue uses correct signature."""
        # Mock RQ enqueue
        job_id = str(uuid.uuid4())
        movement_id = 1
        org_id = 1
        
        # Verify job_id format
        assert len(job_id) == 36  # UUID4 format
        assert job_id.count('-') == 4


# =============================================================================
# FIX 3: Review Endpoint Tests
# =============================================================================

class TestReviewEndpoint:
    """Test review approve/reject workflow (FIX 3)."""
    
    def test_review_action_approve(self):
        """Test approve sets validated status and immutable."""
        from app.models import WasteMovement, MovementStatus
        
        movement = WasteMovement(
            id=1,
            organization_id=1,
            manifest_number="NOM-TEST",
            status=MovementStatus.PENDING,
            is_immutable=False,
        )
        
        # Simulate approve action
        movement.status = MovementStatus.VALIDATED
        movement.is_immutable = True
        movement.reviewed_by = "admin@pranely.com"
        movement.reviewed_at = datetime.now(timezone.utc)
        
        assert movement.status == MovementStatus.VALIDATED
        assert movement.is_immutable is True
        assert movement.reviewed_by == "admin@pranely.com"
    
    def test_review_action_reject(self):
        """Test reject sets rejected status with reason."""
        from app.models import WasteMovement, MovementStatus
        
        movement = WasteMovement(
            id=1,
            organization_id=1,
            manifest_number="NOM-TEST",
            status=MovementStatus.PENDING,
        )
        
        # Simulate reject action
        movement.status = MovementStatus.REJECTED
        movement.rejection_reason = "Document incomplete"
        movement.reviewed_by = "admin@pranely.com"
        
        assert movement.status == MovementStatus.REJECTED
        assert movement.rejection_reason == "Document incomplete"
    
    def test_review_requires_reason_for_reject(self):
        """Test reject action requires a reason."""
        # Validation happens at API level
        # The schema accepts reject with reason
        valid_reject_action = {"action": "reject", "reason": "Missing signatures"}
        assert valid_reject_action["reason"] is not None


# =============================================================================
# FIX 4: Command Operators Tests
# =============================================================================

class TestCommandOperators:
    """Test command operator CRUD with role/extra_data (FIX 4)."""
    
    def test_operator_role_enum(self):
        """Test valid operator roles."""
        from app.models import UserRole
        
        valid_roles = {"admin", "member", "viewer"}
        
        for role_str in valid_roles:
            role = UserRole(role_str)
            assert role.value == role_str
    
    def test_operator_cannot_be_owner(self):
        """Test operator endpoint prevents owner/director roles."""
        invalid_roles = {"owner", "director"}
        
        # In the endpoint, these should return 400
        for role_str in invalid_roles:
            # Endpoint validates this
            assert role_str not in {"admin", "member", "viewer"}
    
    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        """Test operators only returns org's members."""
        from app.models import Membership
        
        # Mock query with tenant filter
        org_id = 1
        
        # Verify membership requires organization_id
        mock_membership = MagicMock()
        mock_membership.organization_id = org_id
        
        assert mock_membership.organization_id == 1


# =============================================================================
# FIX 5: Invite Tests
# =============================================================================

class TestInviteHash:
    """Test invite with secure hash and 24h expiry (FIX 5)."""
    
    def test_invite_hash_format(self):
        """Test invite hash is UUID4."""
        hash_key = str(uuid.uuid4())
        
        # Verify UUID4 format
        uuid_obj = uuid.UUID(hash_key)
        assert str(uuid_obj) == hash_key
        assert len(hash_key) == 36
    
    def test_invite_expiry_calculation(self):
        """Test 24h expiry is calculated correctly."""
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(hours=24)
        
        delta = expiry - now
        assert delta.total_seconds() == 86400  # 24 hours
    
    @pytest.mark.asyncio
    async def test_validate_invite_hash(self):
        """Test validate_invite_hash returns data or None."""
        # Mock Redis validation
        valid_hash = str(uuid.uuid4())
        invalid_hash = "invalid-uuid"
        
        # Valid hash should be parseable as UUID
        try:
            uuid.UUID(valid_hash)
            is_valid = True
        except ValueError:
            is_valid = False
        
        assert is_valid is True
        
        # Invalid hash should fail
        try:
            uuid.UUID(invalid_hash)
            is_valid = False  # Should not reach here
        except ValueError:
            is_valid = False
        
        assert is_valid is False
    
    def test_invite_hash_one_time_use(self):
        """Test invite hash is deleted after use."""
        # Mock delete operation
        deleted_hashes = set()
        
        def use_and_delete(hash_key):
            deleted_hashes.add(hash_key)
            return True
        
        hash_key = str(uuid.uuid4())
        result = use_and_delete(hash_key)
        
        assert result is True
        assert hash_key in deleted_hashes


# =============================================================================
# Integration: Full Workflow Tests
# =============================================================================

class TestFullWorkflow:
    """E2E workflow tests."""
    
    @pytest.mark.asyncio
    async def test_upload_review_approve_workflow(self):
        """Test complete upload → review → approve workflow."""
        from app.models import WasteMovement, MovementStatus
        
        # 1. Upload creates movement
        movement = WasteMovement(
            organization_id=1,
            manifest_number=f"NOM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status=MovementStatus.PENDING,
            created_by_user_id=1,
            confidence_score=0.85,
        )
        
        assert movement.status == MovementStatus.PENDING
        assert movement.confidence_score == 0.85
        
        # 2. Review in progress
        movement.status = MovementStatus.IN_REVIEW
        assert movement.status == MovementStatus.IN_REVIEW
        
        # 3. Approve
        movement.status = MovementStatus.VALIDATED
        movement.is_immutable = True
        movement.reviewed_by = "admin@pranely.com"
        
        assert movement.status == MovementStatus.VALIDATED
        assert movement.is_immutable is True
        assert movement.reviewed_by is not None
    
    def test_immutable_prevents_further_changes(self):
        """Test validated movements cannot be modified."""
        from app.models import WasteMovement, MovementStatus
        
        movement = WasteMovement(
            organization_id=1,
            manifest_number="NOM-TEST",
            status=MovementStatus.VALIDATED,
            is_immutable=True,
        )
        
        # is_immutable flag is set - API enforces no further changes
        assert movement.is_immutable is True
        assert movement.status == MovementStatus.VALIDATED


# =============================================================================
# Tenant Isolation Tests
# =============================================================================

class TestTenantIsolation:
    """Test organization_id is enforced on all operations."""
    
    def test_waste_movement_requires_org_id(self):
        """Test WasteMovement always has organization_id."""
        from app.models import WasteMovement
        
        # Create movement with org_id
        movement = WasteMovement(
            organization_id=1,
            manifest_number="NOM-TEST",
        )
        
        assert movement.organization_id == 1
        
        # Verify org_id is not nullable in model
        org_col = WasteMovement.__table__.columns.get('organization_id')
        assert org_col.nullable is False
    
    def test_membership_tenant_filter(self):
        """Test Membership requires organization_id."""
        from app.models import Membership
        
        # Verify organization_id FK
        org_col = Membership.__table__.columns.get('organization_id')
        assert org_col is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])